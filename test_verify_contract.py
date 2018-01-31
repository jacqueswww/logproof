from ethereum.tools import tester
from viper import compiler


# def test_merkle_proof_contract():
#     tester.languages['viper'] = compiler.Compiler()
#     s = tester.Chain()

#     # contract_code = open('merkleproof.v.py').read()
#     # contract = s.contract(contract_code, language='viper')

#     contract.add_root_hash(b'test')

#     assert contract.get_timestamp(b't') == 0
#     assert contract.get_timestamp(b'test') == s.head_state.timestamp
