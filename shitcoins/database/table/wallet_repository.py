import logging

from shitcoins.model.coin_data import Holder
from shitcoins.database.table.table import Table

LOGGER = logging.getLogger(__name__)


class WalletRepository(Table):
    name = 'wallet'

    def __init__(self, cursor):
        super().__init__(cursor)

    def insert_new_wallet_entry(self, holder: Holder):
        values = f"('{holder['address']}', '{holder['status']}',{holder['transactions_count']})"
        if self.get_wallet_entry(holder['address']) is None:
            super()._insert_entry(self.name, values)
        else:
            LOGGER.warning(f"WALLET {holder['address']} ALREADY EXISTS IN DB, NOT INSERTING")

    def get_wallet_entry(self, holder_address: str):
        return super()._get_entry_by_key(self.name, "address", holder_address)

    def update_wallet_entry(self, holder: Holder):
        """
        Updates entries in wallet table according to provided statement
        :param holder: new holder instance to update existing transactions_count and status
        """
        update_statement = (f"transactions_count = {holder['transactions_count']} "
                            f", status = '{holder['status']}' "
                            f"WHERE address = '{holder['address']}'")
        super()._update_table(self.name, update_statement)

    def get_average_transactions_count_for_fresh_wallet(self) -> float:
        query = """
        SELECT AVG(transactions_count) AS average_transactions
        FROM wallet
        WHERE status = 'FRESH';
        """
        result = self._cursor.execute(query)
        return result

    def get_max_transactions_count_for_fresh_wallet(self) -> int:
        query = """
        SELECT MAX(transactions_count) AS max_transactions
        FROM wallet
        WHERE status = 'FRESH';
        """
        result = self._cursor.execute(query)
        return result

    def truncate_all_entries(self):
        """
        Clear all entries in the wallet table
        """
        super()._truncate_table('wallet')
