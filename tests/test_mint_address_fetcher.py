import os
import unittest

from shitcoins.mint_address_fetcher import MintAddressFetcher
from shitcoins.model.coin_data import CoinData


class TestMintAddressFetcher(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        os.environ['MIN_MARKET_CAP'] = '20000'
        os.environ['MAX_MARKET_CAP'] = '300000'
        self.test_token_address = '3S8qX1MsMqRbiwKg2cQyx7nis1oHMgaCuc9c4VfvVdPN'
        self.dicki_token_address = '8EHC2gfTLDb2eGQfjm17mVNLWPGRc9YVD75bepZ2nZJa'
        self.mint_address_fetcher = MintAddressFetcher()

    async def test_fetch_pump_addresses_from_telegram_does_not_error(self):
        """
        Call fetch_pump_addresses_from_telegram and see that no errors occur
        """
        await self.mint_address_fetcher.fetch_pump_addresses_from_telegram()
        self.assertTrue(True)

    async def test_fetch_pump_addresses_from_telegram_respects_min_max_market_cap(self):
        os.environ['MIN_MARKET_CAP'] = '1'
        os.environ['MAX_MARKET_CAP'] = '1000'
        coins_data = await self.mint_address_fetcher.fetch_pump_addresses_from_telegram()
        self.assertEqual(0, len(coins_data))

    def test_fetch_pump_address_info_dexscreener_returns_correct_market_info(self):
        market_info = self.mint_address_fetcher.fetch_pump_address_info_dexscreener([self.dicki_token_address,
                                                                                     self.test_token_address])
        self.assertTrue(self.dicki_token_address in market_info)
        self.assertTrue(self.test_token_address in market_info)
        self.assertTrue(0 < market_info[self.dicki_token_address]['price'] < 100_000)
        self.assertTrue(0 < market_info[self.test_token_address]['price'] < 100_000)
        self.assertTrue(0 < market_info[self.dicki_token_address]['liquidity'] < 100_000_000)
        self.assertTrue(0 < market_info[self.test_token_address]['liquidity'] < 100_000_000)
        self.assertTrue(0 < market_info[self.dicki_token_address]['market_cap'])
        self.assertTrue(0 < market_info[self.test_token_address]['market_cap'])

