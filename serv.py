#!/usr/bin/python3
import datetime
import hashlib
import json
import math
import queue
import socketserver
import threading

from pathlib import Path

HOST, PORT = "0.0.0.0", 5140

write_q = queue.Queue()
checkpoints = {}
checkpoint_timediff = datetime.timedelta(seconds=3)
checkpoint_path = 'checkpoints/'


def log_writer_worker():
    while True:
        item = write_q.get()
        if item is None:
            break
        ts, client_address, message = item

        filename = ts.strftime('%Y-%m-%d') + ".log"
        path = Path("/".join((client_address, filename)))
        if not path.parent.exists():
            path.parent.mkdir(parents=True)

        current_pos = 0
        with path.open('a') as logfile:
            logfile.write("{} {}\n".format(ts.isoformat(), message))
            current_pos = logfile.tell()

        if current_pos:
            check_point_update(str(path), ts, current_pos)

        write_q.task_done()


class LogProofJSONEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()

        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, o)


def save_checkpoints():
    file_path = Path(checkpoint_path + '{}_checkpoints.json'.format(
        datetime.datetime.now().strftime('%Y-%m-%d')
    ))
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True)
    with file_path.open('wt') as f:
        f.write(LogProofJSONEncoder().encode(checkpoints))


def gt(dt_str):
    dt, _, us = dt_str.partition(".")
    dt = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
    us = int(us.rstrip("Z"), 10)
    return dt + datetime.timedelta(microseconds=us)


def load_checkpoints():
    file_path = Path(checkpoint_path + '{}_checkpoints.json'.format(
        datetime.datetime.now().strftime('%Y-%m-%d')
    ))
    if file_path.exists():
        print('Existing checkpoints.json found. Loading.')
        with file_path.open('rt') as f:
            checkpoints = json.load(f)

        for path, o in checkpoints.items():
            checkpoints[path]['last_ts'] = gt(o['last_ts'])


def check_point_update(path, ts, current_pos):

    if path not in checkpoints:
        checkpoints[path] = {
            'last_ts': ts,
            'last_pos': current_pos,
            'history': []
        }

    # Time to make a checkpoint.
    if ts - checkpoints[path]['last_ts'] > checkpoint_timediff:
        last_pos = checkpoints[path]['last_pos']

        with open(path, 'rb') as logfile:
            logfile.seek(last_pos)
            total = current_pos - last_pos

            while total > 0:
                bufsize = 1024 if math.floor(total / 1024) else total
                _hash = hashlib.sha256()
                _hash.update(logfile.read(bufsize))
                total -= bufsize

            checkpoints[path]['history'].append({
                'hash': _hash.hexdigest(),
                'from_date': checkpoints[path]['last_ts'].isoformat(),
                'to_date': ts.isoformat(),
                'from_pos': last_pos,
                'to_pos': current_pos
            })

            checkpoints[path]['last_pos'] = current_pos
            checkpoints[path]['last_ts'] = ts

            save_checkpoints()


class SyslogUDPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        data = bytes.decode(self.request[0].strip(), 'utf-8')
        laengde = len(data)
        if laengde > 4:
            write_q.put((datetime.datetime.now(), self.client_address[0], data))


def quit():
    write_q.put(None)
    t.join()


if __name__ == "__main__":
    try:
        load_checkpoints()
        t = threading.Thread(target=log_writer_worker)
        t.start()
        server = socketserver.UDPServer((HOST, PORT), SyslogUDPHandler)
        server.serve_forever()
    except (IOError, SystemExit):
        quit()
    except KeyboardInterrupt:
        quit()
        print ("Crtl+C Pressed. Shutting down.")
