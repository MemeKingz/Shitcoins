from telethon import TelegramClient, events
import re


api_id = '29624477'
api_hash = '1bb44d4c8505ee865d5df38759d388b5'

client = TelegramClient('session_name', api_id, api_hash)

def filter_message(text):
    name = re.search(r'💸 \*\*Name\*\*: `(.*?)`', text)
    symbol = re.search(r'💫 \*\*Symbol\*\*: `(.*?)`', text)
    mcap = re.search(r'💰 \*\*MCAP\*\*: `(.*?)`', text)
    mint = re.search(r'🧪 \*\*Mint\*\*: `(.*?)`', text)
    
    if name and symbol and mcap and mint:
        return f"Name: `{name.group(1)}`\nSymbol: `{symbol.group(1)}`\nMCAP: `{mcap.group(1)}`\nMint: `{mint.group(1)}`\n"
    return None

async def main():
    await client.start()

    entity = await client.get_entity('pumpfundetector')

    async for message in client.iter_messages(entity, limit=100):
        filtered_message = filter_message(message.text)
        if filtered_message:
            print(filtered_message)

with client:
    client.loop.run_until_complete(main())