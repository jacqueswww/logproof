#!/usr/bin/env python3
import binascii
import collections
import datetime
import json
import math
import queue
import sha3
import socketserver
import threading
import time

from threading import Lock
from pathlib import Path

from mtree import MerkleTreeState, compute_layers, compute_merkleproof_for, \
    merkleroot, validate_proof

HOST, PORT = "0.0.0.0", 5140

write_q = queue.Queue()
checkpoint_timediff = datetime.timedelta(seconds=3)
checkpoint_path = 'checkpoints/'
checkpoint_lock = Lock()


class LogProofJSONEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, set):
            return list(o)
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
    checkpoints = {}
    file_path = Path(checkpoint_path + '{}_checkpoints.json'.format(
        datetime.datetime.now().strftime('%Y-%m-%d')
    ))
    if file_path.exists():
        print('Existing checkpoints.json found. Loading.')
        with file_path.open('rt') as f:
            checkpoints = json.load(f)

            for path, o in checkpoints.items():
                if path != 'roots':
                    checkpoints[path]['last_ts'] = gt(o['last_ts'])
            checkpoints['roots'] = set(checkpoints.get('roots', []))

    return checkpoints


def generate_mt_worker(checkpoints):
    CheckPointInfo = collections.namedtuple('CheckPointInfo', 'path history_pos hash')
    while True:
        time.sleep(3)
        with checkpoint_lock:
            now = datetime.datetime.now()

            path_hashes = []
            for path, details in checkpoints.items():
                if path != 'roots':
                    for i, checkpoint in enumerate(details['history']):
                        # Merkle proofs have not yet been produced
                        # and to_date is one checkpoint time frame ago.
                        if not checkpoint.get('root_hash') and \
                           now - gt(checkpoint['to_date']) > checkpoint_timediff:
                            path_hashes.append(
                                CheckPointInfo(path, i, checkpoint['hash'])
                            )

            if not path_hashes:  # Nothing to calculate.
                continue

            leaves = [
                binascii.unhexlify(ci.hash) for ci in path_hashes
            ]
            layers = compute_layers(leaves)
            tree = MerkleTreeState(layers)
            root_hash_str = binascii.hexlify(merkleroot(tree)).decode()
            # Calculate proofs for leaves.
            proofs = [compute_merkleproof_for(tree, _hash) for _hash in leaves]
            # Set the necessary proofs on the checkpoints.
            for i, ci in enumerate(path_hashes):
                checkpoints[ci.path]['history'][ci.history_pos]['root_hash'] = \
                    root_hash_str
                checkpoints[ci.path]['history'][ci.history_pos]['proofs'] = \
                    [binascii.hexlify(k) for k in proofs[i]]
            # Maintain the set of root hashes.
            if 'roots' not in checkpoints:
                checkpoints['roots'] = set()
            checkpoints['roots'].add(root_hash_str)

            save_checkpoints()


def check_point_update(path, ts, current_pos):
    with checkpoint_lock:
        if path not in checkpoints:
            checkpoints[path] = {
                'last_ts': ts,
                'last_pos': current_pos,
                'history': []
            }

        # Time to make a checkpoint.
        print(ts - checkpoints[path]['last_ts'])
        if ts - checkpoints[path]['last_ts'] > checkpoint_timediff:
            print('making checkpoint')
            last_pos = checkpoints[path]['last_pos']

            with open(path, 'rb') as logfile:
                logfile.seek(last_pos)
                total = current_pos - last_pos

                while total > 0:
                    bufsize = 1024 if math.floor(total / 1024) else total
                    _hash = sha3.keccak_256()
                    _hash.update(logfile.read(bufsize))
                    total -= bufsize

                checkpoints[path]['history'].append({
                    'hash': _hash.hexdigest(),
                    'from_date': checkpoints[path]['last_ts'].isoformat(),
                    'to_date': ts.isoformat(),
                    'from_pos': last_pos,
                    'to_pos': current_pos,
                    'root_hash': None
                })

                checkpoints[path]['last_pos'] = current_pos
                checkpoints[path]['last_ts'] = ts

            save_checkpoints()


def log_writer_worker(checkpoints):
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
        checkpoints = load_checkpoints()
        t = threading.Thread(target=log_writer_worker, args=[checkpoints])
        mt_t = threading.Thread(target=generate_mt_worker, args=[checkpoints])
        t.start()
        mt_t.start()
        server = socketserver.UDPServer((HOST, PORT), SyslogUDPHandler)
        server.serve_forever()
    except (IOError, SystemExit):
        quit()
    except KeyboardInterrupt:
        quit()
        print ("Crtl+C Pressed. Shutting down.")
