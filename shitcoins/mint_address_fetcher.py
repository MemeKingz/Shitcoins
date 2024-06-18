from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict

from telethon import TelegramClient
import asyncio
import os
import json
import logging
import requests
from dotenv import load_dotenv

from shitcoins.model.coin_data import CoinData
from shitcoins.model.dex_metric import DexMetric
from shitcoins.model.market_info import MarketInfo

# Load environment variables from .env file
load_dotenv()

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
phone = os.getenv('PHONE')
channel_username = os.getenv('CHANNEL_USERNAME')
FETCH_LIMIT = int(os.getenv('FETCH_LIMIT'))
API_KEY = os.getenv('SOLSCAN_API_KEY')
DEX_DELAY_SEC = int(os.getenv('DEX_DELAY_SEC'))
DEX_RETRY_ATTEMPTS = int(os.getenv('DEX_RETRY_ATTEMPTS'))

LOGGER = logging.getLogger(__name__)


class MintAddressFetcher:
    def __init__(self, seen_file='seen_addresses.json'):
        self.seen_file = seen_file
        self.seen_addresses = self._load_seen_addresses()
        self.telegram_client = TelegramClient('session_name', api_id, api_hash)

    def _load_seen_addresses(self):
        if os.path.exists(self.seen_file):
            with open(self.seen_file, 'r') as file:
                return json.load(file)
        return []

    def _save_seen_addresses(self):
        with open(self.seen_file, 'w') as file:
            json.dump(self.seen_addresses, file)

    def check_if_coin_is_bundled(self, coin_address: str) -> bool:
        """
        Determine if a coin is bundled by checking if its latest and 10th transactions have the same timestamp
        On errors determining this, assume it is not bundled
        :param coin_address
        :return boolean True if bundled, False if not
        """
        max_transactions_per_request = 10

        url = (f"https://pro-api.solscan.io/v1.0/token/transfer?tokenAddress={coin_address}"
               f"&limit={max_transactions_per_request}")
        headers = {
            'accept': 'application/json',
            'token': API_KEY
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            try:
                data = response.json()['items']
                if not data:
                    return False

                first_transaction_timestamp = (datetime.fromtimestamp(data[0]['blockTime'],
                                                                      tz=timezone.utc)
                                               .replace(microsecond=0))

                earlier_transaction_timestamp = (datetime.fromtimestamp(data[len(data) - 1]['blockTime'],
                                                                        tz=timezone.utc)
                                                 .replace(microsecond=0))
                if earlier_transaction_timestamp == first_transaction_timestamp:
                    return True
                else:
                    return False


            except json.JSONDecodeError as e:
                LOGGER.error(f"JSON decode error: {e}")
                return False
        elif response.status_code == 504:
            LOGGER.error(f"504 error - unknown  coin address: {coin_address}")
            return False
        else:
            LOGGER.error(f"Error: {response.status_code} - {response.text}")
            return False

    def fetch_pump_address_info_dexscreener(self, pump_addresses: List[str]) -> Dict[str, MarketInfo]:
        address_to_market_info: Dict[str, MarketInfo] = {}
        address_to_dex_metric: Dict[str, DexMetric] = {}
        url = 'https://api.dexscreener.com/latest/dex/tokens/'

        # One or multiple, comma-separated token addresses (up to 30 addresses)
        chunks_pump_addresses = [pump_addresses[x:x + 30] for x in range(0, len(pump_addresses), 30)]
        for chunk_pump_addresses in chunks_pump_addresses:
            addresses = ''
            for pump_address in chunk_pump_addresses:
                addresses += f"{pump_address},"

            url += addresses
            headers = {
                'accept': 'application/json'
            }

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if data['pairs'] is None:
                    LOGGER.error(f"dexscreener did not return market info for {addresses}")
                    continue

                for pair in data['pairs']:
                    addr = pair['baseToken']['address']
                    if addr in address_to_dex_metric:
                        dex_metric = address_to_dex_metric[addr]
                        dex_metric['total_fdv'] += pair['fdv']
                        dex_metric['fdv_count'] += 1
                    else:
                        # calculate average market_cap via average fdv,  but just use first pair's
                        # liquidity and price value
                        address_to_dex_metric[addr] = DexMetric(total_fdv=pair['fdv'], fdv_count=1,
                                                                liquidity=float(pair['liquidity']['usd']),
                                                                price=float(pair['priceUsd']),
                                                                token_name=pair['baseToken']['name'])

                for addr, dex_metric in address_to_dex_metric.items():
                    market_cap = float(dex_metric['total_fdv'] / dex_metric['fdv_count'])
                    address_to_market_info[addr] = MarketInfo(market_cap=market_cap,
                                                              token_name=dex_metric['token_name'],
                                                              liquidity=dex_metric['liquidity'],
                                                              price=dex_metric['price'])
                    LOGGER.info(f"Success: Calculated market info for {dex_metric['token_name']} "
                                f"with DexScreener API")
        return address_to_market_info


    async def fetch_pump_addresses_from_telegram(self) -> List[CoinData]:
        await self.telegram_client.start(phone)

        MIN_MARKET_CAP = float(os.getenv('MIN_MARKET_CAP'))
        MAX_MARKET_CAP = float(os.getenv('MAX_MARKET_CAP'))
        FETCH_LIMIT = int(os.getenv('FETCH_LIMIT', 100))
        channel_username = os.getenv('CHANNEL_USERNAME')
        
        telegram_addresses_market_cap: Dict[str, float] = {}

        async for message in self.telegram_client.iter_messages(channel_username, limit=FETCH_LIMIT):
            text = message.text
            if text:
                lines = text.split('\n')
                potential_address = None
                for line in lines:
                    if 'pump' in line:
                        potential_address = line.strip().strip('`')
                        if potential_address.endswith('pump'):
                            telegram_addresses_market_cap[potential_address] = 0
        await self.telegram_client.disconnect()

        new_addresses = [address for address in telegram_addresses_market_cap
                        if address not in self.seen_addresses]

        return_coins_data: List[CoinData] = []

        if new_addresses:
            attempts = 0

            while attempts < DEX_RETRY_ATTEMPTS:
                attempts += 1
                dexscreener_addr_to_market_info = self.fetch_pump_address_info_dexscreener(new_addresses)

                for new_address in new_addresses:
                    if new_address in dexscreener_addr_to_market_info:
                        if MIN_MARKET_CAP <= dexscreener_addr_to_market_info[new_address]['market_cap'] <= MAX_MARKET_CAP:
                            return_coins_data.append(CoinData(coin_address=new_address,
                                                            suspect_bundled=self.check_if_coin_is_bundled(new_address),
                                                            market_info=dexscreener_addr_to_market_info[new_address],
                                                            holders=[]))
                        else:
                            LOGGER.warning(f"Market cap for {new_address} is out of range.")

                if return_coins_data:
                    break
                else:
                    LOGGER.warning(f"Attempt {attempts} failed to find a coin within market cap range. Retrying in {DEX_DELAY_SEC} seconds.")
                    await asyncio.sleep(DEX_DELAY_SEC)

        self.seen_addresses.extend(new_addresses)
        self.seen_addresses = list(set(self.seen_addresses))
        self._save_seen_addresses()
        
        return return_coins_data

