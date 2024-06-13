import logging

from shitcoins.database.table.table import Table

LOGGER = logging.getLogger(__name__)


class WalletRepository(Table):
    name = 'wallet'

    def __init__(self, cursor):
        super().__init__(cursor)

    def insert_new_wallet_entry(self, holder_address: str, status: str):
        values = f"('{holder_address}', '{status}')"
        if self.get_wallet_entry(holder_address) is None:
            super()._insert_entry(self.name, values)
        else:
            LOGGER.warning(f"WALLET {holder_address} ALREADY EXISTS IN DB, NOT INSERTING")

    def get_wallet_entry(self, holder_address: str):
        return super()._get_entry_by_key(self.name, "address", holder_address)

    def update_wallet_entry_status(self, holder_address: str, status: str):
        """
        Updates entries in wallet table according to provided statement
        :param holder_address: the address to update status
        :param status: the status to be updated i.e. "status = SKIPPED"
        """
        update_statement = f"status = '{status}' WHERE address = '{holder_address}'"
        super()._update_table(self.name, update_statement)

    def truncate_all_entries(self):
        """
        Clear all entries in the wallet table
        """
        super()._truncate_table('wallet')
