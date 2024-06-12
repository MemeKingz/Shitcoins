import json
import os
import asyncio
from scrapePumpFun import MintAddressFetcher
from solscannerScrape import scrape_solscan

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
    
    print("goodbye")

if __name__ == "__main__":
    asyncio.run(main())
