import logging
import unittest

from shitcoins.sol.solana_client import get_first_transaction_sigs, get_transaction_stats
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
        bundled = await get_transaction_stats(signatures[:200])
        self.assertFalse(bundled)

    async def test_if_transaction_stats_are_accurate(self):
        bundled_addressed = 'E3HDR2gDRfwdz96kxo4Yteu4cGgcnpQN76TbB5Jipump'
        signatures, earliest_blocktime = await (get_first_transaction_sigs(bundled_addressed))
        first_buy_stats = await get_transaction_stats(signatures[-10:])
        self.assertEqual(20, first_buy_stats['duplicate_count'])
        self.assertEqual(4, first_buy_stats['duplicate_wallet_count'])
        self.assertEqual(57.79, first_buy_stats['duplicate_pct'])
