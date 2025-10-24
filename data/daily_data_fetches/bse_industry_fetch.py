import time
import logging
import sys
import os
from datetime import datetime
import pandas as pd
from urllib.parse import urlparse, parse_qs
from fastapi import FastAPI, Request
from multiprocessing import Process
import pickle
from tqdm import tqdm

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


session_data_cache= {}

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

# callbacks, load_session_from_file, save_session_to_file, validate_access_token
from kiteconnect import KiteConnect
from dhanhq import dhanhq
from data import fetcher
import config
import json
from tqdm import tqdm
from nsepython import *
from bsedata.bse import BSE


totpsecret = config.CONFIG_AUTH.KITE_TOTP_SECRET
kiteapikey = config.CONFIG_GLOBAL.KITE_API_KEY
kiteapisecret = config.CONFIG_GLOBAL.KITE_API_SECRET
redirecturi = config.CONFIG_AUTH.REDIRECT_URI
session_file_name = config.CONFIG_AUTH.SESSION_FILE_NAME
conn_string = config.CONFIG_GLOBAL_DB.CONN_STRING
req_conn_url =  config.CONFIG_GLOBAL_DB.REQ_CONN_URL
kiteusername = config.CONFIG_AUTH.KITEUSERNAME
kitepwd = config.CONFIG_AUTH.KITEPWD
dhandataapi_access_token = config.CONFIG_GLOBAL.DHAN_DATA_API_ACCESS_TOKEN
dhan_clientid = config.CONFIG_GLOBAL.DHAN_CLIENTID


def get_all_instruments():
    kite = KiteConnect(api_key=kiteapikey)
    
    with open(os.path.join(project_root, 'data', 'daily_auth', session_file_name), 'rb') as f:
        session_data_cache = pickle.load(f)
    kite.set_access_token(session_data_cache['access_token'])

    kiteall_instr = pd.DataFrame(kite.instruments())
    kite_eq_instr = kiteall_instr[kiteall_instr['instrument_type'] == 'EQ']

    print("Kite Instruments Fetched Successfully!")
    print(f"Sample:\t {kite_eq_instr[:5]}\nTotal Count:\t {len(kite_eq_instr)}\n")

    return kite_eq_instr

if __name__ == '__main__':
    
    all_EQ_kite_instr = get_all_instruments()
    BSE_instruments = all_EQ_kite_instr[all_EQ_kite_instr['exchange'] == 'BSE']
    BSE_instrument_scripcodes = BSE_instruments['exchange_token'].tolist()
    
    b = BSE()
    
    b = BSE(update_codes = True)

    for code in tqdm(BSE_instrument_scripcodes[200:300]):
        try:
            q = b.getQuote(code)
            print(q['industry'])
        except Exception as e:
            print(f"Error {e} for {code}")
