from .scrapers import screener, nse_data, bse_data
from .api_pulls import dhan_data
import market_data.quest_db as quest_db
import os
from dotenv import load_dotenv
from kiteconnect import KiteConnect
import pandas as pd
import json
from celery import shared_task
from django.utils import timezone

env_path = os.path.join(os.path.dirname(__file__), '..', 'qore', '.env')
load_dotenv(dotenv_path=env_path)

KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_API_SECRET = os.getenv("KITE_API_SECRET")

def get_kite_intrs():
    kite = KiteConnect(api_key=KITE_API_KEY)
    kiteall_instr = pd.DataFrame(kite.instruments())\
    
    return kiteall_instr

@shared_task
def renew_and_store_dhan_token():
    import requests
    from market_data.models import APICredentials
    
    # Get current credentials
    dhan_creds = APICredentials.objects.get(provider='dhan')
    
    url = 'https://api.dhan.co/v2/RenewToken'
    headers = {
        'access-token': dhan_creds.access_token,
        'dhanClientId': dhan_creds.metadata.get('client_id') if dhan_creds.metadata else ''
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # Update model fields
        dhan_creds.access_token = data.get('token')
        dhan_creds.metadata = {
            'createTime': data.get('createTime'),
            'expiryTime': data.get('expiryTime'),
            'client_id': dhan_creds.metadata.get('client_id') if dhan_creds.metadata else ''
        }
        dhan_creds.save()
        
        print("✅ Dhan token renewed and saved to database")
        return {
        'status': 'completed',
        'expiryTime': data.get('expiryTime')
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {
        'status': 'failed',
        'error': e
        }

@shared_task
def screener_fetch_and_store(symb_slice = None):
    """
    Fetch and store screener data one symbol at a time.
    Handles errors gracefully and continues processing.
    """
    
    # Get symbol list
    sql_query = """SELECT 
                DISTINCT(tradingsymbol)
                from kite_instruments_list
                where 1=1
                and instrument_type = 'EQ'
                and exchange in ('NSE', 'BSE')
                and segment in ('NSE', 'BSE')"""

    result = quest_db.execute_query(sql_query)
    symbollist = [sym[0] for sym in result['dataset']]

    if symb_slice is None:
        symbols = symbollist
    else:
        symbols = symbollist[:symb_slice]

    # Login once for all symbols
    login_session = screener.login_screener()
    
    # Track successes and failures
    scrape_errors = []
    storage_errors = []
    success_count = 0
    
    # Drop tables once at the beginning
    tables_to_drop = ['pnl', 'quarterly_pnl', 'bs', 'cf']
    for table in tables_to_drop:
        sql = f"DROP TABLE IF EXISTS {table};"
        quest_db.execute_query(sql)
        print(f"Dropped table: {table}")
    
    # Process each symbol individually
    from tqdm import tqdm
    for symbol in tqdm(symbols):
        try:
            # Scrape data for single symbol
            scraped_data, errors = screener.Scrape(
                symbols=[symbol], 
                session=login_session
            )
            
            # Check if scraping failed
            if errors:
                scrape_errors.append(symbol)
                print(f"Scraping failed for {symbol}")
                continue
            
            if not scraped_data or symbol not in scraped_data:
                scrape_errors.append(symbol)
                print(f"No data returned for {symbol}")
                continue
            
            # Format the data
            formatted_data = screener.get_formatted_data(
                scraped_data={symbol: scraped_data[symbol]}
            )
            
            if symbol not in formatted_data:
                scrape_errors.append(symbol)
                continue
            
            # Extract dataframes
            pnl_df = scraped_data[symbol]['formatted_data']['pnl']
            quarterly_pnl_df = scraped_data[symbol]['formatted_data']['quarterly_pnl']
            bs_df = scraped_data[symbol]['formatted_data']['bs']
            cf_df = scraped_data[symbol]['formatted_data']['cf']
            
            # Add symbol column
            for df in [pnl_df, quarterly_pnl_df, bs_df, cf_df]:
                if not df.empty:
                    df['symbol'] = symbol
            
            # Helper to safely convert dict to JSON
            def safe_json_convert(df):
                if df.empty or 'items' not in df.columns:
                    return df
                
                def safe_dumps(x):
                    if isinstance(x, dict):
                        import pandas as pd
                        cleaned = {k: (None if pd.isna(v) else v) 
                                  for k, v in x.items()}
                        return json.dumps(cleaned)
                    return x
                
                df['items'] = df['items'].apply(safe_dumps)
                return df
            
            # Convert dicts to JSON strings
            pnl_df = safe_json_convert(pnl_df)
            quarterly_pnl_df = safe_json_convert(quarterly_pnl_df)
            bs_df = safe_json_convert(bs_df)
            cf_df = safe_json_convert(cf_df)
            
            # Store to database (one symbol at a time)
            try:
                if not pnl_df.empty:
                    quest_db.insert_dataframe(
                        table_name='pnl',
                        df=pnl_df,
                        symbol_columns=['symbol'],
                        timestamp_col='report_date'
                    )
                
                if not quarterly_pnl_df.empty:
                    quest_db.insert_dataframe(
                        table_name='quarterly_pnl',
                        df=quarterly_pnl_df,
                        symbol_columns=['symbol'],
                        timestamp_col='report_date'
                    )
                
                if not bs_df.empty:
                    quest_db.insert_dataframe(
                        table_name='bs',
                        df=bs_df,
                        symbol_columns=['symbol'],
                        timestamp_col='report_date'
                    )
                
                if not cf_df.empty:
                    quest_db.insert_dataframe(
                        table_name='cf',
                        df=cf_df,
                        symbol_columns=['symbol'],
                        timestamp_col='report_date'
                    )
                
                success_count += 1
                
            except Exception as e:
                storage_errors.append({'symbol': symbol, 'error': str(e)})
                print(f"Storage failed for {symbol}: {e}")
                continue
        
        except Exception as e:
            scrape_errors.append(symbol)
            print(f"Unexpected error for {symbol}: {e}")
            continue
    
    # Save error logs
    errors_df = pd.DataFrame({
        'scrape_errors': pd.Series(scrape_errors),
        'storage_errors': pd.Series([str(e) for e in storage_errors])
    })
    errors_df.to_csv('screener_fetch_errors.csv', index=False)  
    
    return {
        'status': 'completed',
        'timestamp': timezone.now().isoformat(),
        'total_symbols': len(symbols),
        'success_count': success_count,
        'scrape_error_count': len(scrape_errors),
        'storage_error_count': len(storage_errors)
    }

@shared_task
def dhan_fetch_hist_data(symb_slice = None):

    
    exch_tokens, errors, success_count, errors_df = dhan_data.fetch_hist_data_and_store(slice_i=symb_slice)
    errors_df.to_csv('dhan_api_errors.csv', index=False)
    return {
        'status': 'completed',
        'total_symbols': len(exch_tokens),
        'total_errors': len(errors),
        'total_success_count': success_count
    }
    
@shared_task
def nse_fetch_metadata_and_store(symbslice = None):

    nse_fetch_res = nse_data.nse_fetch_market_metadata(symb_slice=symbslice)

    return nse_fetch_res

@shared_task
def bse_fetch_metadata_and_store(symbslice = None):
    
    bse_fetch_res = bse_data.bse_fetch_market_metadata(symb_slice=symbslice)
    
    return bse_fetch_res

if __name__ == '__main__':

    import os, sys
    import django
    from django.conf import settings

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qore.settings")

    django.setup()

    res = dhan_fetch_hist_data(symb_slice=50)
    print(res)

    pass