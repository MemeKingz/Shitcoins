import requests
import json
import os

class MintAddressFetcher:
    def __init__(self, seen_file='seen_addresses.json'):
        self.seen_file = seen_file
        self.seen_addresses = self.load_seen_addresses()

    def load_seen_addresses(self):
        if os.path.exists(self.seen_file):
            with open(self.seen_file, 'r') as file:
                return json.load(file)
        return []

    def save_seen_addresses(self):
        with open(self.seen_file, 'w') as file:
            json.dump(self.seen_addresses, file)

    def fetch_mint_addresses(self, limit=4): #change limit to increase coin scrape 
        url = "https://pumpapi.fun/api/get_newer_mints"
        params = {"limit": limit}

        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            mint_addresses = data.get("mint", [])
            new_addresses = [
                address for address in mint_addresses 
                if 'pump' in address and address not in self.seen_addresses
            ]
            self.seen_addresses.extend(new_addresses)
            self.save_seen_addresses()
            return new_addresses
        else:
            print(f"Error retrieving data: {response.status_code}")
            return []
