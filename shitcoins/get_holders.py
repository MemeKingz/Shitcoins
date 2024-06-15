import requests
from dotenv import load_dotenv
import os
import re

# Load environment variables from .env file
load_dotenv()

# Define a pattern for Solana addresses
solana_address_pattern = re.compile(r"^[A-HJ-NP-Za-km-z1-9]{44}$")


def is_valid_solana_address(address):
    """Check if the address matches the Solana address pattern."""
    return bool(solana_address_pattern.match(address))

def get_holders(token_address):
    api_key = os.getenv('SOLSCAN_API_KEY')
    if not api_key:
        raise ValueError("API key not found. Please set it in the .env file.")

    holder_addresses = []
    page = 0
    limit = 50  # Adjust the limit as per the API's pagination limit
    min_holders_required = int(os.getenv('MIN_HOLDER_COUNT'))

    while True:
        url = (f"https://pro-api.solscan.io/v1.0/token/holders?tokenAddress={token_address}&limit={limit}"
               f"&offset={page * limit}")
        headers = {
            'accept': 'application/json',
            'token': api_key
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            holders = data.get('data', [])
            if not holders:
                break  # No more data to fetch

            holder_addresses.extend([holder['owner'] for holder in holders if is_valid_solana_address(holder['owner'])])
            page += 1
        else:
            print(f"Error: {response.status_code} - {response.text}")
            break

    if len(holder_addresses) < min_holders_required:
        print(f"Token {token_address} has less than {min_holders_required} holders.")
        return []

    return holder_addresses

