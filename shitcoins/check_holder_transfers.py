from __future__ import annotations

import logging
import multiprocessing
import os
import json
import re
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
import requests
import psycopg2
import psycopg2.extras
from shitcoins.model.coin_data import CoinData, Holder
from shitcoins.database.table.wallet_repository import WalletRepository

LOGGER = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv('SOLSCAN_API_KEY')
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
    total_transactions = 0

    while True:
        if total_transactions >= int(os.getenv('SKIP_THRESHOLD', 200)):
            LOGGER.info(f"Reached {int(os.getenv('SKIP_THRESHOLD', 200))} transactions for "
                        f"holder {holder_addr}, labelling as old.")
            # we know its old, so set a really old time
            return (current_time - timedelta(days=10)), total_transactions

        url = (f"https://pro-api.solscan.io/v1.0/account/solTransfers?account={holder_addr}"
               f"&limit={max_trns_per_req}&offset={total_transactions}")
        headers = {
            'accept': 'application/json',
            'token': API_KEY
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            try:
                data = response.json()['data']
                if not data:
                    break

                total_transactions += len(data)
                latest_transfer_time = (datetime.fromtimestamp(data[0]['blockTime'], tz=timezone.utc)
                                        .replace(microsecond=0))
                earliest_transfer_time = (datetime.fromtimestamp(data[len(data) - 1]['blockTime'], tz=timezone.utc)
                                          .replace(microsecond=0))
                last_tx_hash = data[-1]['txHash']

                # check for bundlers and if timestamps of first and last are the same
                if total_transactions <= max_trns_per_req:
                    if latest_transfer_time == earliest_transfer_time:
                        return "BUNDLER"

                # check for fresh/old
                if (len(data) < max_trns_per_req or current_time - latest_transfer_time
                        > timedelta(hours=int(os.getenv('FRESH_WALLET_HOURS')))):
                    # return potential fresh/old with total transactions
                    return earliest_transfer_time, total_transactions
            except json.JSONDecodeError as e:
                LOGGER.error(f"JSON decode error: {e}")
                break
        elif response.status_code == 504:
            LOGGER.error(f"504 error - unknown address: {holder_addr}")
            return "UNKNOWN"
        elif response.status_code == 429:
            LOGGER.error(f"Error: {response.status_code} - {response.text}")
            time.sleep(int(os.getenv('TOO_MANY_REQUESTS_BACKOFF_SEC', 60)))
        else:
            LOGGER.error(f"Error: {response.status_code} - {response.text}")
            return "UNKNOWN"

    return "UNKNOWN"


def check_holder(holder: Holder) -> Holder:
    LOGGER.info(f"Processing holder: {holder}")

    wallet_repo = None
    wallet_entry = None
    if os.getenv('RUN_WITH_DB').lower() == 'true':
        # todo - creating a new connection everytime may be inefficient, consider alternative
        conn = psycopg2.connect(
            database='shitcoins', user=os.getenv('DB_USER'), host='localhost', port=os.getenv('DB_PORT')
        )
        conn.autocommit = True

        wallet_repo = WalletRepository(conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        wallet_entry = wallet_repo.get_wallet_entry(holder['address'])
        # prematurely return if holder address is not fresh to save api request and time
        if wallet_entry is not None and (wallet_entry['status'] == 'OLD'
                                         or wallet_entry['status'] == 'BUNDLER'):
            holder['status'] = wallet_entry['status']
            holder['transactions_count'] = wallet_entry['transactions_count']
            return holder

    current_time = datetime.now(timezone.utc)
    result = get_first_transfer_time_or_status(holder['address'], current_time)

    if isinstance(result, tuple):
        blocktime, total_transactions = result
        time_diff = current_time - blocktime
        is_within_24_hours = time_diff <= timedelta(hours=int(os.getenv('FRESH_WALLET_HOURS')))
        holder['status'] = "FRESH" if is_within_24_hours else "OLD"
        holder['transactions_count'] = total_transactions
        hours_diff = time_diff.total_seconds() / 3600

        LOGGER.info(f"First transfer block time for holder {holder}: {blocktime} "
                    f"(within 24 hours: {is_within_24_hours} - {hours_diff:.2f} hours old)")
    elif result == "OLD" or result == "BUNDLER":
        holder['status'] = result

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