import unittest

from shitcoins.check_holder_transfers import multiprocess_coin_holders
from shitcoins.coin_data import CoinData


class TestCheckHolderTransfers(unittest.TestCase):
    def test_multiprocess_coin_holders(self):
        pump_address = "BE2BzgHTA8UHfAUESULgBcipEtKQqRinhxwT8v69pump"
        holder_addresses = ["5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1",
                            "716gAK3yUXGsB6CQbUw6Yr26neWa4TzZePdYHN299ANd",
                            "369s8C1BTaMFRbyKtEfhjPV3d1N9t2VFV7Am3Q549Asi"]
        coin_data: CoinData = multiprocess_coin_holders(pump_address, holder_addresses)
        self.assertEqual(pump_address, coin_data["coin_address"])
        self.assertEqual(3, len(coin_data['holders']))
        self.assertEqual('369s8C1BTaMFRbyKtEfhjPV3d1N9t2VFV7Am3Q549Asi - OLD', coin_data['holders'][2])