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


# Function to calculate fresh and old percentages and send Telegram alerts
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
            fresh_addresses = sum(1 for holder in holders if holder['status'] == 'FRESH')
            old_addresses = sum(1 for holder in holders if holder['status'] == 'OLD')
            bundler_addresses = sum(1 for holder in holders if holder['status'] == 'BUNDLER')

            percent_fresh = 0
            percent_old = 0
            percent_bundler = 0
            if total_addresses != 0:
                percent_fresh = (fresh_addresses / total_addresses) * 100
                percent_old = (old_addresses / total_addresses) * 100
                percent_bundler = (bundler_addresses / total_addresses) * 100

            # Extract coin address from the filename (assuming filename is the coin address)
            coin_address = os.path.splitext(filename)[0]
            market_cap_formatted = "${:,.2f}".format(coin_data['market_info']['market_cap'])
            liquidity_formatted = "${:,.2f}".format(coin_data['market_info']['liquidity'])
            price_formatted = '${:f}'.format(coin_data['market_info']['price'])
            message = (
                f'🔥 INSIDER ALERT 🔥\n'
                f'Coin address: \n\n{coin_address}\n\n'
                f"Name: {coin_data['market_info']['token_name']}\n"
                f"Suspected bundled: {coin_data['suspect_bundled']}\n"
                f"Market cap: {market_cap_formatted}\n"
                f"Price: {price_formatted}\n"
                f"Liquidity: {liquidity_formatted}\n"
                f'Analyzed holders: {total_addresses}\n'
                f'Fresh holders: {fresh_addresses}\n'
                f'Old holders: {old_addresses}\n'
                f'Percentage of fresh holders: {percent_fresh:.2f}%\n'
                f'Percentage of old holders: {percent_old:.2f}%'
                f'Percentage of bundler holders: {percent_bundler:.2f}%'
            )

            print(message)
            print('-' * 40)

            # Send message to Telegram if percent_fresh is 10 or higher
            if bot_token and chat_id and percent_fresh >= SEND_PERCENT_THRESHOLD:
                response = send_telegram_message(message, bot_token, chat_id)
                if debug:
                    print(f'Telegram response: {response.text}')
