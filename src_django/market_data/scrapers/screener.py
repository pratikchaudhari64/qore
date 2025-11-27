import requests
import re
import logging
from tqdm import tqdm
import pandas as pd
import xlwings
import json
# from .urlread import *
import urllib.request
import io
import numpy as np
import time
from dotenv import load_dotenv
import os

env_path = os.path.join(os.path.dirname(__file__), '..', '..', 'qore', '.env')
load_dotenv(dotenv_path=env_path)

SCRENER_EMAIL = os.getenv("SCRENER_EMAIL")
SCRENER_PASSWORD = os.getenv("SCRENER_PASSWORD")

def login_screener():
    """Performs the login sequence to establish an authenticated session."""
    session = requests.Session()     
    LOGIN_URL = "https://www.screener.in/login/"
    
    try:
        # --- Step 1: GET Request to fetch the initial CSRF token ---
        
        login_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
            "Referer": "https://www.screener.in/login/"
        }
        
        r_get = session.get(LOGIN_URL, headers=login_headers, timeout=10)
        r_get.raise_for_status()

        # Extract the CSRF token from the HTML form
        csrf_match = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', r_get.text)
        if not csrf_match:
            print("Failed to find initial CSRF token on login page.")
            return False
            
        initial_csrf_token = csrf_match.group(1)

        # --- Step 2: POST Request to log in ---
        
        login_payload = {
            'csrfmiddlewaretoken': initial_csrf_token,
            'username': SCRENER_EMAIL,
            'password': SCRENER_PASSWORD,
            'next': '/', # Redirect to home page after login
        }
        
        # The session automatically sends the cookies received from Step 1
        r_post = session.post(LOGIN_URL, data=login_payload, headers=login_headers, timeout=10)

        # Check if login was successful (e.g., check for a redirect or a known page element)
        # A successful login usually redirects you away from the login URL
        if r_post.url == LOGIN_URL:
            # If the URL is still the login page, authentication failed
            print("Login failed. Check username/password.")
            return False
        
        print("Login successful. Session established.")
        
        # Update the session's headers for subsequent scraping requests
        session.headers.update({
            'Referer': 'https://www.screener.in/dashboard/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'none',
            'Accept-Language': 'en-US,en;q=0.8',
            'X-CSRFToken': session.cookies.get('csrftoken') # Use the new CSRF token from the session cookies
        })
        
        return session

    except Exception as e:
        print(f"Error during login process: {e}")
        return False
    
def getData(warehouseid,session, symbol,PATH):
    
    url = 'https://www.screener.in/user/company/export/{}/'.format(warehouseid)

    csrf_token = session.cookies.get('csrftoken')
    payload = {
        'csrfmiddlewaretoken': csrf_token,
        'next': f'/company/{symbol}/consolidated/'  # Use the symbol you are scraping
    }

    r = session.post(url, data = payload)

    return r

def Scrape(symbols,session, PATH = None,delay=0.2):
    error_symbols = []
    data = []
    exported_data = {}
    rexp = r'formaction=.\/user\/company\/export/([0-9]+)\/.'
    for symbol in tqdm(symbols):
        api = "https://www.screener.in/api/company/search/?q=" + symbol    
        
        try:
            d = urlread(api, header = session.headers)
            j = json.loads(d)[0]
            # print(json.loads(d))
            # html = urlread('https://www.screener.in' + j['url'])
            html = urlretry3('https://www.screener.in' + j['url'])   
            # print(html)     
            results = re.findall(rexp,html)
        
            # print(results)
            j['warehouse'] = results[0]
            data.append(j)        
        


            data_df = getData(warehouseid=results[0], session=session, symbol=symbol, PATH=None)
            file_data = io.BytesIO(data_df.content)
            read_df = pd.read_excel(
                        file_data, 
                        # header=2, 
                        sheet_name=None, 
                        engine='openpyxl'
                    )

            exported_data[symbol] = read_df
        except:
            # print("Error: " + api)
            # logging.error(api)
            error_symbols.append(symbol)
        time.sleep(1)
    
    return exported_data, error_symbols

