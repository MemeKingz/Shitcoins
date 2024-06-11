import requests

def fetch_mint_addresses(limit=10):
    url = "https://pumpapi.fun/api/get_newer_mints"
    params = {"limit": limit}

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        mint_addresses = data.get("mint", [])
        return mint_addresses
    else:
        print(f"Error retrieving data: {response.status_code}")
        return []