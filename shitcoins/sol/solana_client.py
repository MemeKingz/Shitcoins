from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import List

from dotenv import load_dotenv
import time

import solana.exceptions
from shitcoins.model.first_buy_statistics import FirstBuyStatistics
from shitcoins.util.time_util import datetime_from_utc_to_local
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


async def get_transaction(client: AsyncClient, earliest_signature: Signature):
    try:
        earliest_transaction = (await client.get_transaction(tx_sig=earliest_signature,
                                                             max_supported_transaction_version=0)).value
        return earliest_transaction
    except solana.exceptions.SolanaRpcException as e:
        LOGGER.error(e)
        raise


async def get_transaction_stats(
        earliest_signatures: List[RpcConfirmedTransactionStatusWithSignature]) -> FirstBuyStatistics:
    """
    :earliest_signatures:
    """
    LOGGER.info(f"Checking bundling against {len(earliest_signatures)} transactions")
    transactions_ui = []
    first_block_time = earliest_signatures[-1].block_time
    earliest_signatures.pop()  # remove first dev purchase

    # filter signatures to same first timestamp
    earliest_signatures_same_block_time = []
    for signature in reversed(earliest_signatures):
        if signature.block_time == first_block_time:
            earliest_signatures_same_block_time.append(signature)
        else:
            break

    async with AsyncClient(os.getenv("SOLANA_API_KEY")) as client:
        # Alchemy rate limits at 330 Compute Units per Second
        # (for free tier; growth tier allows us to double this function's speed)
        signatures_chunked = [earliest_signatures_same_block_time[x:x + 5] for x
                              in range(0, len(earliest_signatures_same_block_time), 5)]
        # Each get_signature_block_time costs 59 Compute Units, thus chunk
        for signatures in signatures_chunked:
            results = [get_transaction(client, signature.signature) for signature in signatures]
            transactions_ui.extend(await asyncio.gather(*results))
            time.sleep(0.2)

        # calculate total purchase pct and total buy count
        total_purchase_amt = 0
        total_buy_count = 0
        for transaction_ui in transactions_ui:
            meta = transaction_ui.transaction.meta
            account_index = meta.pre_token_balances[0].account_index
            pre_balance = meta.pre_token_balances[0].ui_token_amount.ui_amount
            for post_token_balance in meta.post_token_balances:
                if post_token_balance.account_index == account_index:
                    post_balance = post_token_balance.ui_token_amount.ui_amount
                    purchase_amt = pre_balance - post_balance
                    total_purchase_amt += purchase_amt
                    break
            total_buy_count += len(transaction_ui.transaction.transaction.signatures)
        total_purchase_pct = round((total_purchase_amt * 100) / 1000000000, 2)

    return FirstBuyStatistics(duplicate_wallet_count=len(earliest_signatures_same_block_time),
                              duplicate_count=total_buy_count,
                              duplicate_pct=total_purchase_pct)


async def is_mint_authority_revoked(mint_address: str) -> bool:
    """
    todo - check if mint authority is revoked on a coin to ignore
    """
    async with AsyncClient("https://api.devnet.solana.com") as client:
        res = await client.is_connected()
        if res is False:
            LOGGER.error("Unable to connect to Solana RPC API")
    return False
