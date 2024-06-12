import requests
from dotenv import load_dotenv
import os
import json
import re
from datetime import datetime, timedelta, timezone

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv('SOLSCAN_API_KEY')

if not API_KEY:
    raise ValueError("API key not found. Please set it in the .env file.")

# Define a pattern for Solana addresses
solana_address_pattern = re.compile(r"^[A-HJ-NP-Za-km-z1-9]{32,44}$")

def is_valid_solana_address(address):
    """Check if the address matches the Solana address pattern."""
    return bool(solana_address_pattern.match(address))

# Function to get transfer data for a given holder address
def get_holder_transfers(holder_address, current_time, debug=False):
    if not is_valid_solana_address(holder_address):
        if debug:
            print(f"Invalid Solana address: {holder_address}")
        return []

    limit = 50
    transfers = []
    last_tx_hash = ""
    while True:
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

                # Check if the first transaction in the batch is older than 24 hours
                first_transfer_time = datetime.fromtimestamp(data[0]['blockTime'], tz=timezone.utc)
                if current_time - first_transfer_time > timedelta(hours=24):
                    break

                transfers.extend([{'blockTime': tx['blockTime']} for tx in data if 'blockTime' in tx])
                last_tx_hash = data[-1]['txHash']

                if len(data) < limit:
                    break
            except json.JSONDecodeError as e:
                if debug:
                    print(f"JSON decode error: {e}")
                break
        else:
            if debug:
                print(f"Error: {response.status_code} - {response.text}")
            break

    return transfers

# Function to get the time of the first transfer
def get_first_transfer_time(holder_address, current_time, debug=False):
    transfers = get_holder_transfers(holder_address, current_time, debug)
    if not transfers:
        return None

    first_transfer_time = min(transfer['blockTime'] for transfer in transfers)
    return first_transfer_time

# Function to process files and update the JSON based on transfer times
def process_files_and_update_json(debug=False):
    coins_dir = 'coins'
    current_time = datetime.now(timezone.utc)
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
            updated_holders = []
            total_holders = len(holders)
            for index, holder in enumerate(holders, start=1):
                if debug:
                    print(f"Processing holder: {holder}")
                blocktime = get_first_transfer_time(holder, current_time, debug)
                if blocktime:
                    blocktime_dt = datetime.fromtimestamp(blocktime, tz=timezone.utc)
                    time_diff = current_time - blocktime_dt
                    is_within_24_hours = time_diff <= timedelta(hours=24)
                    status = "FRESH" if is_within_24_hours else "OLD"
                    hours_diff = time_diff.total_seconds() / 3600
                    updated_holders.append(f"{holder} - {status}")
                    if debug:
                        print(f"{index}/{total_holders} - First transfer block time for holder {holder}: {blocktime} (within 24 hours: {is_within_24_hours} - {hours_diff:.2f} hours old)")
                else:
                    updated_holders.append(f"{holder} - UNKNOWN")

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

# Example usage
process_files_and_update_json(debug=True)
