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
            #old_addresses = sum(1 for holder in holders if holder['status'] == 'OLD')
            #bundler_addresses = sum(1 for holder in holders if holder['status'] == 'BUNDLER')

            percent_fresh = 0
            #percent_old = 0
            #percent_bundler = 0
            if total_addresses != 0:
                percent_fresh = (fresh_addresses / total_addresses) * 100
                #percent_old = (old_addresses / total_addresses) * 100
                #percent_bundler = (bundler_addresses / total_addresses) * 100

            coin_address = os.path.splitext(filename)[0]

            market_cap_formatted = "${:,.2f}".format(coin_data['market_info']['market_cap'])
            liquidity_formatted = "${:,.2f}".format(coin_data['market_info']['liquidity'])
            #price_formatted = '${:f}'.format(coin_data['market_info']['price'])

            message = [
                f'<strong>{coin_data["market_info"]["token_name"]}</strong>',
                '',
                f'<code>{coin_address}</code>',
                '',
                f"🚀Market Cap: <strong>{market_cap_formatted}</strong>",
                f"💦Liquidity: <strong>{liquidity_formatted}</strong>",
                f"🕗Token Age: <strong>N/A</strong>",
                f"👥Holders: <strong>{total_addresses}</strong>",
                f"👀Fresh: <strong>{fresh_addresses}</strong> - <strong>({percent_fresh:.2f}%)</strong>",
                f'⛳Bundled: <strong>{"Yes" if coin_data.get("suspect_bundled") else "No"}</strong>',
                '',
                f'🐤Twitter: <a href="http://www.twitter.com/">Link goes here</a>',
                f'🌎Website: <a href="http://www.pornhub.com/">Link goes here</a>',
                f'📬Telegram: <a href="http://www.telegram.com/">Link goes here</a>',
                ''
            ]

            alert = '\n'.join(message)

            print(alert)
            print('-' * 40)

            if bot_token and chat_id and percent_fresh >= SEND_PERCENT_THRESHOLD:
                response = send_telegram_message(alert, bot_token, chat_id)
                if debug:
                    print(f'Telegram response: {response.text}')

