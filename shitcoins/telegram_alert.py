import os
import json
import requests
from dotenv import load_dotenv

from shitcoins.util.time_util import datetime_from_utc_to_local

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
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
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
            firstBuystatistics = coin_data.get("first_buy_statistics", None)
            total_addresses = len(holders)
            fresh_addresses = sum(1 for holder in holders if holder['status'] == 'FRESH')

            percent_fresh = 0
            if total_addresses != 0:
                percent_fresh = (fresh_addresses / total_addresses) * 100
            coin_address = os.path.splitext(filename)[0]

            market_cap_formatted = "${:,.2f}".format(coin_data['market_info']['market_cap'])
            liquidity_formatted = "${:,.2f}".format(coin_data['market_info']['liquidity'])

            message = []

            try:
                message.append(f'<strong>{coin_data["market_info"]["token_name"]}</strong>')
            except KeyError:
                message.append('<strong>N/A</strong>')

            message.append('')

            try:
                message.append(f'<code>{coin_address}</code>')
            except KeyError:
                message.append('<code>N/A</code>')

            message.append('')

            try:
                message.append(f"🚀Market Cap: <strong>{market_cap_formatted}</strong>")
            except KeyError:
                message.append("🚀Market Cap: <strong>N/A</strong>")

            try:
                message.append(f"💦Liquidity: <strong>{liquidity_formatted}</strong>")
            except KeyError:
                message.append("💦Liquidity: <strong>N/A</strong>")
            try:
                utc_time = coin_data['market_info']['created_at_utc']
                if utc_time is not None:
                    local_creation_time = datetime_from_utc_to_local(utc_time)
                    message.append(f"🕗Token Age (ACST): <strong>{local_creation_time.ctime()}</strong>")
                else:
                    message.append(f"🕗Token Age (ACST): <strong>N/A</strong>")
            except KeyError:
                message.append(f"🕗Token Age (ACST): <strong>N/A</strong>")

            try:
                message.append(f"👥Holders: <strong>{total_addresses}</strong>")
            except KeyError:
                message.append("👥Holders: <strong>N/A</strong>")

            try:
                message.append(f"👀Fresh: <strong>{fresh_addresses} ({percent_fresh:.2f}%)</strong>")
            except KeyError:
                message.append("👀Fresh: <strong>N/A</strong>")

            # message.append("⛳Bundled: <strong>N/A</strong>")
            if firstBuystatistics is not None:
                try:
                    message.append(f"⛳Duplicate First Buys: "
                                   f"<strong>{firstBuystatistics['duplicate_count']}</strong>")
                except KeyError:
                    message.append("⛳Duplicate First Buys: <strong>N/A</strong>")
                try:
                    message.append(f"⛳% Of Total Billion Supply: "
                                   f"<strong>{firstBuystatistics['duplicate_pct']}%</strong>")
                except KeyError:
                    message.append("⛳& Of Total: <strong>N/A</strong>")

                try:
                    message.append(f"⛳# Of Wallets: "
                                   f"<strong>{firstBuystatistics['duplicate_wallet_count']}</strong>")
                except KeyError:
                    message.append("⛳# Of Wallets: <strong>N/A</strong>")

            message.append('')
            #get twitter link
            try:
                message.append('🐤Twitter: <a href="http://www.twitter.com/">N/A</a>')
            except KeyError:
                message.append('🐤Twitter: <a href="http://www.twitter.com/">N/A</a>')
            #get website link
            try:
                message.append('🌎Website: <a href="http://www.pornhub.com/">N/A</a>')
            except KeyError:
                message.append('🌎Website: <a href="http://www.pornhub.com/">N/A</a>')
            #get telegram channel link
            try:
                message.append('📬Telegram: <a href="http://www.telegram.com/">N/A</a>')
            except KeyError:
                message.append('📬Telegram: <a href="http://www.telegram.com/">N/A</a>')

            message.append('')

            alert = '\n'.join(message)

            print(alert)
            print('-' * 40)

            if bot_token and chat_id and percent_fresh >= SEND_PERCENT_THRESHOLD:
                response = send_telegram_message(alert, bot_token, chat_id)
                if debug:
                    print(f'Telegram response: {response.text}')

