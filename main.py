import json
import os
import asyncio
from scrapePumpFun import MintAddressFetcher
from solscannerScrape import scrape_solscan
from checkHolderTransfers import process_files
from telegramAlert import alert
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')


async def main():
    if not os.path.exists('coins'):
        os.makedirs('coins')
    
    fetcher = MintAddressFetcher()
    
    # Fetch pump addresses from Telegram
    pump_addresses = await fetcher.fetch_pump_addresses_from_telegram()
    for address in pump_addresses:
        print(f"Getting holder address for {address}")
        holder_addresses = scrape_solscan(address)
        
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
    process_files(debug=True)
    alert(bot_token=BOT_TOKEN, chat_id=CHAT_ID)
    print("goodbye")

if __name__ == "__main__":
    asyncio.run(main())
