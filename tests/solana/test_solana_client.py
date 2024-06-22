import unittest

from shitcoins.solana.solana_client import get_first_transaction


class TestSolanaClient(unittest.IsolatedAsyncioTestCase):

    async def test_solana_client_get_first_transaction(self):
        mint_address = '3QJzpi68a3CUVPGVUjYLWziGKCAvbNXmC5VFNy1ypump'
        await get_first_transaction(mint_address)