def locate_tables(data):
    # Ensure data is a NumPy array for consistent checking
    if not isinstance(data, np.ndarray):
        # This conversion step is crucial for consistent behavior
        data = np.array(data) 
        
    tables = []
    start = None
    
    for i in range(data.shape[0]):
        cell_value = data[i, 0]

        # --- CONDITION 1: Find the Start of a Table ---
        # The logic here is mostly correct: check if it's a non-empty string and a known header.
        is_start_marker = (
            cell_value is not None and 
            isinstance(cell_value, str) and 
            cell_value.strip().lower() in ['profit & loss', 'quarters', 'balance sheet', 'cash flow:', 'price:']
        )
        
        if is_start_marker and start is None:
            start = i
            # print(f"Found Start at: {start}") # Debugging print
        
        # --- CONDITION 2: Find the End of a Table (The likely point of failure) ---
        # A table ends when the first column is empty, AND we are currently tracking a table (start is not None).
        
        # Check for empty markers: None, empty string, or NumPy NaN/inf
        is_end_marker = False
        
        if cell_value is None or (isinstance(cell_value, str) and cell_value.strip() == ''):
            is_end_marker = True
        
        # Crucial check for NumPy NaN/float-like missing values
        elif isinstance(cell_value, (int, float)) and np.isnan(cell_value):
            is_end_marker = True
        
        # Additional check: If the cell is np.nan and the dtype is 'object'
        elif isinstance(cell_value, float) and np.isnan(cell_value) and data.dtype == 'object':
            is_end_marker = True
        
        
        if is_end_marker and start is not None:
            tables.append((start, i - 1)) # The end is the row before the blank line
            start = None
            # print(f"Found End at: {i - 1}. Table found: {tables[-1]}") # Debugging print
            
    # --- CONDITION 3: Handle the last table ---
    if start is not None:
        tables.append((start, data.shape[0] - 1))
        
    return tables
    

def get_formatted_data(scraped_data):
    for symbol in scraped_data:
        scraped_data[symbol]['formatted_data'] = {}
        data = scraped_data[symbol]['Data Sheet'].values
        table_locations = locate_tables(data)
        # print(table_locations)
        
        for loc in table_locations:
            table = scraped_data[symbol]['Data Sheet'].loc[loc[0]:loc[1]]
            table_name = table.iloc[0 ,0]

            if table_name.lower() in ['profit & loss', 'quarters', 'balance sheet', 'cash flow:']:
                modified_table = scraped_data[symbol]['Data Sheet'].loc[loc[0]+1:loc[1]]

                # Find the row index where 'Report Date' is located
                report_date_idx = modified_table[modified_table.iloc[:, 0] == 'Report Date'].index[0]

                # Set that row as the new column headers
                modified_table.columns = modified_table.loc[report_date_idx].values

                # Drop all rows up to and including the Report Date row
                modified_table = modified_table.loc[report_date_idx + 1:].reset_index(drop=True)

                modified_table.set_index(modified_table.columns[0], inplace=True)

                modified_table = modified_table.loc[:, ~modified_table.columns.isna() & ~modified_table.columns.duplicated()]
                # print(modified_table.to_dict('dict'))
                formatted_table = modified_table.to_dict('dict')

                df_new = pd.DataFrame({
                    'report_date': list(formatted_table.keys()),
                    'items': list(formatted_table.values())
                })

                if table_name.lower()=='profit & loss':
                    scraped_data[symbol]['formatted_data']['pnl'] = df_new
                if table_name.lower()=='quarters':
                    scraped_data[symbol]['formatted_data']['quarterly_pnl'] = df_new
                if table_name.lower()=='balance sheet':
                    scraped_data[symbol]['formatted_data']['bs'] = df_new
                if table_name.lower()=='cash flow:':
                    scraped_data[symbol]['formatted_data']['cf'] = df_new
    
    return scraped_data
    
if __name__ == '__main__':

    from urlread import *
    
    symbols = ['SWIGGY']

    login_session = login_screener()
    scraped_data, err = Scrape(symbols=symbols, session = login_session)
    # print(scraped_data['SWIGGY'])
    formatted_scraped_data = get_formatted_data(scraped_data={'SWIGGY':scraped_data['SWIGGY']})
    # print(formatted_scraped_data['SWIGGY']['formatted_data']['pnl'])
    # for sym in formatted_scraped_data:
    #     print(scraped_data[sym]['formatted_data'].keys())
else:
    from .urlread import *