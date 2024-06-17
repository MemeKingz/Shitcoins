import json
import os
import asyncio
import logging
from time import sleep

from mint_address_fetcher import MintAddressFetcher
from get_holders import get_holders
from check_holder_transfers import multiprocess_coin_holders
from telegram_alert import alert
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
LOOP_DELAY = int(os.getenv('LOOP_DELAY'))

logging.basicConfig(level=logging.INFO)


async def main():
    if not os.path.exists('coins'):
        os.makedirs('coins')

    fetcher = MintAddressFetcher()

    while True:
        coins_data = await fetcher.fetch_pump_addresses_from_telegram()
        # coin holders are ordered by percentage of the coin they hold (supply)
        for coin_data in coins_data:
            print(f"Getting holder addresses for {coin_data['coin_address']}")
            holders = get_holders(coin_data['coin_address'])

            if len(holders) >= int(os.getenv('MIN_HOLDER_COUNT')):
                coin_data['holders'] = holders
                with open(f"coins/{coin_data['coin_address']}.json", 'w') as json_file:
                    json.dump(coin_data, json_file, indent=4)
                print(f"Saved {coin_data['coin_address']} with {len(holders)} addresses.")
            else:
                print(f"Skipped {coin_data['coin_address']} with only {len(holders)} addresses.")

            coin_data_with_updated_holders = multiprocess_coin_holders(coin_data)

            # Write the updated data back to the JSON file
            with open(f"coins/{coin_data['coin_address']}.json", 'w') as json_file:
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
