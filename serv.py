#!/usr/bin/env python3
import datetime
import queue
import socketserver
import threading

from pathlib import Path
from checkpoints import (
    check_point_update,
    generate_mt_worker,
    load_checkpoints,
    save_checkpoints
)


HOST, PORT = "0.0.0.0", 5140

write_q = queue.Queue()
checkpoint_timediff = datetime.timedelta(seconds=3)
checkpoint_path = 'checkpoints/'


def log_writer_worker(checkpoints, checkpoint_timediff):
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
            check_point_update(checkpoint_path, checkpoints, str(path), ts, current_pos, checkpoint_timediff)
        write_q.task_done()


class SyslogUDPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        data = bytes.decode(self.request[0].strip(), 'utf-8')
        length = len(data)
        if length > 4:
            data = data[:-1] if data[-1] == '\x00' else data
            write_q.put((datetime.datetime.now(), self.client_address[0], data))


def quit():
    write_q.put(None)
    t.join()


if __name__ == "__main__":

    try:
        checkpoints = load_checkpoints(checkpoint_path)
        t = threading.Thread(target=log_writer_worker, args=[checkpoints, checkpoint_timediff])
        mt_t = threading.Thread(target=generate_mt_worker, args=[checkpoint_path, checkpoints, checkpoint_timediff])
        t.start()
        mt_t.start()
        server = socketserver.UDPServer((HOST, PORT), SyslogUDPHandler)
        server.serve_forever()
    except (IOError, SystemExit):
        quit()
    except KeyboardInterrupt:
        quit()
        print ("Crtl+C Pressed. Shutting down.")
