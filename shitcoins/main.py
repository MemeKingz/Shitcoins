import json
import os
import asyncio
from time import sleep
from scrape_pump_fun import MintAddressFetcher
from get_holders import get_holders
from check_holder_transfers import process_files_and_update_json
from telegram_alert import alert
from dotenv import load_dotenv

# Load environment variables from .env file
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
        for address in pump_addresses:
            print(f"Getting holder addresses for {address}")
            holder_addresses = get_holders(address)
            
            if len(holder_addresses) >= 50:
                address_data = {
                    "coin address": address,
                    "holders": holder_addresses
                }
                with open(f'coins/{address}.json', 'w') as json_file:
                    json.dump(address_data, json_file, indent=4)
                print(f"Saved {address} with {len(holder_addresses)} addresses.")
            else:
                print(f"Skipped {address} with only {len(holder_addresses)} addresses.")
        
        process_files_and_update_json(debug=True)
        alert(bot_token=BOT_TOKEN, chat_id=CHAT_ID)
        
        for file in os.listdir('coins'):
            if file.endswith('.json'):
                os.remove(os.path.join('coins', file))

        print("Iteration complete. Waiting for next run.")
        
        sleep(LOOP_DELAY)

if __name__ == "__main__":
    asyncio.run(main())
