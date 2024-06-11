from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def scrape_solscan(tokenAddress):
    url_template = "https://solscan.io/token/{tokenAddress}#holders"
    formatted_url = url_template.format(tokenAddress=tokenAddress)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(formatted_url)
    time.sleep(10)
    
    try:
        table = driver.find_element(By.TAG_NAME, 'table')
        account_addresses = []
        for row in table.find_elements(By.TAG_NAME, 'tr'):
            columns = row.find_elements(By.TAG_NAME, 'td')
            if columns:  # Check if there are columns in the row
                account_addresses.append(columns[1].text.strip())

        return account_addresses
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        driver.quit()