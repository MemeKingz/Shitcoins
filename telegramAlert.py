import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SEND_PERCENT_THRESHOLD = float(os.getenv('SEND_PERCENT_THRESHOLD'))

# Function to send message to Telegram
def send_telegram_message(message, bot_token, chat_id):
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, data=payload)
    return response

# Function to calculate fresh percentage and send Telegram alerts
def alert(coins_dir='coins', bot_token=None, chat_id=None, debug=False):
    for filename in os.listdir(coins_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(coins_dir, filename)
            
            if debug:
                print(f'Processing file: {file_path}')

            try:
                with open(file_path, 'r') as file:
                    coin_data = json.load(file)
                if debug:
                    print(f'Read JSON data: {coin_data}')
            except Exception as e:
                if debug:
                    print(f'Error reading file: {file_path}, Error: {e}')
                continue

            holders = coin_data.get('holders', [])
            total_addresses = len(holders)
            fresh_addresses = sum(1 for holder in holders if ' - FRESH' in holder)
            
            if total_addresses == 0:
                percent_fresh = 0
            else:
                percent_fresh = (fresh_addresses / total_addresses) * 100

            # Extract coin address from the filename (assuming filename is the coin address)
            coin_address = os.path.splitext(filename)[0]

            message = (
                f'TEST ALERT\n'
                f'🔥 INSIDER ALERT 🔥\n'
                f'Coin address: \n\n{coin_address}\n\n'
                f'Analyzed addresses: {total_addresses}\n'
                f'Fresh addresses: {fresh_addresses}\n'
                f'Percentage of fresh addresses: {percent_fresh:.2f}%'
            )

            print(message)
            print('-' * 40)

            # Send message to Telegram if percent_fresh is 10 or higher
            if bot_token and chat_id and percent_fresh >= SEND_PERCENT_THRESHOLD:
                response = send_telegram_message(message, bot_token, chat_id)
                if debug:
                    print(f'Telegram response: {response.text}')


alert(bot_token=BOT_TOKEN, chat_id=CHAT_ID)