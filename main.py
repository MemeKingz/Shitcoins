from scrapePumpFun import fetch_mint_addresses

def main():
    mint_addresses = fetch_mint_addresses()
    for address in mint_addresses:
        print(address)

if __name__ == "__main__":
    main()