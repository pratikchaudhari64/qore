import requests
import urllib.parse
import json
import hashlib
import pandas as pd

API_KEY = 'ldzz1f2494zst7yw'
API_SECRET = '6wxo6gefdin0hhtw106j5nmqkyuao12k'

root_api = "https://api.kite.trade"

login_url = f"https://kite.zerodha.com/connect/login?v=3&api_key={API_KEY}"

# redirected_url = "https://localhost:3000/?action=login&type=login&status=success&request_token=DKR1zH5qZc3a4y8RUSBHBHzKfniDPD7J"
REQUEST_TOKEN_RECEIVED = "DKR1zH5qZc3a4y8RUSBHBHzKfniDPD7J"

KITE_TOKEN_URL = root_api + '/' + "session/token"


ACCESS_TOKEN = "Gq1DnCBcr9Ba4WeQDD1DGdgq8PygNBdd"

PUBLIC_TOKEN = "LVMHwGErpyRv468NiXOWJ4tnULLQDoN9"

ENCTOKEN = "9fDGEvIi9HBrgcvTM0q47UHb8smxo99kXKjXrMslIhOncUNiQbMSzAcYipnzTRwZPgHxpYt6bTnHIHObAVIcR48OVIAXwa8zpiDPQeI39hoeCx6brIpiIodYRls5d7s="


headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {API_KEY}:{ACCESS_TOKEN}"
        }

def generate_checksum(request_token_value):
    """Generates the SHA256 checksum required by Kite Connect for token exchange.
    The checksum is SHA256(api_key + request_token + api_secret).
    """
    text_to_hash = f"{API_KEY}{request_token_value}{API_SECRET}"
    return hashlib.sha256(text_to_hash.encode('utf-8')).hexdigest()

def get_access_token(request_token_value):
    """
    Exchanges the request_token for an access_token using Kite's token API.
    """
    print(f"Attempting to exchange request_token: {request_token_value} for access_token...")

    # Data payload for the POST request
    payload = {
        "api_key": API_KEY,
        "request_token": request_token_value,
        "checksum": generate_checksum(request_token_value)
    }

    # Headers required by Kite API
    headers = {
        "X-Kite-Version": "3", # Specify API version
        "Content-Type": "application/x-www-form-urlencoded" # Required for POST data
    }

    try:
        # Make the POST request to the token API endpoint
        response = requests.post(KITE_TOKEN_URL, data=payload, headers=headers)
        return response
    
    except:
        print("Something went wrong while posting request...")


def get_user_profile():
    
    profile_response = requests.get("https://api.kite.trade/user/profile", headers=headers)
    print(profile_response.json())

def get_holdings():
    holdings_resp = requests.get("https://api.kite.trade/portfolio/holdings", headers=headers)
    return holdings_resp.json()

def get_positions():
    holdings_resp = requests.get("https://api.kite.trade/portfolio/positions", headers=headers)
    return holdings_resp.json()

def get_historical(instrument_token):
    base_url = f"https://api.kite.trade/instruments/historical/{instrument_token}/day"

    params = {
        "from": "2025-01-01 09:15:00",
        "to": "2025-04-30 09:20:00",
        "continuous": 1
    }

    response = requests.get(base_url, params=params, headers=headers)

    return response.json()



if __name__ == "__main__":
    
    # get_user_profile()
    holdings = get_holdings()
    print(pd.json_normalize(holdings['data']))

    # hist_data = get_historical(instrument_token=3861249)
    # print(hist_data)

    #  response = get_access_token(REQUEST_TOKEN_RECEIVED)
    # print(response.json())


    # print(login_url)
    # if access_token:
    #     print("\nAccess Token is ready for further API calls!")
    #     print(f"access token: {access_token}")
        # Now you can use this access_token for fetching holdings, profile, etc.
        # Example (assuming you have a function like make_kite_api_call from previous snippets):
        # headers = {
        #     "X-Kite-Version": "3",
        #     "Authorization": f"token {API_KEY}:{access_token}"
        # }
        # profile_response = requests.get("https://api.kite.trade/user/profile", headers=headers)
        # print(profile_response.json())
