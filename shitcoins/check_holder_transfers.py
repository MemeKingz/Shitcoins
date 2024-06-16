from __future__ import annotations

import logging
import multiprocessing
import os
import json
import re
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
import requests
import psycopg2
import psycopg2.extras
from shitcoins.coin_data import CoinData, Holder
from shitcoins.database.table.wallet_repository import WalletRepository

LOGGER = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv('SOLSCAN_API_KEY')
SKIP_THRESHOLD = int(os.getenv('SKIP_THRESHOLD', 200))
RESERVED_CPUS = int(os.getenv('RESERVED_CPUS'))

if not API_KEY:
    raise ValueError("API key not found. Please set it in the .env file.")

solana_address_pattern = re.compile(r"^[A-HJ-NP-Za-km-z1-9]{32,44}$")


def is_valid_solana_address(address):
    """Check if the address matches the Solana address pattern."""
    return bool(solana_address_pattern.match(address))


def get_first_transfer_time_or_status(holder_addr: str, current_time: datetime) -> (
        None | str | tuple[datetime, int]):
    if not is_valid_solana_address(holder_addr):
        LOGGER.info(f"Invalid Solana address: {holder_addr}")
        return "UNKNOWN"

    max_trns_per_req = 50
    last_tx_hash = ""
    total_transactions = 0

    while True:
        if total_transactions >= SKIP_THRESHOLD:
            LOGGER.info(f"Reached {SKIP_THRESHOLD} transactions for holder {holder_addr}, skipping.")
            return "SKIPPED"

        url = f"https://pro-api.solscan.io/v1.0/account/transactions?account={holder_addr}&limit={max_trns_per_req}"
        if last_tx_hash:
            url += f"&beforeHash={last_tx_hash}"
        headers = {
            'accept': 'application/json',
            'token': API_KEY
        }

        response = requests.get(url, headers=headers)
        LOGGER.debug(f"Response status code: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                if not data:
                    break

                total_transactions += len(data)
                latest_transfer_time = (datetime.fromtimestamp(data[0]['blockTime'], tz=timezone.utc)
                                        .replace(microsecond=0))
                earliest_transfer_time = (datetime.fromtimestamp(data[len(data) - 1]['blockTime'], tz=timezone.utc)
                                          .replace(microsecond=0))
                last_tx_hash = data[-1]['txHash']

                # check for danger, if timestamps of first and last are the same
                if total_transactions <= max_trns_per_req:
                    if latest_transfer_time == earliest_transfer_time:
                        return "DANGER"

                # check for fresh
                if (len(data) < max_trns_per_req or current_time - latest_transfer_time
                        > timedelta(hours=int(os.getenv('FRESH_WALLET_HOURS')))):
                    return earliest_transfer_time, total_transactions
            except json.JSONDecodeError as e:
                LOGGER.error(f"JSON decode error: {e}")
                break
        elif response.status_code == 504:
            LOGGER.warning(f"504 error - skipped address: {holder_addr}")
            return "UNKNOWN"
        else:
            LOGGER.error(f"Error: {response.status_code} - {response.text}")
            break

    return "UNKNOWN"


def check_holder(holder_address: str) -> Holder:
    LOGGER.info(f"Processing holder: {holder_address}")

    wallet_repo = None
    wallet_entry = None
    if os.getenv('RUN_WITH_DB').lower() == 'true':
        conn = psycopg2.connect(
            database='shitcoins', user=os.getenv('DB_USER'), host='localhost', port=os.getenv('DB_PORT')
        )
        conn.autocommit = True

        wallet_repo = WalletRepository(conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        wallet_entry = wallet_repo.get_wallet_entry(holder_address)
        # prematurally return if holder address is not fresh to save api request and time
        if wallet_entry is not None and (wallet_entry['status'] == 'OLD'
                                         or wallet_entry['status'] == 'SKIPPED'
                                         or wallet_entry['status'] == 'DANGER'):
            return Holder(address=holder_address, status=wallet_entry['status'],
                          transactions_count=wallet_entry['transactions_count'])

    current_time = datetime.now(timezone.utc)
    result = get_first_transfer_time_or_status(holder_address, current_time)
    return_holder: Holder = Holder(address=holder_address, status="UNKNOWN", transactions_count=0)

    if result == "SKIPPED" or result == "DANGER":
        return_holder['status'] = result
    elif isinstance(result, tuple):
        blocktime, total_transactions = result
        time_diff = current_time - blocktime
        is_within_24_hours = time_diff <= timedelta(hours=int(os.getenv('FRESH_WALLET_HOURS')))
        return_holder['status'] = "FRESH" if is_within_24_hours else "OLD"
        # checking wallet transactions_count from DB - if transactions_count not none, increment transactions
        return_holder['transactions_count'] = total_transactions
        hours_diff = time_diff.total_seconds() / 3600

        LOGGER.info(f"First transfer block time for holder {holder_address}: {blocktime} "
                    f"(within 24 hours: {is_within_24_hours} - {hours_diff:.2f} hours old)")

    if wallet_repo is not None and return_holder['status'] != "UNKNOWN":
        if wallet_entry is None:
            wallet_repo.insert_new_wallet_entry(return_holder)
        else:
            wallet_repo.update_wallet_entry(return_holder)
    return return_holder


def check_holder_with_counter(args):
    holder, counter, lock, total_holders_count = args
    result = check_holder(holder)
    with lock:
        counter.value += 1
        print(f"Processed {counter.value} of {total_holders_count}")
    return result


def multiprocess_coin_holders(pump_address: str, holder_addresses: [str]) -> CoinData:
    total_holders_count = len(holder_addresses)

    print(f"Assessing {total_holders_count} holder wallet addresses..")

    manager = multiprocessing.Manager()
    counter = manager.Value('i', 0)
    lock = manager.Lock()

    with multiprocessing.Pool(processes=multiprocessing.cpu_count() - RESERVED_CPUS) as pool:
        results = []
        for holder in holder_addresses:
            result = pool.apply_async(check_holder_with_counter, args=((holder, counter, lock, total_holders_count),))
            results.append(result)
        updated_holders = [res.get() for res in results]

    coin_data = {'coin_address': pump_address, 'holders': updated_holders}

    return coin_data
