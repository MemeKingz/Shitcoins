import os
import json
import requests
from datetime import datetime, timedelta
from pytz import timezone
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SEND_PERCENT_THRESHOLD = float(os.getenv('SEND_PERCENT_THRESHOLD'))

# Global variable to track if the report has been sent today
report_sent = False
last_checked_date = None

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

def analysis_report():
    global report_sent
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_folder = os.path.join(base_dir, 'alerts')
    current_date = datetime.now(timezone('Australia/Adelaide')).strftime('%Y-%m-%d')
    report_filepath = os.path.join(json_folder, f"{current_date}.json")

    print(f"Checking for report file at: {report_filepath}")

    if os.path.exists(json_folder):
        print(f"Contents of {json_folder}: {os.listdir(json_folder)}")
    else:
        print(f"The directory {json_folder} does not exist.")

    data_list = []

    if os.path.exists(report_filepath):
        try:
            with open(report_filepath, 'r') as file:
                report_data = json.load(file)

                if isinstance(report_data, list):
                    data_list.extend(report_data)
                elif isinstance(report_data, dict):
                    data_list.append(report_data)
                else:
                    print(f"Skipping {report_filepath} because it contains an unsupported format.")
                    return

            if not data_list:
                print(f"No data in the report file {report_filepath}. Skipping Telegram message.")
                return

            message = []
            message.append("<strong>DAILY REPORT</strong>")
            message.append("Alerts reviewed 6 hours post-channel posting.")
            message.append("")

            for item in data_list:
                try:
                    message.append(f'<strong>{item["name"]}</strong>')
                except KeyError:
                    message.append('<strong>N/A</strong>')

                try:
                    message.append(f'<code>{item["address"]}</code>')
                except KeyError:
                    message.append('<code>N/A</code>')

                try:
                    market_cap_formatted = "${:,.2f}".format(item['original_market_cap'])
                    message.append(f"🚀Original Market Cap: <strong>{market_cap_formatted}</strong>")
                except KeyError:
                    message.append("🚀Original Market Cap: <strong>N/A</strong>")

                try:
                    market_cap_formatted = "${:,.2f}".format(item['new_market_cap'])
                    message.append(f"🚀New Market Cap: <strong>{market_cap_formatted}</strong>")
                except KeyError:
                    message.append("🚀New Market Cap: <strong>N/A</strong>")

                try:
                    market_cap_difference_formatted = "${:,.2f}".format(item['market_cap_difference'])
                    message.append(f"💹Market Cap Difference: <strong>{market_cap_difference_formatted}</strong>")
                except KeyError:
                    message.append("💹Market Cap Difference: <strong>N/A</strong>")

                try:
                    percentage_change = item['percentage_change']
                    message.append(f"📈Percentage Change: <strong>{percentage_change:.2f}%</strong>")
                except KeyError:
                    message.append("📈Percentage Change: <strong>N/A</strong>")

                message.append('')

            alert_message = '\n'.join(message)
            response = send_telegram_message(alert_message, BOT_TOKEN, CHAT_ID)
            if response.status_code == 200:
                print(f'Successfully sent report to Telegram.')
            else:
                print(f'Failed to send report to Telegram. Response: {response.text}')

            os.remove(report_filepath)
            print(f'Deleted report file: {report_filepath}')
            report_sent = True
        except json.JSONDecodeError:
            print(f"Error decoding JSON from file {report_filepath}.")
        except Exception as e:
            print(f'Error processing report file: {report_filepath}, Error: {e}')
    else:
        print(f'No report file found for {current_date}.')


def check_time_and_send_report():
    global report_sent, last_checked_date
    adelaide_time = datetime.now(timezone('Australia/Adelaide'))
    current_date = adelaide_time.strftime('%Y-%m-%d')

    if last_checked_date != current_date:
        report_sent = False
        last_checked_date = current_date

    if adelaide_time.hour == 0 and adelaide_time.minute < 5 and not report_sent:
        analysis_report()
        report_sent = True

def alert(coins_dir='coins', bot_token=None, chat_id=None, debug=False):
    output_dir = os.path.join(coins_dir, '..', 'alerts')

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
            
            percent_fresh = 0
            if total_addresses != 0:
                percent_fresh = (fresh_addresses / total_addresses) * 100

            coin_address = os.path.splitext(filename)[0]

            market_cap_formatted = "${:,.2f}".format(coin_data['market_info']['market_cap'])
            liquidity_formatted = "${:,.2f}".format(coin_data['market_info']['liquidity'])
            price_formatted = '${:f}'.format(coin_data['market_info']['price'])

            message = []
            name = ""
            address = ""
            market_cap = ""
            liquidity = ""

            try:
                message.append(f'<strong>{coin_data["market_info"]["token_name"]}</strong>')
                name = coin_data["market_info"]["token_name"]
            except KeyError:
                message.append('<strong>N/A</strong>')

            message.append('')

            try:
                message.append(f'<code>{coin_address}</code>')
                address = coin_address
            except KeyError:
                message.append('<code>N/A</code>')

            message.append('')

            try:
                message.append(f"🚀Market Cap: <strong>{market_cap_formatted}</strong>")
                market_cap = market_cap_formatted
            except KeyError:
                message.append("🚀Market Cap: <strong>N/A</strong>")

            try:
                message.append(f"💦Liquidity: <strong>{liquidity_formatted}</strong>")
                liquidity = liquidity_formatted
            except KeyError:
                message.append("💦Liquidity: <strong>N/A</strong>")

            try:
                message.append(f"🕗Token Age: <strong>N/A</strong>")
            except KeyError:
                message.append(f"🕗Token Age: <strong>N/A</strong>")

            try:
                message.append(f"👥Holders: <strong>{total_addresses}</strong>")
            except KeyError:
                message.append("👥Holders: <strong>N/A</strong>")

            try:
                message.append(f"👀Fresh: <strong>{fresh_addresses} ({percent_fresh:.2f}%)</strong>")
            except KeyError:
                message.append("👀Fresh: <strong>N/A</strong>")

            try:
                message.append(f'⛳Bundled: <strong>{"Yes" if coin_data.get("suspect_bundled") else "No"}</strong>')
            except KeyError:
                message.append("⛳Bundled: <strong>N/A</strong>")

            message.append('')

            try:
                message.append('🐤Twitter: <a href="http://www.twitter.com/">N/A</a>')
            except KeyError:
                message.append('🐤Twitter: <a href="http://www.twitter.com/">N/A</a>')

            try:
                message.append('🌎Website: <a href="http://www.pornhub.com/">N/A</a>')
            except KeyError:
                message.append('🌎Website: <a href="http://www.pornhub.com/">N/A</a>')

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
                print("hello")
                if debug:
                    print(f'Telegram response: {response.text}')

                alert_data = {
                    'name': name,
                    'address': address,
                    'market cap': market_cap,
                    'price': price_formatted,
                    'Liquidity': liquidity,
                    'time': datetime.now().isoformat()
                }

                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                alert_filename = f'{coin_address}.json'
                alert_filepath = os.path.join(output_dir, alert_filename)

                try:
                    with open(alert_filepath, 'w') as alert_file:
                        json.dump(alert_data, alert_file, indent=4)
                    if debug:
                        print(f'Alert saved to file: {alert_filepath}')
                except Exception as e:
                    if debug:
                        print(f'Error saving alert to file: {alert_filepath}, Error: {e}')


