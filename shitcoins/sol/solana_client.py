from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import List

from dotenv import load_dotenv
import time

import solana.exceptions
from shitcoins.util.time_util import datetime_from_utc_to_local
from collections import Counter
from solana.rpc.async_api import AsyncClient, Signature, Pubkey
from solana.rpc.commitment import Finalized
from solders.rpc.responses import RpcConfirmedTransactionStatusWithSignature

LOGGER = logging.getLogger(__name__)
load_dotenv()


async def get_first_transaction_sigs(mint_address: str, from_signature=None) -> (
        list[RpcConfirmedTransactionStatusWithSignature], int | None):
    """
    :mint_address: the newly minted coin address
    :from_signature: if known, a signature to begin checking from, otherwise default None and start from latest transaction
    :throws: SolanaRpcException
    """
    async with AsyncClient(os.getenv("SOLANA_API_KEY")) as client:
        mint_pubkey = Pubkey.from_string(mint_address)

        # do we need to determine if there is no mint authority to slim it down further?
        # account_info = (await client.get_account_info(pubkey=mint_pubkey)).value

        start_time = time.time()
        earliest_signature = from_signature
        counter = 0
        skip_threshold = int(os.getenv("SOLANA_SKIP_THRESHOLD"))
        while counter < skip_threshold:
            try:
                signatures = (await client.get_signatures_for_address(account=mint_pubkey,
                                                                      before=earliest_signature,
                                                                      commitment=Finalized)).value
                earliest_signature = signatures[-1].signature
                earliest_transaction = (await client.get_transaction(tx_sig=earliest_signature,
                                                                     max_supported_transaction_version=0)).value

                earliest_ltime = datetime_from_utc_to_local(datetime.utcfromtimestamp(earliest_transaction.block_time))
                counter += 1
                if counter % 50:
                    LOGGER.debug(f" Searching earliest transaction for {mint_address} :: "
                                f"Currently at {earliest_ltime}")

                if len(signatures) < 1000:
                    # found the earliest transaction
                    LOGGER.info(f" Found earliest transaction execution "
                                f":: {earliest_ltime} "
                                f":: Coin {mint_address} ")
                    LOGGER.debug(f"First transaction found in {round(time.time() - start_time, 2)} seconds")
                    return signatures, earliest_transaction.block_time
            except solana.exceptions.SolanaRpcException as e:
                LOGGER.error(e)
                raise
        LOGGER.warning(f" UNABLE to determine earliest transaction within the last "
                     f"{(skip_threshold * 1000):,} transactions :: "
                     f"return {earliest_ltime}")
        return signatures, earliest_transaction.block_time


async def get_signature_block_time(client: AsyncClient, earliest_signature: Signature):
    try:
        earliest_transaction = (await client.get_transaction(tx_sig=earliest_signature,
                                                             max_supported_transaction_version=0)).value
        return earliest_transaction.block_time
    except solana.exceptions.SolanaRpcException as e:
        LOGGER.error(e)
        raise


async def is_bundled(earliest_signatures: List[RpcConfirmedTransactionStatusWithSignature]) -> bool:
    """
    If timestamps of the first len(earliest_signatures) is greater than DUPLICATE_FIRST_TRANSACTIONS_PCT
    :earliest_signatures:
    """
    LOGGER.info(f"Checking bundling against {len(earliest_signatures)} transactions")
    results = []
    async with AsyncClient(os.getenv("SOLANA_API_KEY")) as client:
        total_signatures_count = len(earliest_signatures)

        # Alchemy rate limits at 330 Compute Units per Second
        # (for free tier; growth tier allows us to double this function's speed)
        signatures_chunked = [earliest_signatures[x:x + 5] for x in range(0, len(earliest_signatures), 5)]
        # Each get_signature_block_time costs 59 Compute Units, thus chunk
        for signatures in signatures_chunked:
            tasks = [get_signature_block_time(client, signature.signature) for signature in signatures]
            results.extend(await asyncio.gather(*tasks))
            time.sleep(0.2)

        count_dict = Counter(results)
        duplicate_count = max(count_dict.values())
        print(f"{duplicate_count} duplicates found within first {total_signatures_count} transactions")
        if ((duplicate_count * 100) / total_signatures_count) > int(os.getenv('DUPLICATE_FIRST_TRANSACTIONS_PCT')):
            print(f"{round(((duplicate_count * 100) / total_signatures_count))}% of early transactions are bundled")
            return True
    return False


async def is_mint_authority_revoked(mint_address: str) -> bool:
    """
    todo - check if mint authority is revoked on a coin to ignore
    """
    async with AsyncClient("https://api.devnet.solana.com") as client:
        res = await client.is_connected()
        if res is False:
            LOGGER.error("Unable to connect to Solana RPC API")
    return False
