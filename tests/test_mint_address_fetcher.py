import unittest

from shitcoins.mint_address_fetcher import MintAddressFetcher


class TestMintAddressFetcher(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.test_token_address = '3S8qX1MsMqRbiwKg2cQyx7nis1oHMgaCuc9c4VfvVdPN'
        self.dicki_token_address = '8EHC2gfTLDb2eGQfjm17mVNLWPGRc9YVD75bepZ2nZJa'
        self.mint_address_fetcher = MintAddressFetcher()

    async def test_fetch_pump_addresses_from_telegram_gets_correct_market_cap(self):
        coins_data = await self.mint_address_fetcher.fetch_pump_addresses_from_telegram()
        print(coins_data)

    def test_pump_address_info(self):
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
