from telethon import TelegramClient, events
import re


api_id = '29624477'
api_hash = '1bb44d4c8505ee865d5df38759d388b5'

client = TelegramClient('session_name', api_id, api_hash)

def extract_mint_address(text):
    mint = re.search(r'🧪 \*\*Mint\*\*: `(.*?)`', text)
    if mint:
        return mint.group(1)
    return None

async def main():
    await client.start()

    # Replace 'channel_or_group_username' with the username of the channel/group you want to scrape
    entity = await client.get_entity('pumpfundetector')

    mint_addresses = []

    # Fetch the last 100 messages
    async for message in client.iter_messages(entity, limit=100):
        mint_address = extract_mint_address(message.text)
        if mint_address:
            mint_addresses.append(mint_address)

    # Print the list of mint addresses
    for address in mint_addresses:
        print(address)

# Run the client
with client:
    client.loop.run_until_complete(main())