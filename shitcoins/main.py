import json
import os
import asyncio
from time import sleep

from scrape_pump_fun import MintAddressFetcher
from get_holders import get_holders
from check_holder_transfers import multiprocess_coin_holders
from telegram_alert import alert
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
LOOP_DELAY = int(os.getenv('LOOP_DELAY'))


async def main():
    if not os.path.exists('coins'):
        os.makedirs('coins')

    fetcher = MintAddressFetcher()

    while True:
        pump_addresses = await fetcher.fetch_pump_addresses_from_telegram()
        for pump_address in pump_addresses:
            print(f"Getting holder addresses for {pump_address}")
            holder_addresses = get_holders(pump_address)

            if len(holder_addresses) >= int(os.getenv('MIN_HOLDER_COUNT')):
                address_data = {
                    "coin address": pump_address,
                    "holders": holder_addresses
                }
                with open(f'coins/{pump_address}.json', 'w') as json_file:
                    json.dump(address_data, json_file, indent=4)
                print(f"Saved {pump_address} with {len(holder_addresses)} addresses.")
            else:
                print(f"Skipped {pump_address} with only {len(holder_addresses)} addresses.")

            coin_data_with_updated_holders = multiprocess_coin_holders(pump_address, holder_addresses)

            with open(f'coins/{pump_address}.json', 'w') as json_file:
                try:
                    json.dump(coin_data_with_updated_holders, json_file, indent=4)
                    print(f"Updated JSON data: {coin_data_with_updated_holders}")
                except Exception as e:
                    print(f"Error writing file: {json_file}, Error: {e}")

        alert(bot_token=BOT_TOKEN, chat_id=CHAT_ID)

        for file in os.listdir('coins'):
            if file.endswith('.json'):
                os.remove(os.path.join('coins', file))

        print("Iteration complete. Waiting for next run.")

        sleep(LOOP_DELAY)


if __name__ == "__main__":
    asyncio.run(main())
