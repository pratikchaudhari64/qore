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
import config
import json
from tqdm import tqdm


totpsecret = config.CONFIG_AUTH.KITE_TOTP_SECRET
kiteapikey = config.CONFIG_GLOBAL.KITE_API_KEY
kiteapisecret = config.CONFIG_GLOBAL.KITE_API_SECRET
redirecturi = config.CONFIG_AUTH.REDIRECT_URI
session_file_name = config.CONFIG_AUTH.SESSION_FILE_NAME
conn_string = config.CONFIG_GLOBAL_DB.CONN_STRING
req_conn_url =  config.CONFIG_GLOBAL_DB.REQ_CONN_URL
kiteusername = config.CONFIG_AUTH.KITEUSERNAME
kitepwd = config.CONFIG_AUTH.KITEPWD
dhandataapi_access_token = config.CONFIG_AUTH.DHAN_DATA_API_ACCESS_TOKEN
dhan_clientid = config.CONFIG_GLOBAL.DHAN_CLIENTID

def _get_historical_data(dhan_client, 
                        security_id, exchange_segment, instrument_type,
                        to_date, from_date = "1980-01-02"):
    
    df = dhan_client.historical_daily_data(security_id=security_id, 
                                   exchange_segment=exchange_segment, 
                                   instrument_type=instrument_type, 
                                   to_date=to_date, from_date=from_date)
    
    data = pd.DataFrame(df['data'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='s')
    data.loc[:, 'security_id'] = security_id

    return data

def all_eq_hist_data():

    dhan = dhanhq(dhan_clientid, dhandataapi_access_token) 
    to_date = datetime.now().strftime('%Y-%m-%d')

    kite = KiteConnect(api_key=kiteapikey)
    
    with open(os.path.join(project_root, 'data', 'daily_auth', session_file_name), 'rb') as f:
        session_data_cache = pickle.load(f)
    kite.set_access_token(session_data_cache['access_token'])

    kiteall_instr = pd.DataFrame(kite.instruments())
    kiteall_instr['exchange_token'] = kiteall_instr['exchange_token'].astype(int)

    dhansecurity_list = dhan.fetch_security_list(mode='detailed')
    instr_eq_dhan_list = dhansecurity_list[dhansecurity_list['INSTRUMENT'].isin(['EQUITY'])]
    logging.info(f"Total securities in Dhan: {dhansecurity_list.shape[0]}")
    logging.info(f"Total securities in Kite: {kiteall_instr.shape[0]}")

    securities_to_pull = instr_eq_dhan_list[instr_eq_dhan_list['SECURITY_ID'].isin(kiteall_instr['exchange_token'].tolist())]

    securities_to_pull.loc[:, 'exchange_segment'] = securities_to_pull['EXCH_ID'] + '_EQ'

    allhist_data = []
    for idx, security in tqdm(securities_to_pull.head(10).iterrows(), total=10):

        try:
            data = _get_historical_data(dhan, security['SECURITY_ID'], 
                                       security['exchange_segment'], security['INSTRUMENT'], 
                                       to_date=to_date)
            data.loc[:, 'symbol'] = security['UNDERLYING_SYMBOL']
            allhist_data.append(data)
        
        except Exception as e:
            print(f"not fetched for {security['DISPLAY_NAME']}:{security['SECURITY_ID']} ")
        
        time.sleep(0.2)
    
    allhist_data_df = pd.concat(allhist_data)

    return allhist_data_df
    

if __name__ == '__main__':
    #Dhan API: robust for all historical OHLC data; Currently handles Equity, need to figure out Indexes. 
    # Does not have industry. Rely on nsepy for industry code
    all_eq_hist_df = all_eq_hist_data()
    print(all_eq_hist_df)
