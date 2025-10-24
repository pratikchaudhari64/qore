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

def _get_industry_type():
    kite = KiteConnect(api_key=kiteapikey)
    
    with open(os.path.join(project_root, 'data', 'daily_auth', session_file_name), 'rb') as f:
        session_data_cache = pickle.load(f)
    kite.set_access_token(session_data_cache['access_token'])

    kiteall_instr = pd.DataFrame(kite.instruments())
    kite_eq_instr = kiteall_instr[kiteall_instr['instrument_type'] == 'EQ']

    symbols = kite_eq_instr['tradingsymbol'].tolist()
    # for symbol in symbols:
    #     nsedata = nse_quote(symbol)
    # nsepy_data = fetcher.AuthData(kc_instance=kite)
    # nsepy_data, error_symbols = nsepy_data.test_nsepy_quotes(symbols_list=symbols[200:250])

    # return pd.DataFrame(nsepy_data)
    return symbols

if __name__ == "__main__":

    df = _get_industry_type()
    nsedata = {}
    for symbol in tqdm(df[200:210]):
        try:
            nsedata[symbol] = nse_quote(symbol)
            print(json.dumps(nsedata[symbol], indent=4))
        except Exception as e:
            print(f"error for {symbol}. Error: {e}")
    
    for keysymbol in nsedata.keys():
        if 'error' in nsedata[keysymbol].keys():
            print(f"symbol: {keysymbol}; error: {nsedata[keysymbol]['error']}; message: {nsedata[keysymbol]['message']}")
