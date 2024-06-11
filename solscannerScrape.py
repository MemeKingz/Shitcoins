from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def scrape_solscan(tokenAddress, debug=False):
    base_url = "https://solscan.io/token/{tokenAddress}?page={page}#holders"
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    
    page = 1
    account_addresses = []
    
    try:
        while True:
            formatted_url = base_url.format(tokenAddress=tokenAddress, page=page)
            driver.get(formatted_url)
            time.sleep(10)
            
            try:
                table = driver.find_element(By.TAG_NAME, 'table')
                rows = table.find_elements(By.TAG_NAME, 'tr')
                if not rows or len(rows) == 1:  # Assuming the header row is always present
                    break
                
                for row in rows[1:]:  # Skip header row
                    columns = row.find_elements(By.TAG_NAME, 'td')
                    if columns and columns[1].text.strip():
                        account_addresses.append(columns[1].text.strip())
                
                print(f"Page {page} scraped. Total addresses: {len(account_addresses)}")
                
                page += 1
            except IndexError:
                print(f"No more addresses found on page {page}. Exiting.")
                break
        
        if debug:
            for address in account_addresses:
                print(address)
        
        return account_addresses
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        driver.quit()

# Example usage for testing
# scrape_solscan("579t4FvQQ6JsWtoGrAVHWSK6AgRcw3XBJGaDefVL92e1", debug=True)