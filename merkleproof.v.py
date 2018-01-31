
roots: timestamp[bytes32]


@public
def add_root_hash(x: bytes32):
    self.roots[x] = block.timestamp


@public
def get_timestamp(x: bytes32) -> timestamp:
    return self.roots[x]


@constant
@public
def verify(proofs: bytes32[100], root: bytes32, leaf: bytes32) -> bool:

    computed_hash: bytes32 = leaf
    for proof in proofs:
        if leaf < proof:
            computed_hash = sha3(concat(computed_hash, proof))
        else:
            computed_hash = sha3(concat(proof, computed_hash))

    return computed_hash == root
