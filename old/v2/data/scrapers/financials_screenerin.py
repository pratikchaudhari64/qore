import json
from symtable import Symbol
from urlread import *
import logging
import csv
import requests
import os
import re
from time import sleep
import uuid
from io import BytesIO
import pandas as pd
import xlwings as xl
from tqdm import tqdm


# logging.basicConfig(filename='log.txt', filemode='a',format='%(asctime)s - %(message)s', level=logging.DEBUG)
# console = logging.StreamHandler()
# logging.getLogger().addHandler(console)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-language": "en-US,en;q=0.9,hi;q=0.8",
    "cache-control": "max-age=0",
    "content-type": "application/x-www-form-urlencoded",
    "sec-ch-ua": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"98\", \"Google Chrome\";v=\"98\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    # "cookie": "csrftoken=I7FasdasdsamHZfqY4duaGsB0jgi1BQFlNmifDmbd sessionid=sdsdadsdsds; _gcl_au=1.1.602809564.1645862651; _ga=GA1.2.",
    "cookie": "csrftoken=Dvb6rxEdFd25n2dRVVxjTgyaWIOYSXxL; sessionid=0xgyrkrkc3jpsjqsg0pe4ysud0xj05hu",
    "Referer": "https://www.screener.in/company/HDFCBANK/consolidated/",
    "Referrer-Policy": "no-referrer-when-downgrade"
  }

# postdata = "csrfmiddlewaretoken=FWEEawGRsB2XkdKTSMxkRao1OZzlv2xq&next=%2Fcompany%2FTATAMOTORS%2Fconsolidated%2F"
postdata = "csrfmiddlewaretoken=Lt9BUPN02dNhQ3oBqY4sdM9qpt6xSOkaeOaxbch3xgFc3VribJrBWSxqb1KlABHL&next=/company/HDFCBANK/consolidated/"


def getData(warehouseid,symbol,PATH):
    url = 'https://www.screener.in/user/company/export/{}/'.format(warehouseid)
    r = requests.post(url, data= postdata, headers=headers)
    
    with open(f"{symbol}.xlsx", 'wb') as f:
        for chunks in r:
            f.write(chunks)

    try:
        # Use xlwings to process the file and save changes (if needed). 
        # Doing an "extra" save to make file readable for pd.read_excel
        app = xl.App(visible=False)
        book = app.books.open(f"{symbol}.xlsx")
        book.save()
        app.kill()
        
        # Read the Excel file into a dictionary of DataFrames
        read_df = pd.read_excel(f"{symbol}.xlsx", header=2, sheet_name=None)
        
        logging.info(f"Successfully processed and read data for {symbol}.")
        
    except Exception as e:
        logging.error(f"Error processing or reading Excel file for {symbol}: {e}")
        
    finally:
        # This block is guaranteed to run, ensuring the file is deleted
        if os.path.exists(f"{symbol}.xlsx"):
            os.remove(f"{symbol}.xlsx")
            logging.info(f"Deleted temporary file: {f"{symbol}.xlsx"}")
            
    return read_df
    

def Scrape(symbols,PATH = None,delay=0.2):
    data = []
    exported_data = {}
    rexp = 'formaction=.\/user\/company\/export/([0-9]+)\/.'
    for symbol in tqdm(symbols):
        api = "https://www.screener.in/api/company/search/?q=" + symbol    
        logging.info("Getting: " + api)
        try:
            d = urlread(api)
            j = json.loads(d)[0]
            html = urlread('https://www.screener.in' + j['url'])        
            results = re.findall(rexp,html)
            print("Warehouse Id = " + results[0])      
            
            j['warehouse'] = results[0]
            data.append(j)        
            logging.info("Downloading: " + symbol)
            data_df = getData(results[0],symbol,PATH)
            exported_data[symbol] = data_df
        except:
            print("Error: " + api)
            logging.error(api)
        sleep(delay)
    
    return exported_data



if __name__ == "__main__":

    import os, sys
    import pandas as pd
    from io import BytesIO
    import xlwings as xl
    import time
    from datetime import datetime
    from tqdm import tqdm

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(current_dir, '..', '..')
    sys.path.insert(0, project_root)
    
    from kiteconnect import KiteConnect
    import config
    from data import fetcher
    from data import db


    kiteapikey = config.CONFIG_GLOBAL.KITE_API_KEY

    kc_instance = KiteConnect(api_key=kiteapikey)

    kitedata = fetcher.AuthData(kc_instance=kc_instance)
    all_instruments = pd.DataFrame(kitedata.test_instruments())
    
    symbols = all_instruments[all_instruments['instrument_type'] == 'EQ']['tradingsymbol'].head(300).tolist()
    scraped_data = Scrape(symbols)
    
    
    transf_scraped_data = []
    for stock_data in tqdm(scraped_data.keys()):

        pnl = scraped_data[stock_data]['Profit & Loss'].set_index('Narration')
        pnl = pnl[~pnl.index.duplicated(keep=False)]
        pnl_json = pnl.to_json()

        bl = scraped_data[stock_data]['Balance Sheet'].set_index('Narration')
        bl = bl[~bl.index.duplicated(keep=False)]
        bl_json = bl.to_json()

        cf = scraped_data[stock_data]['Cash Flow'].set_index('Narration')
        cf = cf[~cf.index.duplicated(keep=False)]
        cf_json = cf.to_json()

        all_keys = set(json.loads(bl_json).keys()).union(json.loads(pnl_json).keys(), json.loads(cf_json).keys())
        common_ts_keys = [key for key in all_keys if isinstance(key, str) and key.isdigit() and datetime.fromtimestamp(int(key) / 1000)]
        

        for key in common_ts_keys:
            ts = int(key)
            data_row = {
                'time_period_ts': datetime.fromtimestamp(ts / 1000),
                'stock_ticker': stock_data,
                'pnl': json.dumps(json.loads(pnl_json).get(key, None)),
                'balance_sheet': json.dumps(json.loads(bl_json).get(key, None)),
                'cash_flows': json.dumps(json.loads(cf_json).get(key, None))
            }

            transf_scraped_data.append(data_row)
    
    transf_scraped_data_df = pd.DataFrame(transf_scraped_data)
    print(transf_scraped_data_df.shape)

    req_conn_url = config.CONFIG_GLOBAL_DB.REQ_CONN_URL

    resp, err = db.insert_dataframe_to_questdb(df=transf_scraped_data_df,
                                            table_name='financial_statements',
                                            timestamp_col='time_period_ts',
                                            req_conn_url=req_conn_url)
    
    print(resp, err)