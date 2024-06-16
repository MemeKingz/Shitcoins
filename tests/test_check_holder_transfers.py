import os
import unittest

import psycopg2
import psycopg2.extras

from shitcoins.check_holder_transfers import multiprocess_coin_holders, check_holder
from shitcoins.model.coin_data import CoinData
from shitcoins.database.table.wallet_repository import WalletRepository
from shitcoins.model.holder import Holder
from shitcoins.model.market_info import MarketInfo


class TestCheckHolderTransfers(unittest.TestCase):
    # test to see if UNKNOWN are NOT being added to db
    def setUp(self):
        self.expected_holder_addr_old: Holder = Holder(address='369s8C1BTaMFRbyKtEfhjPV3d1N9t2VFV7Am3Q549Asi',
                                                       status='OLD', transactions_count=0)
        self.expected_holder_addr_old2: Holder = Holder(address='716gAK3yUXGsB6CQbUw6Yr26neWa4TzZePdYHN299ANd',
                                                        status='OLD', transactions_count=0)
        self.expected_holder_addr_skipped: Holder = Holder(address='5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1',
                                                           status='SKIPPED', transactions_count=0)
        self.expected_holder_addr_fresh: Holder = Holder(address='2h6UHRdvF46GaUy5BMmWzN6tby6Vnsu3ZW2ep6PKkhGt',
                                                         status='FRESH', transactions_count=0)
        self.expected_holder_addr_unknown: Holder = Holder(address='bad address', status='UNKNOWN',
                                                           transactions_count=0)
        self.pump_address = "BE2BzgHTA8UHfAUESULgBcipEtKQqRinhxwT8v69pump"

        self.holders = [self.expected_holder_addr_skipped,
                                 self.expected_holder_addr_old2,
                                 self.expected_holder_addr_old]
        self.holder_addresses = [self.expected_holder_addr_skipped['address'],
                                 self.expected_holder_addr_old2['address'],
                                 self.expected_holder_addr_old['address']]
        os.environ['DB_USER'] = 'tests'
        os.environ['DB_PORT'] = '5332'
        os.environ['MIN_HOLDER_COUNT'] = '1'
        os.environ['FRESH_WALLET_HOURS'] = '24'
        os.environ['SKIP_THRESHOLD'] = '200'
        self.conn = psycopg2.connect(
            database='shitcoins', user=os.environ['DB_USER'], host='localhost', port=os.environ['DB_PORT']
        )
        self.conn.autocommit = True

    def test_multiprocess_coin_holders(self):
        """
        Basic test without db to see that multiprocess_coin_holders succeeds with old and skipped addresses
        """
        os.environ['RUN_WITH_DB'] = 'false'
        coin_data: CoinData = CoinData(coin_address=self.pump_address,
                                       market_info=MarketInfo(market_cap=0, liquidity=0, price=0),
                                       holders=self.holders)
        coin_data: CoinData = multiprocess_coin_holders(coin_data)
        self.assertEqual(self.pump_address, coin_data["coin_address"])
        self.assertEqual(3, len(coin_data['holders']))
        self.assertEqual('369s8C1BTaMFRbyKtEfhjPV3d1N9t2VFV7Am3Q549Asi', coin_data['holders'][2]['address'])
        self.assertEqual('OLD', coin_data['holders'][2]['status'])

    def test_multiprocess_coin_holders_identifies_skip_based_on_skip_threshold(self):
        os.environ['SKIP_THRESHOLD'] = '50'
        os.environ['RUN_WITH_DB'] = 'false'
        coin_data: CoinData = CoinData(coin_address=self.pump_address, holders=[self.expected_holder_addr_skipped])
        coin_data: CoinData = multiprocess_coin_holders(coin_data)
        self.assertEqual(1, len(coin_data['holders']))
        self.assertEqual('SKIPPED', coin_data['holders'][0]['status'])

    def test_multiprocess_coin_holder_unknown_not_added_to_db(self):
        """
        Test multiprocess_coin_holder function does not save UNKNOWN wallet to database
        """
        os.environ['RUN_WITH_DB'] = 'true'
        wallet_repo = WalletRepository(self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        wallet_repo.truncate_all_entries()
        coin_data: CoinData = CoinData(coin_address=self.pump_address,
                                       market_info=MarketInfo(market_cap=0, liquidity=0, price=0),
                                       holders=[self.expected_holder_addr_unknown])
        coin_data: CoinData = multiprocess_coin_holders(coin_data)
        self.assertEqual(1, len(coin_data['holders']))
        self.assertEqual('UNKNOWN', coin_data['holders'][0]['status'])

        holder_unknown = wallet_repo.get_wallet_entry(self.expected_holder_addr_unknown['address'])
        self.assertIsNone(holder_unknown)

    def test_multiprocess_coin_holders_added_to_db(self):
        """
        Test if multiprocess_coin_holders adds OLD and DANGER to database
        """
        os.environ['RUN_WITH_DB'] = 'true'

        # check items are in db as
        wallet_repo = WalletRepository(self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        wallet_repo.truncate_all_entries()
        coin_data: CoinData = CoinData(coin_address=self.pump_address,
                                       market_info=MarketInfo(market_cap=0, liquidity=0, price=0),
                                       holders=self.holders)
        coin_data: CoinData = multiprocess_coin_holders(coin_data)
        self.assertEqual(self.pump_address, coin_data["coin_address"])
        self.assertEqual(3, len(coin_data['holders']))
        self.assertEqual('OLD', coin_data['holders'][2]['status'])

        holder_old = wallet_repo.get_wallet_entry(self.expected_holder_addr_old['address'])
        self.assertEqual(self.expected_holder_addr_old['address'], holder_old['address'])
        self.assertEqual('OLD', holder_old['status'])

        os.environ['SKIP_THRESHOLD'] = '50'
        holder_skipped = wallet_repo.get_wallet_entry(self.expected_holder_addr_skipped['address'])
        self.assertEqual(self.expected_holder_addr_skipped['address'], holder_skipped['address'])
        self.assertEqual('SKIPPED', holder_skipped['status'])


    def test_multiprocess_coin_holders_skip_checks_if_in_db(self):
        """
        This is a manual test. Place a debugger on get_first_transfer_time to see that it is not called
        """
        os.environ['RUN_WITH_DB'] = 'true'
        wallet_repo = WalletRepository(self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        wallet_repo.truncate_all_entries()
        wallet_repo.insert_new_wallet_entry(self.expected_holder_addr_old)
        wallet_repo.insert_new_wallet_entry(self.expected_holder_addr_old2)
        wallet_repo.insert_new_wallet_entry(self.expected_holder_addr_skipped)
        coin_data: CoinData = CoinData(coin_address=self.pump_address,
                                       market_info=MarketInfo(market_cap=0, liquidity=0, price=0),
                                       holders=self.holders)
        coin_data: CoinData = multiprocess_coin_holders(coin_data)

        self.assertEqual(self.pump_address, coin_data["coin_address"])
        self.assertEqual(3, len(coin_data['holders']))

    def test_check_holder_transactions_count_with_db(self):
        """
        Test that transaction counts are being recorded correctly to the database.
        """
        os.environ['FRESH_WALLET_HOURS'] = '10000000'
        os.environ['SKIP_THRESHOLD'] = '1000'
        os.environ['RUN_WITH_DB'] = 'true'

        wallet_repo = WalletRepository(self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        wallet_repo.truncate_all_entries()
        check_holder(self.expected_holder_addr_fresh)
        result = wallet_repo.get_wallet_entry(self.expected_holder_addr_fresh['address'])
        self.assertEqual(self.expected_holder_addr_fresh['address'], result['address'])
        self.assertEqual("FRESH", result['status'])

        self.assertTrue(result['transactions_count'] > 0)
        check_holder(self.expected_holder_addr_fresh)
        result_second_run = wallet_repo.get_wallet_entry(self.expected_holder_addr_fresh['address'])
        self.assertEqual(result['transactions_count'], result_second_run['transactions_count'])


