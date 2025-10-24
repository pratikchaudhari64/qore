#TODO:
# 1. 

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
import holidays
from data.daily_data_fetches.securities import Stocks

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
kiteapi_access_token = config.CONFIG_AUTH.KITE_API_ACCESS_TOKEN
dhan_clientid = config.CONFIG_GLOBAL.DHAN_CLIENTID

class MarketDataFetcher:
    def __init__(self, save_file='market_data.pkl'):
        self.dhan_client = dhanhq(dhan_clientid, dhandataapi_access_token) 
        self.kite_client = KiteConnect(api_key=kiteapikey)
        self.kite_client.set_access_token(kiteapi_access_token)
        self.stocks = Stocks(exchanges=['NSE', 'BSE'], instrument_types=['EQ'])
        self.data_dir = os.path.join(project_root, 'data')
        self.available_hist_file = 'available_hist_instruments.pkl'
        self.holidays_file = 'market_holidays.pkl'
        self.save_file = save_file
        if os.path.exists(os.path.join(self.data_dir,self.holidays_file)):
            print("\nFound existing market data...")
            self.holidays = pd.read_pickle(os.path.join(self.data_dir,self.holidays_file))
        else: 
            print("\nNo holidays data found...")
            # print("\nHolidays data does not exists, scraping...")
            self.holidays = self.__get_holidays__()
            # self.holidays = []

        if os.path.exists(os.path.join(self.data_dir,self.available_hist_file)):
            print("\nFound existing market data...")
            self.available_hist = pd.read_pickle(os.path.join(self.data_dir,self.available_hist_file))
        else: 
            print("\nNo market data found...")
            # print("\nInstruments data does not exists, downloading...")
            # self.available_hist = pd.DataFrame()
            # self.available_hist = self.__generate_instruments__()
            # self.available_hist.to_pickle(os.path.join(self.data_dir,self.available_hist_file))
            self.available_hist = [] 
    
    def __get_holidays__(self):
        return []

    def _get_historical_data_(self, security_id, exchange_segment, instrument_type,
                            from_date = "1980-01-02", to_date=datetime.now().strftime('%Y-%m-%d')):
        try:
            df = self.dhan_client.historical_daily_data(security_id=security_id, 
                                        exchange_segment=exchange_segment, 
                                        instrument_type=instrument_type, 
                                        from_date=from_date, to_date=to_date)
            # print(df.keys)
            # print(df)
            data = pd.DataFrame(df['data'])
            data['timestamp'] = pd.to_datetime(data['timestamp'], unit='s')
            data.loc[:, 'security_id'] = security_id
            return data
        except Exception as e:
            logger.error(f"Error fetching historical data for {security_id}: {e}")
            return pd.DataFrame()
    
    def _get_daily_data_(self, security_id, exchange_segment, instrument_type):

        dt_from = (datetime.now() - pd.Timedelta(days=1))
        dt_to = (datetime.now())

        if dt_from in self.holidays or dt_from.weekday() > 4:
            print(f"{dt_from} was a holiday or weekend, skipping daily fetch.")
            return pd.DataFrame()
        try:
            df = self.dhan_client.historical_daily_data(security_id=security_id, 
                                        exchange_segment=exchange_segment, 
                                        instrument_type=instrument_type, 
                                        from_date=dt_from.strftime('%Y-%m-%d'),
                                        to_date=dt_to.strftime('%Y-%m-%d'))
            
            # print(df)
            data = pd.DataFrame(df['data'])
            data['timestamp'] = pd.to_datetime(data['timestamp'], unit='s')
            data.loc[:, 'security_id'] = security_id
            return data
        except Exception as e:
            logger.error(f"Error fetching daily data for {security_id}: {e}")
            return pd.DataFrame()
    
    def fetch_all_eq_hist_data(self, timeout = 0.07):
        to_date = datetime.now().strftime('%Y-%m-%d')

        kiteall_instr = self.stocks.instruments
        kiteall_instr['exchange_token'] = kiteall_instr['exchange_token'].astype(int)

        dhansecurity_list = self.dhan_client.fetch_security_list(mode='detailed')
        instr_eq_dhan_list = dhansecurity_list[dhansecurity_list['INSTRUMENT'].isin(['EQUITY'])]
        logging.info(f"Total securities in Dhan: {dhansecurity_list.shape[0]}")
        logging.info(f"Total securities in Kite: {kiteall_instr.shape[0]}")

        securities_to_pull = instr_eq_dhan_list[
            (instr_eq_dhan_list['SECURITY_ID'].isin(kiteall_instr['exchange_token'].tolist())) &
            (~instr_eq_dhan_list['SECURITY_ID'].isin(self.available_hist))
        ]
        securities_to_pull.loc[:, 'exchange_segment'] = securities_to_pull['EXCH_ID'] + '_EQ'

        # exch_tokens = self.stocks.instruments['exchange_token'].astype(int)
        # dhansecurity_list = self.dhan_client.fetch_security_list(mode='detailed')
        # instr_eq_dhan_list = dhansecurity_list[dhansecurity_list['INSTRUMENT'].isin(['EQUITY'])]['SECURITY_ID'].sample(n=10).astype(int)
        # print(exch_tokens)
        # print(instr_eq_dhan_list)
        # # return 0
        # merged_df = pd.merge(instr_eq_dhan_list, exch_tokens, left_on='SECURITY_ID', right_on='exchange_token', how='inner')
        # logger.info(f"Securities to pull: {merged_df.shape[0]}")
        # return 0
        all_data = []
        for _, row in tqdm(securities_to_pull[:100].iterrows()):
            try:
                data = self._get_historical_data_(security_id=row['SECURITY_ID'], 
                                                exchange_segment=row['exchange_segment'], 
                                                instrument_type=row['INSTRUMENT'],
                                                to_date=to_date)
                all_data.append(data)
                tqdm.write(f"Fetched data for {row['SECURITY_ID']}")
                time.sleep(timeout)
            except Exception as e:
                tqdm.write(f"Error fetching data for {row['SECURITY_ID']}: {e}")
                time.sleep(timeout)
        print("Loop completed")
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            if os.path.exists(os.path.join(self.data_dir, self.save_file)):
                # If it exists, append the data and do not write the header
                final_df.to_csv(os.path.join(self.data_dir, self.save_file), mode='a', index=False, header=False)
                print(f"Appended DataFrame to '{self.save_file}'.")
            else:
                # If it does not exist, create a new file with the header
                final_df.to_csv(os.path.join(self.data_dir, self.save_file), mode='w', index=False, header=True)
                print(f"Created and wrote new file to '{self.save_file}'.")
            if len(self.available_hist):
                self.available_hist.extend(final_df['security_id'].unique().tolist())
            else:
                self.available_hist = final_df['security_id'].unique().tolist()
            with open(os.path.join(self.data_dir,self.available_hist_file), 'wb') as f:
                pickle.dump(self.available_hist , f)
            return final_df
        else:
            logger.warning("No data fetched.")
            return pd.DataFrame()
    
    def fetch_all_eq_daily_data(self, timeout = 0.07):
        to_date = datetime.now().strftime('%Y-%m-%d')

        kiteall_instr = self.stocks.instruments
        kiteall_instr['exchange_token'] = kiteall_instr['exchange_token'].astype(int)

        dhansecurity_list = self.dhan_client.fetch_security_list(mode='detailed')
        instr_eq_dhan_list = dhansecurity_list[dhansecurity_list['INSTRUMENT'].isin(['EQUITY'])]
        logging.info(f"Total securities in Dhan: {dhansecurity_list.shape[0]}")
        logging.info(f"Total securities in Kite: {kiteall_instr.shape[0]}")

        securities_to_pull = instr_eq_dhan_list[
            (instr_eq_dhan_list['SECURITY_ID'].isin(kiteall_instr['exchange_token'].tolist())) &
            (~instr_eq_dhan_list['SECURITY_ID'].isin(self.available_hist))
        ]
        securities_to_pull.loc[:, 'exchange_segment'] = securities_to_pull['EXCH_ID'] + '_EQ'

        # exch_tokens = self.stocks.instruments['exchange_token'].astype(int)
        # dhansecurity_list = self.dhan_client.fetch_security_list(mode='detailed')
        # instr_eq_dhan_list = dhansecurity_list[dhansecurity_list['INSTRUMENT'].isin(['EQUITY'])]['SECURITY_ID'].sample(n=10).astype(int)
        # print(exch_tokens)
        # print(instr_eq_dhan_list)
        # # return 0
        # merged_df = pd.merge(instr_eq_dhan_list, exch_tokens, left_on='SECURITY_ID', right_on='exchange_token', how='inner')
        # logger.info(f"Securities to pull: {merged_df.shape[0]}")
        # return 0
        all_data = []
        for _, row in tqdm(securities_to_pull[:100].iterrows()):
            try:
                data = self._get_daily_data_(security_id=row['SECURITY_ID'], 
                                                exchange_segment=row['exchange_segment'], 
                                                instrument_type=row['INSTRUMENT'])
                all_data.append(data)
                tqdm.write(f"Fetched data for {row['SECURITY_ID']}")
                time.sleep(timeout)
            except Exception as e:
                tqdm.write(f"Error fetching data for {row['SECURITY_ID']}: {e}")
                time.sleep(timeout)
        print("Loop completed")
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            if os.path.exists(os.path.join(self.data_dir, self.save_file)):
                # If it exists, append the data and do not write the header
                final_df.to_csv(os.path.join(self.data_dir, self.save_file), mode='a', index=False, header=False)
                print(f"Appended DataFrame to '{self.save_file}'.")
            else:
                # If it does not exist, create a new file with the header
                final_df.to_csv(os.path.join(self.data_dir, self.save_file), mode='w', index=False, header=True)
                print(f"Created and wrote new file to '{self.save_file}'.")
            return final_df
        else:
            logger.warning("No data fetched.")
            return pd.DataFrame()

if __name__ == '__main__':
    #Dhan API: robust for all historical OHLC data; Currently handles Equity, need to figure out Indexes. 
    # Does not have industry. Rely on nsepy for industry code
    fetcher = MarketDataFetcher()
    print(fetcher.available_hist)
    # print(fetcher.stocks.instruments[fetcher.stocks.instruments['tradingsymbol'] == 'RELIANCE']) # 2885
    # dat = fetcher._get_historical_data_(security_id=500013, exchange_segment='BSE_EQ', instrument_type='EQUITY')
    dat = fetcher.fetch_all_eq_hist_data()
    # dat.head(10)
    print(fetcher.available_hist)
    # df = pd.read_pickle(os.path.join(project_root, 'data', 'market_data.pkl'))
    # print(df.head(10))
    # all_eq_hist_df = all_eq_hist_data()
    # print(all_eq_hist_df)
