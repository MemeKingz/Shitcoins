from telethon import TelegramClient
import re
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
phone = os.getenv('PHONE')
channel_username = os.getenv('CHANNEL_USERNAME')
MIN_MARKET_CAP = int(os.getenv('MIN_MARKET_CAP'))
MAX_MARKET_CAP = int(os.getenv('MAX_MARKET_CAP'))


class MintAddressFetcher:
    def __init__(self, seen_file='seen_addresses.json'):
        self.seen_file = seen_file
        self.seen_addresses = self.load_seen_addresses()
        self.telegram_client = TelegramClient('session_name', api_id, api_hash)

    def load_seen_addresses(self):
        if os.path.exists(self.seen_file):
            with open(self.seen_file, 'r') as file:
                return json.load(file)
        return []

    def save_seen_addresses(self):
        with open(self.seen_file, 'w') as file:
            json.dump(self.seen_addresses, file)

    async def fetch_pump_addresses_from_telegram(self, limit=100):
        await self.telegram_client.start(phone)

        addresses = []

        async for message in self.telegram_client.iter_messages(channel_username, limit=limit):
            text = message.text
            if text and "NEW CURVE COMPLETED" in text:
                lines = text.split('\n')
                address = None
                marketcap = None
                for line in lines:
                    if 'pump' in line:
                        potential_address = line.strip().strip('`')
                        if potential_address.endswith('pump'):
                            address = potential_address
                    if "Marketcap" in line:
                        marketcap_str = line.split("$")[1].strip()
                        try:
                            marketcap = self.clean_marketcap(marketcap_str)
                        except ValueError:
                            continue
                if address and marketcap:
                    if MIN_MARKET_CAP <= marketcap <= MAX_MARKET_CAP:
                        addresses.append(address)

        new_addresses = [address for address in addresses if address not in self.seen_addresses]
        self.seen_addresses.extend(new_addresses)
        self.save_seen_addresses()

        await self.telegram_client.disconnect()
        return new_addresses

    def clean_marketcap(self, marketcap_str):
        cleaned_str = re.sub(r'[^\d.]', '', marketcap_str)
        return float(cleaned_str)
