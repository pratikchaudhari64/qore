#TODO
# 1. Handle cases where there is a new financial year statement added
# 2. Separate out quarterly and annual statements and flatten

import json
# from symtable import Symbol
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
import sys
from datetime import datetime
import numpy as np
from openpyxl import load_workbook



logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# current_dir = os.path.dirname(os.path.abspath(__file__))
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-language": "en-US,en;q=0.9,hi;q=0.8",
    "cache-control": "no-cache",
    "content-type": "application/x-www-form-urlencoded",
    "sec-ch-ua": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"98\", \"Google Chrome\";v=\"98\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "cookie": "csrftoken=XdmIXXDldBvmI7OBaGUZ2EqUbrnzPwVP; sessionid=fj547dxooj4x79fe0gomfl6r8b32a2u9",
    "Referer": "https://www.screener.in/company/HDFCBANK/consolidated/",
    "Referrer-Policy": "no-referrer-when-downgrade"
  }

postdata = "csrfmiddlewaretoken=SbB6gGmGhK5c7o8DingGhuuDzMAzZXPpFeNE3tPRkbqoFlM4iT0v9YKnA3NYEjA4&next=/company/HDFCBANK/consolidated/"

def default_converter(o):
    if isinstance(o, datetime):
        return o.isoformat()  # YYYY-MM-DDTHH:MM:SS
    if isinstance(o, np.ndarray):
        def format_elem(x):
            if isinstance(x, (int, float, np.number)):
                if np.isnan(x):
                    return 0.0
                return round(float(x), 2)
            else:
                return x  # Preserve strings, None, or other non-numeric types

        def recurse_format(item):
            if isinstance(item, list):
                return [recurse_format(subitem) for subitem in item]
            else:
                return format_elem(item)

        if np.issubdtype(o.dtype, np.number):
            # For purely numeric arrays
            o = np.nan_to_num(o, nan=0.0)
            o = np.round(o, 2)
            return o.tolist()
        else:
            # For mixed/object dtype arrays
            lst = o.tolist()
            return recurse_format(lst)
    elif isinstance(o, np.generic):  # Handle NumPy scalars
        if np.isnan(o):
            return 0.0
        return round(float(o), 2)
    raise TypeError(f"Type {type(o)} not serializable")

