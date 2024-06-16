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


def get_first_transfer_time(holder_address: str, current_time: datetime) -> None | str | tuple[datetime, int]:
    if not is_valid_solana_address(holder_address):
        LOGGER.info(f"Invalid Solana address: {holder_address}")
        return "UNKNOWN"

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
                earliest_transfer_time = datetime.fromtimestamp(data[len(data) - 1]['blockTime'], tz=timezone.utc)
                last_tx_hash = data[-1]['txHash']

                if (len(data) < limit or current_time - latest_transfer_time
                        > timedelta(hours=int(os.getenv('FRESH_WALLET_HOURS')))):
                    return earliest_transfer_time, total_transactions
            except json.JSONDecodeError as e:
                LOGGER.error(f"JSON decode error: {e}")
                break
        elif response.status_code == 504:
            LOGGER.warning(f"504 error - skipped address: {holder_address}")
            return "UNKNOWN"
        else:
            LOGGER.error(f"Error: {response.status_code} - {response.text}")
            break

    return "UNKNOWN"


def check_holder(holder: Holder) -> Holder:
    LOGGER.info(f"Processing holder: {holder}")

    wallet_repo = None
    wallet_entry = None
    if os.getenv('RUN_WITH_DB').lower() == 'true':
        conn = psycopg2.connect(
            database='shitcoins', user=os.getenv('DB_USER'), host='localhost', port=os.getenv('DB_PORT')
        )
        conn.autocommit = True

        wallet_repo = WalletRepository(conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        wallet_entry = wallet_repo.get_wallet_entry(holder['address'])
        # prematurely return if holder address is not fresh to save api request and time
        if wallet_entry is not None and wallet_entry['status'] == 'OLD' and wallet_entry['status'] == 'SKIPPED':
            holder['status'] = wallet_entry['status']
            holder['transactions_count'] = wallet_entry['transactions_count']
            return holder

    current_time = datetime.now(timezone.utc)
    result = get_first_transfer_time(holder['address'], current_time)

    if result == "SKIPPED":
        holder['status'] = "SKIPPED"
    elif isinstance(result, tuple):
        blocktime, total_transactions = result
        time_diff = current_time - blocktime
        is_within_24_hours = time_diff <= timedelta(hours=int(os.getenv('FRESH_WALLET_HOURS')))
        holder['status'] = "FRESH" if is_within_24_hours else "OLD"
        # checking wallet transactions_count from DB - if transactions_count not none, increment transactions
        holder['transactions_count'] = total_transactions
        hours_diff = time_diff.total_seconds() / 3600

        LOGGER.info(f"First transfer block time for holder {holder}: {blocktime} "
                    f"(within 24 hours: {is_within_24_hours} - {hours_diff:.2f} hours old)")

    if wallet_repo is not None and holder['status'] != "UNKNOWN":
        if wallet_entry is None:
            wallet_repo.insert_new_wallet_entry(holder)
        else:
            wallet_repo.update_wallet_entry(holder)
    return holder


# Function to process files and update the JSON based on transfer times
def multiprocess_coin_holders(coin_data: CoinData) -> CoinData:
    total_holders_count = len(coin_data['holders'])
    print(f"Assessing {total_holders_count} holder wallet addresses..")

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()
                                        - int(os.getenv('RESERVED_CPUS'))) as pool:
        updated_holders = pool.map(check_holder, coin_data['holders'])

    # Update the holders in the original JSON data
    coin_data['holders'] = updated_holders
    return coin_data
