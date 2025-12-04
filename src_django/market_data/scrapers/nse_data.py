

def nse_fetch_market_metadata(symb_slice):

    import json
    import requests
    import market_data.quest_db as quest_db
    from retry import retry
    from tqdm import tqdm
    import datetime
    import pandas as pd

    @retry(tries = 3, delay = 0.8, max_delay = 5, backoff=1.2, jitter=(1, 3))
    def get_nse_info(symbol: str):
        url = "https://www.nseindia.com/api/quote-equity"
        
        params = {
            "symbol": symbol
        }

        headers = {
            "Host": "www.nseindia.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        return data

    # drop tables if exist
    tables = ['nse_eq_metadata']
    for table in tables:
        sql = f"DROP TABLE IF EXISTS {table};"
        quest_db.execute_query(sql)

    sql_query = """SELECT 
                DISTINCT(tradingsymbol)
                from kite_instruments_list
                where 1=1
                and instrument_type = 'EQ'
                and exchange in ('NSE')
                and segment in ('NSE')"""

    result = quest_db.execute_query(sql_query)
    allsymbols = [symb[0] for symb in result['dataset']]

    res = {}
    success_cnt = 0
    err_cnt = 0

    if symb_slice!=None:
        allsymbols = allsymbols[:symb_slice]

    for symbol in tqdm(allsymbols):
        try:
            nse_res = get_nse_info(symbol=symbol)
            res[symbol] = json.dumps(nse_res)
            # print(f"{symbol}: {nse_res}")
            success_cnt+=1
        except Exception as e:
            error_details = {
                "error_type": type(e).__name__,  # e.g., "ValueError"
                "error_message": str(e),          # The error message (e.g., "Invalid symbol data for BAD_SYMBOL"
                "status": "failed"
                }
            res[symbol] = json.dumps(error_details)
            # print(f"{symbol}: {e}")
            err_cnt+=1
    
    try:
        res_df = pd.Series(res).to_frame(name='Data_JSON').reset_index().rename(columns={'index': 'Symbol'})
        res_df.loc[:, 'created_at'] = pd.Timestamp.now()
        res_df['created_at'] = res_df['created_at'].astype('datetime64[ns]')
        quest_db.insert_dataframe(
                            table_name='nse_eq_metadata',
                            df=res_df,
                            symbol_columns=['Symbol'],
                            timestamp_col='created_at'
                        )
        
        return {
            "status": "completed",
            "total_count": len(allsymbols),
            "success_count": success_cnt,
            "error_count": err_cnt
        }

    except Exception as e:
        return {
            "status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }
    


if __name__=='__main__':

    import os, sys
    import pandas as pd
    import django
    from django.conf import settings

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qore.settings")

    django.setup()

    # from nsepython import *
    # res = nse_fetch_market_metadata(symb_slice=5)

    # print(res)
    # print(pd.DataFrame(res))
    # df = pd.Series(res).to_frame(name='Data_JSON').reset_index().rename(columns={'index': 'Symbol'})
    # print(df)
    

    