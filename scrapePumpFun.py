from telethon import TelegramClient
import re

api_id = '29624477'
api_hash = '1bb44d4c8505ee865d5df38759d388b5'

client = TelegramClient('session_name', api_id, api_hash)

def extract_mint_address(text):
    mint = re.search(r'🧪 \*\*Mint\*\*: `(.*?)`', text)
    if mint:
        return mint.group(1)
    return None

async def fetch_mint_addresses(limit=100):
    await client.start()
    
    entity = await client.get_entity('pumpfundetector')

    mint_addresses = []

    async for message in client.iter_messages(entity, limit=limit):
        mint_address = extract_mint_address(message.text)
        if mint_address:
            mint_addresses.append(mint_address)

    return mint_addresses