class FinancialsExtractor:
    def __init__(self):
        self.data_dir = os.path.join(project_root, 'data', 'scrapers')
        self.financials_file = 'financials.json'
        self.existing_syms = [] if not os.path.exists(os.path.join(self.data_dir, self.financials_file)) else self._load_existing_data_()
        pass

    def _load_existing_data_(self):
        with open(os.path.join(self.data_dir, self.financials_file), "r") as f:
            return json.load(f).keys()
    
    def getData(self, warehouseid, symbol, PATH):
        if not os.path.exists(os.path.join(PATH, f"{symbol}.xlsx")):
            tqdm.write(f"Downloading financials for {symbol}...")
            # Construct the URL
            url = 'https://www.screener.in/user/company/export/{}/'.format(warehouseid)
            r = requests.post(url, data= postdata, headers=headers)

            r.raise_for_status() # Raise an error for bad responses

            filepath = os.path.join(PATH, f"{symbol}.xlsx")
            # Save the file locally
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive chunks
                        f.write(chunk)
            tqdm.write("Download complete!")
        else:
            print(f"File for {symbol} already exists. Skipping download.")
        try:
            # Read the Excel file into a dictionary of DataFrames
            # read_df = pd.read_excel(os.path.join(PATH, f"{symbol}.xlsx"), engine='openpyxl', sheet_name='Data Sheet')
            # result = self.cleanup_df(read_df)
            workbook = load_workbook(os.path.join(PATH, f"{symbol}.xlsx"), data_only=True)
            result = self.cleanup_json(workbook)
            # print(read_df.head(30))
            os.remove(os.path.join(PATH, f"{symbol}.xlsx"))
            tqdm.write(f"Successfully processed and read data for {symbol}.")

        except Exception as e:
            tqdm.write(f"Error processing or reading Excel file for {symbol}: {e}")
            result = None
        # return read_df
        return result

    def scrape(self, symbols,PATH = None,delay=0.2):
        data = []
        scraped_data = {}
        rexp = 'formaction=.\/user\/company\/export/([0-9]+)\/.'
        new_syms = []
        for symbol in tqdm(symbols):
            if symbol in self.existing_syms:
                tqdm.write(f"Data for {symbol} already exists. Skipping.")
                continue
            new_syms.append(symbol)
            api = "https://www.screener.in/api/company/search/?q=" + symbol
            tqdm.write("Getting: " + api)
            try:
                d = urlread(api)
                j = json.loads(d)[0]
                html = urlread('https://www.screener.in' + j['url'])
                results = re.findall(rexp,html)                
                j['warehouse'] = int(results[0])
                data.append(j)        
                tqdm.write("Downloading: " + symbol)
                data_out = self.getData(int(results[0])*1,symbol,PATH)
                if data_out is not None:
                    scraped_data[symbol] = data_out
            except:
                tqdm.write("Error: " + api)
            sleep(delay)
        if self.existing_syms and new_syms:
            tqdm.write(f"Appending {len(new_syms)} new symbols to existing file with {len(self.existing_syms)} symbols.")
            with open(os.path.join(self.data_dir, self.financials_file), "r") as f:
                existing_data = json.load(f)
            for k, v in scraped_data.items():
                if k not in existing_data:
                    existing_data[k] = v
            with open(os.path.join(self.data_dir, self.financials_file), "w") as f:
                json.dump(existing_data, f, indent=4, default=default_converter)
        elif new_syms:
            tqdm.write(f"Writing {len(new_syms)} new symbols to a new file.")
            with open(os.path.join(self.data_dir, self.financials_file), "w") as f:
                json.dump(scraped_data, f, indent=4, default=default_converter)
        self.existing_syms = self._load_existing_data_()
        return scraped_data
    
    def __locate_tables__(self,data):
        tables = []
        start = None
        for i in range(data.shape[0]):
            if data[i, 0] is not None and isinstance(data[i, 0], str) and data[i, 0].strip() != '' and start is None and data[i, 0].strip().lower() in ['profit & loss', 'quarters', 'balance sheet', 'cash flow:', 'price:']:
                start = i
                # print(f"Start : {start}")
            elif (data[i, 0] is None or (isinstance(data[i, 0], str) and data[i, 0].strip() == '')) and start is not None:
                tables.append((start, i - 1))
                start = None
        if start is not None:
            tables.append((start, data.shape[0] - 1))
        return tables
    
    def cleanup_json(self, scraped_data):
        sheet = scraped_data['Data Sheet']
        data = []
        for row in sheet.iter_rows(values_only=True):
            data.append(row)
        data = np.array(data)
        table_locations = self.__locate_tables__(data)
        result = {}
        result['pnl'] = np.array(data[table_locations[0][0]+1:table_locations[0][1]+1, :])
        result['quarters'] = np.array(data[table_locations[1][0]+1:table_locations[1][1]+1, :])
        result['balance_sheet'] = np.array(data[table_locations[2][0]+1:table_locations[2][1]+1, :])
        result['cash_flow'] = np.array(data[table_locations[3][0]+1:table_locations[3][1]+1, :])
        result['price'] = np.array([data[table_locations[0][0]+1, :],data[table_locations[4][0]:table_locations[4][1]+1, :][0]])
        # print(result['pnl'])
        
        # data = data[list(range(15, 31)) + list(range(56, 72)) + list(range(81, 85)) + [89], :]
        # print(np.array(data))
        # print(np.array(data).shape)

        # result = {row[0]: list(row[1:]) for row in data}
        for key, array in result.items():
            array = np.nan_to_num(array, nan=0.0)

        # other_assets = np.array(result['Other Assets'])
        # other_liabilities = np.array(result['Other Liabilities'])
        # # Compute Working Capital
        # result['Working Capital'] = list(other_assets - other_liabilities)
        # expense_cols = [
        #     'Raw Material Cost', 'Power and Fuel', 'Other Mfr. Exp',
        #     'Employee Cost', 'Selling and admin', 'Other Expenses'
        # ]
        # expense_arrays = [np.array(result[col]) for col in expense_cols]
        # total_expense = sum(expense_arrays)
        # total_expense -= np.array(result['Change in Inventory'])
        # result['Expense'] = list(total_expense)
        # result['Operating Profit'] = list(np.array(result['Sales']) - total_expense)
        # for key, values in result.items():
        #     if key == 'Report Date':
        #         continue
        #     result[key] = [round(float(v), 2) for v in values]
        return result

    def cleanup_df(self, scraped_data):
        financials = {}
        df = scraped_data
        df1 = df.iloc[[*range(14, 30), 88]].fillna(0).transpose()
        pnl_header = df1.iloc[0].values
        pnl_cols = df1.iloc[1:].values
        pnl = pd.DataFrame(pnl_cols, columns=pnl_header)
        expense_cols = ['Raw Material Cost', 'Power and Fuel', 'Other Mfr. Exp', 'Employee Cost', 'Selling and admin', 'Other Expenses']
        pnl['Expense'] = pnl[expense_cols].sum(axis=1)    
        pnl['Operating Profit'] = pnl['Sales'] - pnl['Expense']
        financials['Profit & Loss'] = pnl

        df1 = df.iloc[54:71].fillna(0).transpose()
        bs_header = df1.iloc[0].values
        bs_cols = df1.iloc[1:].values
        bs = pd.DataFrame(bs_cols, columns=bs_header)
        bs['Working Capital'] = bs['Other Assets'] - bs['Other Liabilities']
        financials['Balance Sheet'] = bs

        df1 = df.iloc[79:84].fillna(0).transpose()
        cf_header = df1.iloc[0].values
        cf_cols = df1.iloc[1:].values
        cf = pd.DataFrame(cf_cols, columns=cf_header)
        financials['Cash Flow'] = cf

            # prices = df.iloc[88:89].fillna(0).transpose()[1:]
            # print(prices.shape)
            # print(pnl_cols.shape)
            # print(bs_cols.shape)
            # print(cf_cols.shape)
            # statements['Metadata'] = pd.DataFrame(np.hstack([pnl_cols, bs_cols, cf_cols, prices]), columns=pnl_header)
        # print(financials.keys())
        # print(financials['RELIANCE'].keys())
        return financials
    
        # print(transf_scraped_data_df.shape)

        # req_conn_url = config.CONFIG_GLOBAL_DB.REQ_CONN_URL

        # resp, err = db.insert_dataframe_to_questdb(df=transf_scraped_data_df,
        #                                         table_name='financial_statements',
        #                                         timestamp_col='time_period_ts',
        #                                         req_conn_url=req_conn_url)
        
        # print(resp, err)

