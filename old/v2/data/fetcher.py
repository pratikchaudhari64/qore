"""
data/fetcher.py
Responsible for fetching asset and strategy data from database or external APIs.
"""



import time
# from datetime import datetime
import os, sys
from typing import List, Dict, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

from tqdm import tqdm
from data import db
# from kiteconnect import KiteConnect
from nsepython import *

# Placeholder for DB/API connection imports

class AuthData:

    def __init__(self, 
                 kc_instance: object):
        self.init_alert = 'obj_init'
        self.kc_instance = kc_instance
    
    def test_profile(self):
        """Fetches user profile data"""
        return self.kc_instance.profile()
    
    def test_holdings(self):
        """Fetches user holdings data"""
        return self.kc_instance.holdings()
    
    def test_orders(self):
        """Fetches user orders data"""
        return self.kc_instance.orders()
    
    def test_quotes(self, instruments):
        """Fetches real-time quotes for given instruments"""
        return self.kc_instance.quote(instruments)
    
    def test_instruments(self):
        """Fetches all available instruments data"""
        return self.kc_instance.instruments()
    
    '''FREE NSEPI TO FETCH INDSUTRY AND QUOTES: 
     - coverage of industry is good, 
     - but not of close, 
     - and batch fetch not available. averages 1.5-2s per symbol!''' 
    def test_nsepy_quotes(self, symbols_list):
        # data = nse_quote(symbol)
        all_symb_list = symbols_list
        info_collected = []
        error_symbols = []
        for symbol in tqdm(all_symb_list):
            time.sleep(2)
            nsepy_quote = nse_quote(symbol)

            if 'error' not in nsepy_quote.keys():
                try:
                    ind = nsepy_quote['info']['industry']
                except:
                    ind = None
            
                try:
                    underlyingval = nsepy_quote['underlyingValue']
                except:
                    underlyingval = None

                try:
                    priceInfo = nsepy_quote['priceInfo']['close']
                except:
                    priceInfo = None
                
                daily_info = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), 
                              "symbol": symbol, 
                              "industry": ind, 
                              "close": underlyingval or priceInfo}
                
                info_collected.append(daily_info)
            else:
                error_symbols.append(symbol)

        return info_collected, error_symbols
    
    def test_nse_get_top_gainers(self):
        data = nse_get_top_gainers()
        return data
    
    def nse_corp_info(self):
        import requests

        # headers = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        #     "Accept-Language": "en-US,en;q=0.9",
        #     "Referer": "https://www.nseindia.com/get-quotes/equity?symbol=ADANIENT",
        #     "Origin": "https://www.nseindia.com",
        # }

        # session = requests.Session()
        # session.headers.update(headers)

        # Visit homepage first to get cookies
        # test_resp = session.get("https://www.nseindia.com")
        # print(test_resp.status_code)

        # URL for corporate info JSON
        # api_url = "https://www.nseindia.com/api/corporate-info?symbol=ADANIENT"
        api_url = "https://www1.nseindia.com/homepage/peDetails.json'"
        response = requests.get(api_url)
        print(response)

        return response

    
    # def test_positions(self):
    #     """Fetches user positions data"""
    #     return self.kc_instance.positions()
    
    # def test_trades(self):
    #     """Fetches user trades data"""
    #     return self.kc_instance.trades()

class FRONTPAGEDATA:

    def __init__(self):
        self.init_alert = 'obj_init'

    def test_kiteapi_call_holdings(self):
        holdings = self.kc_instance.holdings()
        return holdings
    
    def fetch_holdings(self):

        frontpage_sql = """SELECT
                    dl.*, nsmap.*
                    from daily_holdings as dl
                    left join nse_official_industry_map as nsmap on nsmap.basic_industry = dl.industry"""
    
        data = db.read_questdb_req(readsql_query=frontpage_sql)
        json_data = json.loads(data)
        
        
        columnnames = [col_meta['name'] for col_meta in json_data['columns']]
        df_data = pd.DataFrame(json_data['dataset'], columns=columnnames)
        
        return df_data
    
    def fetch_market(self):
        sql = f"""
            select count(*) as market_data_count from market_daily;
            """
        data = db.read_questdb_req(readsql_query=sql)
        json_data = json.loads(data)

        columnnames = [col_meta['name'] for col_meta in json_data['columns']]
        df_data = pd.DataFrame(json_data['dataset'], columns=columnnames)

        return df_data
    
    def latest_data(self):

        sql = """SELECT max(timestamp) as latest_market_data_fetch from market_daily;"""
        data = db.read_questdb_req(readsql_query=sql)
        json_data = json.loads(data)
        
        
        columnnames = [col_meta['name'] for col_meta in json_data['columns']]
        df_data = pd.DataFrame(json_data['dataset'], columns=columnnames)

        return df_data

        


class DataFetcher:
    """Fetches asset and portfolio strategy data for dashboards and analysis."""

    def __init__(self, db_connection=None):
        # db_connection: connection/session for your database or ORM
        self.db = db_connection

    def fetch_dashboard_data(self, strategies: Optional[List[dict]] = None) -> Dict:
        """
        Fetch all stock/asset data needed for dashboard display.
        Args:
            strategies: List of strategy objects (or dicts) to extract symbols.
        Returns:
            Dictionary keyed by asset symbol, with relevant price/meta data.
        """
        symbols = set()
        if strategies:
            for strat in strategies:
                # Assume each strategy has an 'assets' list with dicts containing 'symbol'
                for asset in strat.assets:
                    symbol = asset.get('symbol') if isinstance(asset, dict) else None
                    if symbol:
                        symbols.add(symbol)

        # Simulate DB/API calls to fetch asset data for each unique symbol
        stock_data = {}
        for sym in symbols:
            stock_data[sym] = self.fetch_single_stock_data(sym)

        return stock_data

    def fetch_single_stock_data(self, symbol: str) -> dict:
        """
        Fetch full historical and metadata for a single asset symbol.
        Placeholder for real database or API integration.
        """
        return {
            'symbol': symbol,
            'price_history': [],  # List of OHLCV dicts or records
            'fundamentals': {},   # Company/ETF fundamentals
            'metadata': {},       # Sector, exchange, etc.
        }



if __name__ == "__main__":

    import requests
    import json

    sql_query = "SELECT timestamp, symbol FROM trades;"

    # Set the QuestDB HTTP endpoint
    url = "http://localhost:9000/exec"

    # Provide the query parameters
    params = {
        "query": sql_query,
        "fmt": "json"   # You can also use "csv"
    }

    # Send GET request
    response = requests.get(url, params=params)

    # Parse JSON response
    data = response.json()
    print(json.dumps(data, indent=2))

    pass