from ethereum.tools import tester
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


def test_merkle_proof_contract():
    hash0 = b'a' * 32
    hash1 = b'b' * 32
    leaves = [hash0, hash1]
    layers = compute_layers(leaves)
    tree = MerkleTreeState(layers)
    root = merkleroot(tree)
    proofs0 = compute_merkleproof_for(tree, hash0)
    proofs1 = compute_merkleproof_for(tree, hash1)

    s = tester.Chain()
    contract_code = open('MerkleProof.sol').read()
    contract = s.contract(contract_code, language='solidity')

    assert contract.verifyProof(b''.join(proofs0), root, hash0)
    assert contract.verifyProof(b''.join(proofs1), root, hash1)
    assert contract.verifyProof(b''.join(proofs1), root, hash0) is False
