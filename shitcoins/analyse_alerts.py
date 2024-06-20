import os
import json
import requests
from datetime import datetime, timedelta
from collections import namedtuple

DexMetric = namedtuple('DexMetric', ['total_fdv', 'fdv_count', 'liquidity', 'price', 'token_name'])
MarketInfo = namedtuple('MarketInfo', ['market_cap', 'token_name', 'liquidity', 'price'])

def get_market_cap_from_dexscreener(address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        address_to_dex_metric = {}
        for pair in data.get('pairs', []):
            if address not in address_to_dex_metric:
                address_to_dex_metric[address] = DexMetric(
                    total_fdv=pair['fdv'],  # Fully Diluted Valuation
                    fdv_count=1,
                    liquidity=float(pair['liquidity']['usd']),
                    price=float(pair['priceUsd']),
                    token_name=pair['baseToken']['name']
                )
        
        address_to_market_info = {}
        for addr, dex_metric in address_to_dex_metric.items():
            market_cap = float(dex_metric.total_fdv / dex_metric.fdv_count)
            address_to_market_info[addr] = MarketInfo(
                market_cap=market_cap,
                token_name=dex_metric.token_name,
                liquidity=dex_metric.liquidity,
                price=dex_metric.price
            )
            print(f"Success: Calculated market info for {dex_metric.token_name} with DexScreener API")
        
        return address_to_market_info
    else:
        print(f"Failed to fetch data for {address}")
        return None

def append_to_json_file(filepath, data):
    if os.path.exists(filepath):
        with open(filepath, 'r+') as file:
            try:
                existing_data = json.load(file)
                if isinstance(existing_data, list):
                    existing_data.extend(data)
                else:
                    existing_data = data
            except json.JSONDecodeError:
                existing_data = data
            file.seek(0)
            json.dump(existing_data, file, indent=4)
    else:
        with open(filepath, 'w') as file:
            json.dump(data, file, indent=4)

def analyse():
    # Make the path absolute
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_folder = os.path.join(script_dir, 'alerts')
    results = []
    try:
        filenames = os.listdir(json_folder)
    except FileNotFoundError:
        print(f"The directory {json_folder} does not exist.")
        return
    except PermissionError:
        print(f"Permission denied to access the directory {json_folder}.")
        return

    for filename in filenames:
        if filename.endswith('.json'):
            filepath = os.path.join(json_folder, filename)
            try:
                with open(filepath, 'r') as file:
                    data = json.load(file)
            except json.JSONDecodeError:
                print(f"Error decoding JSON from file {filepath}. Skipping.")
                continue
            except IOError:
                print(f"Error reading file {filepath}. Skipping.")
                continue
                
            if isinstance(data, list):
                print(f"Skipping {filepath} because it contains a list.")
                continue

            name = data.get('name', 'Unknown')
            address = data.get('address', 'Unknown')
            market_cap_str = data.get('market cap', '0').replace('$', '').replace(',', '')
            market_cap = float(market_cap_str) if market_cap_str else 0
            time_str = data.get('time')
            try:
                time = datetime.fromisoformat(time_str)
            except ValueError:
                print(f"Error parsing time {time_str} in file {filepath}. Skipping.")
                continue

            # Calculate the time 6 hours after the given time
            time_6_hours_later = time + timedelta(seconds=6)
                
            # Check if the current time is past the time_6_hours_later
            if datetime.now() < time_6_hours_later:
                print(f"Skipping {name}, will check after {time_6_hours_later}")
                continue
                
            # Get the market cap from Dexscreener
            market_info = get_market_cap_from_dexscreener(address)
                
            if market_info and address in market_info:
                new_market_cap = market_info[address].market_cap
                percentage_change = ((new_market_cap - market_cap) / market_cap) * 100 if market_cap != 0 else 0
                
                result = {
                    "name": name,
                    "address": address,
                    "original_market_cap": market_cap,
                    "new_market_cap": new_market_cap,
                    "market_cap_difference": new_market_cap - market_cap,
                    "percentage_change": percentage_change,
                }
                results.append(result)

                # Delete the original JSON file
                try:
                    os.remove(filepath)
                    print(f"Deleted file: {filepath}")
                except Exception as e:
                    print(f"Error deleting file {filepath}: {e}")

    # Write results to a JSON file with the current date as the name
    current_date = datetime.now().strftime('%Y-%m-%d')
    output_filepath = os.path.join(json_folder, f"{current_date}.json")
    append_to_json_file(output_filepath, results)

if __name__ == "__main__":
    analyse()
