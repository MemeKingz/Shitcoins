from scrapePumpFun import fetch_mint_addresses
from solscannerScrape import scrape_solscan

def main():
    mint_addresses = fetch_mint_addresses()
    for address in mint_addresses:
        print(scrape_solscan(address))

if __name__ == "__main__":
    main()