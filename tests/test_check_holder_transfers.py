import os
import unittest
from unittest.mock import patch

import psycopg2
import psycopg2.extras

from shitcoins.check_holder_transfers import multiprocess_coin_holders
from shitcoins.coin_data import CoinData
from shitcoins.database.table.wallet_repository import WalletRepository


class TestCheckHolderTransfers(unittest.TestCase):

    def setUp(self):
        self.expected_holder_addr_old = '369s8C1BTaMFRbyKtEfhjPV3d1N9t2VFV7Am3Q549Asi'
        self.expected_holder_addr_old2 = '716gAK3yUXGsB6CQbUw6Yr26neWa4TzZePdYHN299ANd'
        self.expected_holder_addr_unknown = '5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1'
        self.pump_address = "BE2BzgHTA8UHfAUESULgBcipEtKQqRinhxwT8v69pump"
        self.holder_addresses = [self.expected_holder_addr_unknown,
                                 self.expected_holder_addr_old2,
                                 self.expected_holder_addr_old]
        os.environ['DB_USER'] = 'TestyMcTestfaceDB'
        os.environ['DB_PORT'] = '5332'
        self.conn = psycopg2.connect(
            database='shitcoins', user='TestyMcTestfaceDB', host='localhost', port='5332'
        )
        self.conn.autocommit = True

    def test_multiprocess_coin_holders(self):
        os.environ['RUN_WITH_DB'] = 'false'
        coin_data: CoinData = multiprocess_coin_holders(self.pump_address, self.holder_addresses)
        self.assertEqual(self.pump_address, coin_data["coin_address"])
        self.assertEqual(3, len(coin_data['holders']))
        self.assertEqual('369s8C1BTaMFRbyKtEfhjPV3d1N9t2VFV7Am3Q549Asi - OLD', coin_data['holders'][2])

    def test_multiprocess_coin_holders_added_to_db(self):
        """
        This test requires a postgres instance running on 5332 with the correct db and user
        """
        os.environ['RUN_WITH_DB'] = 'true'

        # check items are in db as expected
        wallet_repo = WalletRepository(self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        wallet_repo.truncate_all_entries()

        coin_data: CoinData = multiprocess_coin_holders(self.pump_address, self.holder_addresses)
        self.assertEqual(self.pump_address, coin_data["coin_address"])
        self.assertEqual(3, len(coin_data['holders']))
        self.assertEqual(f'{self.expected_holder_addr_old} - OLD', coin_data['holders'][2])

        holder_old = wallet_repo.get_wallet_entry(self.expected_holder_addr_old)
        print(holder_old)
        self.assertEqual(self.expected_holder_addr_old, holder_old['address'])
        self.assertEqual('OLD', holder_old['status'])

        holder_unknown = wallet_repo.get_wallet_entry(self.expected_holder_addr_unknown)
        self.assertEqual(self.expected_holder_addr_unknown, holder_unknown['address'])
        self.assertEqual('UNKNOWN', holder_unknown['status'])

    def test_multiprocess_coin_holders_skip_checks_if_in_db(self):
        """
        Requires a proper instance of the postgres database
        Place a debugger on get_first_transfer_time to see that it is not called
        """
        wallet_repo = WalletRepository(self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        wallet_repo.truncate_all_entries()
        wallet_repo.insert_new_wallet_entry(self.expected_holder_addr_old, 'OLD')
        wallet_repo.insert_new_wallet_entry(self.expected_holder_addr_old2, 'OLD')
        wallet_repo.insert_new_wallet_entry(self.expected_holder_addr_unknown, 'UNKNOWN')
        coin_data: CoinData = multiprocess_coin_holders(self.pump_address, self.holder_addresses)

        self.assertEqual(self.pump_address, coin_data["coin_address"])
        self.assertEqual(3, len(coin_data['holders']))

    def test_calculate_and_save_average_transactions(self):
        fresh_holders = [
            '5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1 - FRESH - 5 transactions',
            '369s8C1BTaMFRbyKtEfhjPV3d1N9t2VFV7Am3Q549Asi - FRESH - 10 transactions'
        ]

        loop = asyncio.get_event_loop()
        loop.run_until_complete(calculate_and_save_average_transactions(fresh_holders, filename=self.filename))

        with open(self.filename, "r") as file:
            lines = file.readlines()
            self.assertTrue("Average Transactions for a fresh wallet:\n" in lines[0])
            self.assertTrue("Total Transactions: 15\n" in lines[1])
            self.assertTrue("Total Fresh Wallets: 2\n" in lines[2])
