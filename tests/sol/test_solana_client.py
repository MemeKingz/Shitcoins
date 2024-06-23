import logging
import unittest

from shitcoins.sol.solana_client import get_first_transaction_sigs, is_bundled
from solana.rpc.async_api import Signature
import base58

logging.basicConfig(level=logging.INFO)


class TestSolanaClient(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.pump_address = '3QJzpi68a3CUVPGVUjYLWziGKCAvbNXmC5VFNy1ypump'
        self.signature_base58 = (base58
                                 .b58decode(
            '28FpjwvkEGi79PirqTi7Li7kePSMqjpojGmURYteeJptNVHp5NxYLPcAQr4bvf8nyou6ZVeKhPq6xmy3cyQen2WX'))

    async def test_solana_client_get_first_transaction(self):
        search_from_signature = Signature(self.signature_base58)
        signatures, earliest_block_time = await (get_first_transaction_sigs(self.pump_address, search_from_signature))
        self.assertTrue(earliest_block_time <= 1718937526)

    async def test_if_bundled_check_returns_false(self):
        search_from_signature = Signature(self.signature_base58)
        signatures, earliest_blocktime = await (get_first_transaction_sigs(self.pump_address, search_from_signature))
        bundled = await is_bundled(signatures)
        self.assertFalse(bundled)

    async def test_if_bundled_check_returns_true(self):
        bundled_addressed = 'E3HDR2gDRfwdz96kxo4Yteu4cGgcnpQN76TbB5Jipump'
        signatures, earliest_blocktime = await (get_first_transaction_sigs(bundled_addressed))
        bundled = await is_bundled(signatures[:500])
        self.assertTrue(bundled)
