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
from shitcoins.coin_data import CoinData
from shitcoins.database.table.wallet_repository import WalletRepository

LOGGER = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv('SOLSCAN_API_KEY')
SKIP_THRESHOLD = int(os.getenv('SKIP_THRESHOLD', 200))

if not API_KEY:
    raise ValueError("API key not found. Please set it in the .env file.")

# Define a pattern for Solana addresses
solana_address_pattern = re.compile(r"^[A-HJ-NP-Za-km-z1-9]{32,44}$")


def is_valid_solana_address(address):
    """Check if the address matches the Solana address pattern."""
    return bool(solana_address_pattern.match(address))


def get_first_transfer_time(holder_address: str, current_time: datetime) -> str | datetime | None:
    if not is_valid_solana_address(holder_address):
        LOGGER.info(f"Invalid Solana address: {holder_address}")
        return

    limit = 50
    last_tx_hash = ""
    total_transactions = 0

    while True:
        if total_transactions >= SKIP_THRESHOLD:
            LOGGER.info(f"Reached {SKIP_THRESHOLD} transactions for holder {holder_address}, skipping.")
            return "SKIPPED"

        url = f"https://pro-api.solscan.io/v1.0/account/transactions?account={holder_address}&limit={limit}"
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
                latest_transfer_time = datetime.fromtimestamp(data[0]['blockTime'], tz=timezone.utc)
                earliest_transfer_time = datetime.fromtimestamp(data[-1]['blockTime'], tz=timezone.utc)
                last_tx_hash = data[-1]['txHash']

                if len(data) < limit or current_time - latest_transfer_time > timedelta(hours=24):
                    return earliest_transfer_time

            except json.JSONDecodeError as e:
                LOGGER.error(f"JSON decode error: {e}")
                break
        else:
            LOGGER.error(f"Error: {response.status_code} - {response.text}")
            break


def check_holder(holder) -> str:
    LOGGER.info(f"Processing holder: {holder}")

    wallet_repo = None
    if os.getenv('RUN_WITH_DB').lower() == 'true':
        conn = psycopg2.connect(
            database='shitcoins', user='bottas', host='localhost', port='5333'
        )
        conn.autocommit = True
        wallet_repo = WalletRepository(conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        wallet_entry = wallet_repo.get_wallet_entry(holder)
        if wallet_entry is not None:
            return f"{holder} - {wallet_entry['status']}"

    current_time = datetime.now(timezone.utc)
    blocktime = get_first_transfer_time(holder, current_time)
    return_holder_status = f"{holder} - UNKNOWN"
    status = "UNKNOWN"

    if blocktime == "SKIPPED":
        return_holder_status = f"{holder} - SKIPPED"
    elif isinstance(blocktime, datetime):
        time_diff = current_time - blocktime
        is_within_24_hours = time_diff <= timedelta(hours=24)
        status = "FRESH" if is_within_24_hours else "OLD"

        hours_diff = time_diff.total_seconds() / 3600

        LOGGER.info(f"First transfer block time for holder {holder}: {blocktime} "
                    f"(within 24 hours: {is_within_24_hours} - {hours_diff:.2f} hours old)")

        return_holder_status = f"{holder} - {status}"

    if status != "FRESH" and wallet_repo is not None:
        wallet_repo.insert_new_wallet_entry(holder, status)

    return return_holder_status


def check_holder_with_counter(args):
    holder, counter, lock, total_holders = args
    result = check_holder(holder)
    with lock:
        counter.value += 1
        print(f"Processed {counter.value} of {total_holders}")
    return result


def multiprocess_coin_holders(pump_address: str, holder_addresses: [str]) -> CoinData:
    total_holders_count = len(holder_addresses)
    print(f"Assessing {total_holders_count} holder wallet addresses..")

    manager = multiprocessing.Manager()
    counter = manager.Value('i', 0)
    lock = manager.Lock()
    total_holders = total_holders_count

    with multiprocessing.Pool(processes=multiprocessing.cpu_count() - 2) as pool:
        results = []
        for holder in holder_addresses:
            result = pool.apply_async(check_holder_with_counter, args=((holder, counter, lock, total_holders),))
            results.append(result)
        updated_holders = [res.get() for res in results]

    coin_data = {'coin_address': pump_address, 'holders': updated_holders}
    return coin_data
