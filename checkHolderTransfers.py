import os
import json
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Function to parse time string from the webpage
def parse_time(time_str):
    parts = time_str.split()
    if "minute" in time_str:
        minutes = int(parts[0]) if parts[0].isdigit() else int(parts[1])
        return datetime.now() - timedelta(minutes=minutes)
    elif "hour" in time_str:
        hours = int(parts[0]) if parts[0].isdigit() else int(parts[1])
        return datetime.now() - timedelta(hours=hours)
    elif "day" in time_str:
        days = int(parts[0]) if parts[0].isdigit() else int(parts[1])
        return datetime.now() - timedelta(days=days)
    elif "month" in time_str:
        months = int(parts[0]) if parts[0].isdigit() else int(parts[1])
        return datetime.now() - timedelta(days=months * 30)
    elif "year" in time_str:
        years = int(parts[0]) if parts[0].isdigit() else int(parts[1])
        return datetime.now() - timedelta(days=years * 365)
    else:
        return datetime.now()  # Fallback to current time if parsing fails

# Function to scrape Solscan for a given holder address
def check_holder_transfers(holder_address, debug=False):
    base_url = f"https://solscan.io/account/{holder_address}#transfers"
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    wait = WebDriverWait(driver, 10)  # Initialize WebDriverWait

    try:
        driver.get(base_url)
        if debug:
            print(f"Navigating to {base_url}")
        # Wait for the page to load
        time.sleep(3.5)

        # Automate some clicks and scrolling
        try:
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(0.3)  # Wait to ensure scrolling takes effect

            # Wait for the button to be clickable and then click
            button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.rounded-md:nth-child(5)')))
            button.click()

            # Wait for 5 seconds
            time.sleep(1.1)

            # Extract the table data
            table = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'table')))
            rows = table.find_elements(By.TAG_NAME, 'tr')
            if not rows or len(rows) == 1:
                if debug:
                    print("No transfers found or only header row present.")
                return None

            # Extract time from the last row and print it
            last_row = rows[-1]
            columns = last_row.find_elements(By.TAG_NAME, 'td')
            time_of_transfer = columns[2].text.strip()

            # Print the extracted time
            if debug:
                print(f"Last transfer time: {time_of_transfer}")

            return parse_time(time_of_transfer)

        except Exception as e:
            if debug:
                print(f"Error during automation: {e}")
            return None
    finally:
        driver.quit()

# Function to process files and update JSON based on transfer times
def process_files(debug=False):
    coins_dir = 'coins'
    for filename in os.listdir(coins_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(coins_dir, filename)

            if debug:
                print(f"Processing file: {file_path}")

            try:
                with open(file_path, 'r') as file:
                    coin_data = json.load(file)
                if debug:
                    print(f"Original JSON data: {coin_data}")
            except Exception as e:
                if debug:
                    print(f"Error reading file: {file_path}, Error: {e}")
                continue

            holders = coin_data.get('holders', [])
            updated_holders = []

            for holder in holders:
                if debug:
                    print(f"Processing holder: {holder}")
                transfer_time = check_holder_transfers(holder, debug)

                if transfer_time:
                    if transfer_time < datetime.now() - timedelta(days=1):
                        updated_holders.append(f"{holder} - OLD")
                    else:
                        updated_holders.append(f"{holder} - FRESH")
                else:
                    updated_holders.append(f"{holder} - UNKNOWN")

            if debug:
                print(f"Original holders: {holders}")
                print(f"Updated holders: {updated_holders}")

            coin_data['holders'] = updated_holders

            try:
                with open(file_path, 'w') as file:
                    json.dump(coin_data, file, indent=4)
                if debug:
                    print(f"Successfully updated the file: {file_path}")
                    print(f"Updated JSON data: {coin_data}")
            except Exception as e:
                if debug:
                    print(f"Error writing to file: {file_path}, Error: {e}")
