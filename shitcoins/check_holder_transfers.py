import multiprocessing

import requests
from dotenv import load_dotenv
import os
import json
import re
from datetime import datetime, timedelta, timezone

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


# Function to determine if holder should be SKIPPED, IGNORED or INCLUDED with earliest transfer time
def get_first_transfer_time(holder_address, current_time, debug=False) -> str | datetime | None:
    if not is_valid_solana_address(holder_address):
        if debug:
            print(f"Invalid Solana address: {holder_address}")
        return

    limit = 50
    last_tx_hash = ""
    total_transactions = 0

    while True:
        if total_transactions >= SKIP_THRESHOLD:
            if debug:
                print(f"Reached {SKIP_THRESHOLD} transactions for holder {holder_address}, skipping.")
            return "SKIPPED"

        url = f"https://pro-api.solscan.io/v1.0/account/transactions?account={holder_address}&limit={limit}"
        if last_tx_hash:
            url += f"&beforeHash={last_tx_hash}"
        headers = {
            'accept': 'application/json',
            'token': API_KEY
        }

        response = requests.get(url, headers=headers)

        if debug:
            print(f"Response status code: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                if not data:
                    break

                total_transactions += len(data)
                latest_transfer_time = datetime.fromtimestamp(data[0]['blockTime'], tz=timezone.utc)
                earliest_transfer_time = datetime.fromtimestamp(data[len(data) - 1]['blockTime'], tz=timezone.utc)
                last_tx_hash = data[-1]['txHash']

                # Check number of returned transactions is at the end or latest transaction is older than 24 hours
                if len(data) < limit or current_time - latest_transfer_time > timedelta(hours=24):
                    return earliest_transfer_time

            except json.JSONDecodeError as e:
                if debug:
                    print(f"JSON decode error: {e}")
                break
        else:
            if debug:
                print(f"Error: {response.status_code} - {response.text}")
            break


def check_holder(holder, debug=True) -> str:
    if debug:
        print(f"Processing holder: {holder}")

    current_time = datetime.now(timezone.utc)
    blocktime = get_first_transfer_time(holder, current_time, debug)
    if blocktime == "SKIPPED":
        return f"{holder} - SKIPPED"
    elif isinstance(blocktime, datetime):
        time_diff = current_time - blocktime
        is_within_24_hours = time_diff <= timedelta(hours=24)
        status = "FRESH" if is_within_24_hours else "OLD"
        hours_diff = time_diff.total_seconds() / 3600

        if debug:
            print(
                f"First transfer block time for holder {holder}: {blocktime} "
                f"(within 24 hours: {is_within_24_hours} - {hours_diff:.2f} hours old)")

        return f"{holder} - {status}"
    else:
        return f"{holder} - UNKNOWN"


# Function to process files and update the JSON based on transfer times
def process_files_and_update_json(debug=False):
    coins_dir = 'coins'

    for filename in os.listdir(coins_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(coins_dir, filename)

            if debug:
                print(f"Processing file: {file_path}")

            try:
                with open(file_path, 'r') as file:
                    coin_data = json.load(file)
                if debug:
                    print(f"Original JSON data: {coin_data}")
            except Exception as e:
                if debug:
                    print(f"Error reading file: {file_path}, Error: {e}")
                continue

            holders = coin_data.get('holders', [])
            total_holders_count = len(holders)
            print(f"Assessing {total_holders_count} holder wallet addresses..")

            with multiprocessing.Pool(processes=multiprocessing.cpu_count() - 2) as pool:
                updated_holders = pool.map(check_holder, holders)

            # Update the holders in the original JSON data
            coin_data['holders'] = updated_holders

            # Write the updated data back to the JSON file
            try:
                with open(file_path, 'w') as file:
                    json.dump(coin_data, file, indent=4)
                if debug:
                    print(f"Updated JSON data: {coin_data}")
            except Exception as e:
                if debug:
                    print(f"Error writing file: {file_path}, Error: {e}")
