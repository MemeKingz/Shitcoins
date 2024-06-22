import logging
import sys
import time
from base64 import b64encode, b64decode

import solana.exceptions
from solana.rpc.async_api import AsyncClient, Pubkey
from solana.rpc.core import RPCException

LOGGER = logging.getLogger(__name__)


async def get_first_transaction(mint_address: str):
    async with AsyncClient("https://api.mainnet-beta.solana.com") as client:
        res = await client.is_connected()
        if res is False:
            LOGGER.error("Unable to connect to Solana RPC API")

        mint_pubkey = Pubkey.from_string(mint_address)

        # print(mint_pubkey)
        # account_info = (await client.get_account_info(pubkey=mint_pubkey)).value

        start_time = time.time()
        # get last 1000 signatures
        signatures = (await client.get_signatures_for_address(mint_pubkey)).value
        signatures_reversed = signatures[::-1]
        earliest_signature = signatures_reversed[0].signature
        earliest_transaction = (await client.get_transaction(tx_sig=earliest_signature,
                                                             max_supported_transaction_version=0)).value

        counter = 2
        while earliest_transaction is not None or counter < 1000:
            try:
                signatures = (await client.get_signatures_for_address(account=mint_pubkey,
                                                                      before=earliest_signature)).value
                signatures_reversed = signatures[::-1]
                earliest_signature = signatures_reversed[0].signature
                if earliest_signature is not None:
                    earliest_transaction = (await client.get_transaction(tx_sig=earliest_signature,
                                                                         max_supported_transaction_version=0)).value
                counter += 2

                print(earliest_transaction.block_time)
                if counter % 10 == 0:
                    # Devnet maximum number of requests per 10 seconds per IP: 100
                    print('sleeping 10 seconds...')
                    time.sleep(10)
            except solana.exceptions.SolanaRpcException as e:
                LOGGER.error(f"429 Too Many Requests error")
                # keeps happening before counter is 10??
                raise

        print(f"Execution ran for {time.time() - start_time}")

async def is_mint_authority_revoked(mint_address: str) -> bool:
    """
    todo - check if mint authority is revoked on a coin to ignore
    """
    async with AsyncClient("https://api.devnet.solana.com") as client:
        res = await client.is_connected()
        if res is False:
            LOGGER.error("Unable to connect to Solana RPC API")
    return False

