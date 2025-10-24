#TODO:
# 1. Add functionality to retry failed connections : Done - test

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
from tenacity import retry, stop_after_attempt, wait_exponential, RetryCallState, retry_if_exception_type

# Simplified callbacks (no error details)
def retry_before_sleep(retry_state: RetryCallState):
    code = retry_state.args[2]  # Adjust index if NSE signature differs (e.g., args[1] for no 'bse')
    attempt = retry_state.attempt_number  # Just-completed failed attempt
    logger.log(f"Retrying '{code}' (attempt {attempt + 1})...")

def retry_after(retry_state: RetryCallState):
    code = retry_state.args[2]
    attempt = retry_state.attempt_number
    if not retry_state.outcome.failed:
        logger.log(f"Success for '{code}' at attempt {attempt}")

def retry_error_callback(retry_state: RetryCallState):
    code = retry_state.args[2]
    attempts = retry_state.attempt_number
    logger.log(f"Failed for '{code}' after {attempts} tries, skipping...")


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

class Stocks:
    def __init__(self, exchanges=['NSE', 'BSE'], instrument_types=['EQ'], instruments_file='instruments.pkl',
                nse_metadata_file='nse_metadata.pkl', bse_metadata_file='bse_metadata.pkl'):
        # instrument_type: ['FUT' 'CE' 'PE' 'EQ']
        # exchange: ['BFO' 'BSE' 'CDS' 'NSE' 'MCX' 'NSEIX' 'GLOBAL' 'NCO' 'NFO']
        self.exchanges = exchanges
        self.instrument_types = instrument_types

        self.instruments_file = instruments_file
        self.nse_metadata_file = nse_metadata_file
        self.bse_metadata_file = bse_metadata_file
        self.data_dir = os.path.join(project_root, 'data')

        if os.path.exists(os.path.join(self.data_dir,self.instruments_file)):
            print("\nInstruments data exists, importing...")
            self.instruments = pd.read_pickle(os.path.join(self.data_dir,self.instruments_file))
        else: 
            print("\nInstruments data does not exists, downloading...")
            self.instruments = pd.DataFrame()
            self.instruments = self.__generate_instruments__()
            self.instruments.to_pickle(os.path.join(self.data_dir,self.instruments_file))
        
        if os.path.exists(os.path.join(self.data_dir,self.nse_metadata_file)):
            print("\nNSE metadata exists, importing...")
            self.nse_metadata = pd.read_pickle(os.path.join(self.data_dir,self.nse_metadata_file))
        else: 
            print("\nNSE metadata does not exists, downloading...")
            self.nse_metadata = pd.DataFrame()
            self.nse_metadata = self.__generate_nse_metadata__()
            if not self.nse_metadata.empty:
                self.nse_metadata.to_pickle(os.path.join(self.data_dir,self.nse_metadata_file))

        # self.mapper = dict(zip(self.instruments["tradingsymbol"], self.instruments["exchange_token"]))
        if os.path.exists(os.path.join(self.data_dir,self.bse_metadata_file)):
            print("\nBSE metadata exists, importing...")
            self.bse_metadata = pd.read_pickle(os.path.join(self.data_dir,self.bse_metadata_file))
        else: 
            print("\nBSE metadata does not exists, downloading...")
            self.bse_metadata = pd.DataFrame()
            self.bse_metadata = self.__generate_bse_metadata__()
            if not self.bse_metadata.empty:
                self.bse_metadata.to_pickle(os.path.join(self.data_dir,self.bse_metadata_file))

    def __generate_instruments__(self):
        kite = KiteConnect(api_key=kiteapikey)
        with open(os.path.join(project_root, 'data', 'daily_auth', session_file_name), 'rb') as f:
            session_data_cache = pickle.load(f)
        kite.set_access_token(session_data_cache['access_token'])
        kiteall_instr = pd.DataFrame(kite.instruments())
        # print(kiteall_instr['instrument_type'].unique())
        # print(kiteall_instr['exchange'].unique())
        kite_ex_instr = kiteall_instr[kiteall_instr['exchange'].isin(self.exchanges)]
        kite_exty_instr = kite_ex_instr[kite_ex_instr['instrument_type'].isin(self.instrument_types)]
        # print(kite_exty_instr['instrument_type'].unique())
        # print(kite_exty_instr['exchange'].unique())
        # print(kite_exty_instr.head(10))
        return kite_exty_instr
    
    def update_instruments(self):
        print("\nInstruments update requested...")
        self.instruments = self.__generate_instruments__()
        self.instruments.to_pickle(self.instruments_file)
        print("\nInstruments updated sucessfully!")
        pass 
    
    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=0.5, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, ValueError)),
        before_sleep=retry_before_sleep,
        after=retry_after,
        retry_error_callback=retry_error_callback
    )
    def __nse_quote__(self, symbol):
        return nse_quote(symbol)
    
    def __generate_nse_metadata__(self, syms=None):
        tmp_nse_metadata = {}
        symbols = syms if syms else self.instruments.loc[self.instruments['exchange'] == 'NSE']['tradingsymbol'].tolist()
        limit = min(len(symbols), 100)
        for symbol in tqdm(symbols[700:700+limit]):
            # tqdm.write(f"Symbol: {symbol}")
            try:
                tmp_nse_metadata[symbol] = self.__nse_quote__(symbol)
                # tqdm.write(f"NSE Returned: {tmp_nse_metadata[symbol]}")
                keys_to_keep = ["info", "metadata", "securityInfo", "industryInfo", "sddDetails", "currentMarketType"]
                tmp_nse_metadata[symbol] = {k: tmp_nse_metadata[symbol][k] for k in keys_to_keep if k in tmp_nse_metadata[symbol]}
                # print(json.dumps(nsedata[symbol], indent=4))
                # tqdm.write(f"Keys: {tmp_nse_metadata[symbol].keys()}")
                # tqdm.write(f"{tmp_nse_metadata[symbol]["info"]}")
            except Exception as e:
                tqdm.write(f"error for {symbol}. Error: {e}")
        return self.__process_nse_metadata__(tmp_nse_metadata)
    
    def __flatten_json__(self, data, parent_key='', sep='_'):
            items = []
            for key, value in data.items():
                new_key = f"{parent_key}{sep}{key}" if parent_key else key
                if isinstance(value, dict):
                    items.extend(self.__flatten_json__(value, new_key, sep).items())
                elif isinstance(value, list):
                    if key == "preopen":
                        # Convert preopen list to a string or handle separately
                        items.append((new_key, json.dumps(value)))
                    elif key == "pdSectorIndAll":
                        items.append((new_key, ', '.join(value)))
                    elif key == "activeSeries":
                        items.append((new_key, ', '.join(value)))
                    else:
                        items.append((new_key, value))
                else:
                    items.append((new_key, value))
            return dict(items)
    
    def __process_nse_metadata__(self, tmp_nse_metadata):
        nse_flattened = pd.DataFrame()
        # Extract the 'SYMBOL' level and flatten
        for sym in tmp_nse_metadata.keys():
            flattened_data = self.__flatten_json__(tmp_nse_metadata[sym])
            df = pd.DataFrame([flattened_data])
            nse_flattened = pd.concat([nse_flattened, df], ignore_index=True)
        # print("Columns in nse_flattened:", nse_flattened.columns.tolist())
        # print(nse_flattened.head(5))
        # print(nse_flattened.shape)
        if nse_flattened.shape[1] > 0:
            nse_flattened = nse_flattened.dropna(subset=['info_symbol', 'metadata_symbol'], how='all')
        # print(nse_flattened.head(5))
        # print(nse_flattened.shape)
        return nse_flattened
    
    def update_nse_metadata(self):
        print("\nNSE metadata update requested...")
        unique_instr = self.instruments['tradingsymbol'].unique()
        unique_nse = self.nse_metadata['info_symbol'].unique()
        sym_delta = set(unique_instr) ^ set(unique_nse)
        incr_metadata = self.__generate_nse_metadata__(list(sym_delta))
        self.nse_metadata = pd.concat([self.nse_metadata, incr_metadata], ignore_index=True)
        self.nse_metadata = self.nse_metadata.drop_duplicates(subset=['info_symbol', 'metadata_symbol'], keep='last').reset_index(drop=True)
        self.nse_metadata.to_pickle(os.path.join(self.data_dir,self.nse_metadata_file))
        print("\nNSE metadata updated sucessfully!")
        pass
    
    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, ValueError)),
        before_sleep=retry_before_sleep,
        after=retry_after,
        retry_error_callback=retry_error_callback
    )
    def __bse_quote__(self, bse, code):
        return bse.getQuote(code)
    
    def __generate_bse_metadata__(self, scripcodes=None):
        tmp_bse_metadata = {}
        BSE_instrument_scripcodes = scripcodes if scripcodes else self.instruments.loc[self.instruments['exchange'] == 'BSE']['exchange_token'].tolist()
        b = BSE(update_codes = True)
        limit = min(len(BSE_instrument_scripcodes), 20)
        for code in tqdm(BSE_instrument_scripcodes[700:700+limit]):
            try:
                # q = b.getQuote(code)
                q = self.__bse_quote__(b, code)
                tmp_bse_metadata[code] = q
                keys_to_keep = ["companyName", "securityID", "scripCode", "group", "industry"]
                tmp_bse_metadata[code] = {k: tmp_bse_metadata[code][k] for k in keys_to_keep if k in tmp_bse_metadata[code]}
            except Exception as e:
                tqdm.write(f"Error for {code}. Error: {e}")
        return self.__process_bse_metadata__(tmp_bse_metadata)
    
    def __process_bse_metadata__(self, tmp_bse_metadata):
        bse_flattened = pd.DataFrame()
        # Extract the 'SYMBOL' level and flatten
        for code in tmp_bse_metadata.keys():
            flattened_data = self.__flatten_json__(tmp_bse_metadata[code])
            df = pd.DataFrame([flattened_data])
            bse_flattened = pd.concat([bse_flattened, df], ignore_index=True)
        # print("Columns in nse_flattened:", nse_flattened.columns.tolist())
        # print(nse_flattened.head(5))
        # print(nse_flattened.shape)
        if bse_flattened.shape[1] > 0:
            bse_flattened = bse_flattened.dropna(subset=['scripCode'])
        # print(nse_flattened.head(5))
        # print(nse_flattened.shape)
        return bse_flattened
    
    def update_bse_metadata(self):
        print("\nBSE metadata update requested...")
        unique_instr = self.instruments['exchange_token'].unique()
        unique_bse = self.bse_metadata['scripCode'].unique()
        code_delta = set(unique_instr) ^ set(unique_bse)
        incr_metadata = self.__generate_bse_metadata__(list(code_delta))
        self.bse_metadata = pd.concat([self.bse_metadata, incr_metadata], ignore_index=True)
        self.bse_metadata = self.bse_metadata.drop_duplicates(subset=['scripCode']).reset_index(drop=True)
        self.bse_metadata.to_pickle(os.path.join(self.data_dir,self.bse_metadata_file))
        print("\nBSE metadata updated sucessfully!")
        pass



if __name__ == '__main__':
    stocks = Stocks(exchanges=['NSE', 'BSE'], instrument_types=['EQ'])

    # stocks.update_instruments()
    stocks.update_nse_metadata()
    stocks.update_bse_metadata()

    # df = stocks.instruments
    # symbols = df['tradingsymbol'].tolist()
    # print(symbols[500:600])
    # print(df.head(5))
    # df2 = stocks.nse_metadata
    # print(df2.shape)
    # print(df2.head(10))
    # df3 = stocks.bse_metadata
    # print(df3.shape)
    # print(df3.head(10))
    # stocks.update_bse_metadata()
    # df3 = stocks.bse_metadata
    # print(df3.head(10))
    # print(df3.shape)
    # print(json.dumps(nse_quote('VMART'), indent=4))
    # nsedata = {}
    # for symbol in tqdm(df[300:310]):
    #     try:
    #         nsedata[symbol] = nse_quote(symbol)
    #         # print(json.dumps(nsedata[symbol], indent=4))
    #     except Exception as e:
    #         print(f"error for {symbol}. Error: {e}")