if __name__ == '__main__':

    from kiteconnect import KiteConnect
    import config
    from data import fetcher
    from data import db
    import os, sys
    import pandas as pd
    from io import BytesIO
    import xlwings as xl
    import time
    from datetime import datetime
    from tqdm import tqdm
    from data.daily_data_fetches.securities import Stocks

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(current_dir, '..', '..')
    sys.path.insert(0, project_root)

    fin_extractor = FinancialsExtractor()
    
    # stocks = Stocks(exchanges=['NSE', 'BSE'], instrument_types=['EQ'])
    # symbols = stocks.instruments['tradingsymbol'].head(300).tolist()
    # symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'SBIN', 'AXISBANK']
    symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'SBIN', 'AXISBANK', 'ITC', 'HDFCBANK', 'KOTAKBANK', 'LT', 'HCLTECH', 'ICICIBANK', 'BAJFINANCE', 'BHARTIARTL', 'ASIANPAINT', 'MARUTI', 'WIPRO', 'SUNPHARMA', 'TITAN', 'ULTRACEMCO', 'NESTLEIND', 'ADANIPORTS']

    financials_new = fin_extractor.scrape(symbols, PATH = os.path.join(project_root, "data", "scrapers"))

    print(f"Data available for: {fin_extractor.existing_syms}")

    data_dir = os.path.join(project_root, 'data', 'scrapers')
    financials_file = 'financials.json'
    with open(os.path.join(data_dir, financials_file), "r") as f:
        financials_all = json.load(f)
    # print(pd.DataFrame(financials_all['RELIANCE']))
    

    # print(json.dumps(financials_new, indent=4, default=default_converter))



    # df = fin_extractor.getData(6599230, 'TCS', os.path.join(project_root, "data", "scrapers"))
    # df.head(50)
    
    


    # f_scraper = FinancialsExtractor()
    # PATH = os.path.join(project_root, 'data')
    # warehouseid = 6594837  # Example warehouse ID for HDFCBANK
    # symbol = 'AXISBANK'
    # f_scraper.scrape_financials(warehouseid, symbol, PATH)