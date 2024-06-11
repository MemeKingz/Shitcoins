from scrapePumpFun import client, fetch_mint_addresses

async def main():
    mint_addresses = await fetch_mint_addresses()
    
    for address in mint_addresses:
        print(address)

# Run the main function
with client:
    client.loop.run_until_complete(main())
