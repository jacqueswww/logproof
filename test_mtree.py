from mtree import MerkleTreeState, compute_layers, compute_merkleproof_for, \
    merkleroot, validate_proof


def test_mtree_proof():
    leaves = [str(i).encode() * 32 for i in range(10)]
    layers = compute_layers(leaves)
    tree = MerkleTreeState(layers)
    root = merkleroot(tree)
    proofs = [compute_merkleproof_for(tree, _hash) for _hash in leaves]

    for i, leaf in enumerate(leaves):
        assert validate_proof(proofs[i], root, leaf)
