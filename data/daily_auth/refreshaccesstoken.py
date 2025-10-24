import time
import logging
import sys
import os
# import webbrowser
from datetime import datetime
import pandas as pd
import requests
from urllib.parse import urlparse, parse_qs
from fastapi import FastAPI, Request
import uvicorn
from multiprocessing import Process
import pickle


# --- Configure Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

session_data_cache= {}

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

daily_auth_dotenv_path = os.path.join(project_root, "data", "daily_auth", ".env")
db_auth_env = os.path.join(project_root, "data", ".env")
services_env = os.path.join(project_root, "services", ".env")
root_env = os.path.join(project_root, ".env")

# callbacks, load_session_from_file, save_session_to_file, validate_access_token
from kiteconnect import KiteConnect
import config
import pyotp
import json
from tqdm import tqdm
from data.utils import update_env_variable


totpsecret = config.CONFIG_AUTH.KITE_TOTP_SECRET
kiteapikey = config.CONFIG_GLOBAL.KITE_API_KEY
kiteapisecret = config.CONFIG_GLOBAL.KITE_API_SECRET
redirecturi = config.CONFIG_AUTH.REDIRECT_URI
session_file_name = config.CONFIG_AUTH.SESSION_FILE_NAME
conn_string = config.CONFIG_GLOBAL_DB.CONN_STRING
req_conn_url =  config.CONFIG_GLOBAL_DB.REQ_CONN_URL
kiteusername = config.CONFIG_AUTH.KITEUSERNAME
kitepwd = config.CONFIG_AUTH.KITEPWD


app = FastAPI()

@app.get("/")
def login_redirect(request: Request):
    print('request received on the redirect')
    print(request)
    pass

def server_start():
    uvicorn.run(app, host="127.0.0.1", port=8000)

def get_and_save_access_token():

    kite = KiteConnect(api_key=kiteapikey)

    session = requests.Session()

    request_id = session.post("https://kite.zerodha.com/api/login", {"user_id": kiteusername, "password": kitepwd}).json()["data"]["request_id"]
    resp = session.post("https://kite.zerodha.com/api/twofa", {"user_id": kiteusername, "request_id": request_id, "twofa_value": pyotp.TOTP(totpsecret).now()})


    p = Process(target=server_start)
    
    p.start()   
    time.sleep(3)
    
    api_session = session.get(f"https://kite.trade/connect/login?api_key={kiteapikey}")
    
    parsed = urlparse(api_session.url)
    request_token = parse_qs(parsed.query)["request_token"][0]
    kitesession_data = kite.generate_session(request_token, api_secret=kiteapisecret)

    # storing as pickle file - stores as bytes
    with open(os.path.join(project_root, 'data', 'daily_auth', session_file_name), 'wb') as f:
        pickle.dump(kitesession_data, f)

    access_token = kitesession_data['access_token']


    print(f"ACCESS_TOKEN: {access_token}")

    update_env_variable("KITE_API_ACCESS_TOKEN", access_token, daily_auth_dotenv_path)

    kite.set_access_token(access_token)

    profile = kite.profile()
    print(profile)


    time.sleep(4)
    p.terminate()
    p.join()

    print('\nSuccessfully acquired auth token!!')
    

if __name__ == '__main__':

    try:

        get_and_save_access_token()
    
    except Exception as e:
        
        print(f"access token fetching flow couldn't complete. Error: {e}")
        print("start the manual login flow")

    