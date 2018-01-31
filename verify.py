#!/usr/bin/env python3
import sha3
import math

from checkpoints import load_checkpoints
from mtree import validate_proof


checkpoint_path = 'checkpoints/'
checkpoints = load_checkpoints(checkpoint_path)


for path, details in checkpoints.items():

    if path == 'roots':
        continue

    print('Validating {}'.format(path))

    for checkpoint in details['history']:
        with open(path, 'rb') as f:
            total = checkpoint['to_pos'] - checkpoint['from_pos']
            f.seek(checkpoint['from_pos'])
            _hash = sha3.keccak_256()

            while total > 0:
                bufsize = 1024 if math.floor(total / 1024) else total
                data = f.read(bufsize)
                _hash.update(data)
                total -= bufsize

            if _hash.hexdigest() == checkpoint['hash']:
                state = 'ok'
            else:
                state = 'nok'

            # Merkle tree proof check.
            if state == 'ok' and checkpoint['proofs']:
                check = validate_proof(checkpoint['proofs'], checkpoint['root_hash'], checkpoint['hash'])
                if not check:
                    state = 'nok - mt fail'

            print('{} ... {} {}'.format(checkpoint['to_pos'], checkpoint['from_pos'], state))
