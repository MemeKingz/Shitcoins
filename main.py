import json
import os
from scrapePumpFun import MintAddressFetcher
from solscannerScrape import scrape_solscan

def main():
    # Ensure the 'coins' directory exists
    if not os.path.exists('coins'):
        os.makedirs('coins')
    
    fetcher = MintAddressFetcher()
    mint_addresses = fetcher.fetch_mint_addresses()
    
    for address in mint_addresses:
        print(f"Getting holder address for {address}")
        holder_addresses = scrape_solscan(address)
        
        if len(holder_addresses) >= 5:
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
    main()
