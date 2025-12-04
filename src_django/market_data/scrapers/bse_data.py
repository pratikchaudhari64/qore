
def bse_fetch_market_metadata(symb_slice):

    import market_data.quest_db as quest_db
    from bsedata.bse import BSE
    from retry import retry
    from tqdm import tqdm
    import requests
    import json
    import pandas as pd

    @retry(tries = 3, delay = 0.8, max_delay = 5, backoff=1.2, jitter=(1, 3))
    def get_bse_info(scripcode: str):
    
        url = "https://api.bseindia.com/BseIndiaAPI/api/ComHeadernew/w"

        
        params = {
            "quotetype": "EQ",
            "scripcode": scripcode
        }

        headers = {
            "Host": "api.bseindia.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bseindia.com/"
        }

        response = requests.get(url, headers=headers, params=params)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        return data
        
    # drop tables if exist
    tables = ['bse_eq_metadata']
    for table in tables:
        sql = f"DROP TABLE IF EXISTS {table};"
        quest_db.execute_query(sql)

    sql_query = """SELECT 
                DISTINCT(exchange_token)
                from kite_instruments_list
                where 1=1
                and instrument_type = 'EQ'
                and exchange in ('BSE')
                and segment in ('BSE')"""

    result = quest_db.execute_query(sql_query)
    alltokens = [token[0] for token in result['dataset']]

    res = {}
    success_cnt = 0
    err_cnt = 0

    if symb_slice!=None:
        alltokens = alltokens[:symb_slice]

    for token in tqdm(alltokens):
        try:
            bse_res = get_bse_info(scripcode=token)
            res[token] = json.dumps(bse_res)
            # print(f"{symbol}: {nse_res}")
            success_cnt+=1
        except Exception as e:
            error_details = {
                "error_type": type(e).__name__,  # e.g., "ValueError"
                "error_message": str(e),          # The error message (e.g., "Invalid symbol data for BAD_SYMBOL"
                "status": "failed"
                }
            res[token] = json.dumps(error_details)
            # print(f"{symbol}: {e}")
            err_cnt+=1
    
    try:
        res_df = pd.Series(res).to_frame(name='Data_JSON').reset_index().rename(columns={'index': 'Token'})
        res_df.loc[:, 'created_at'] = pd.Timestamp.now()
        res_df['created_at'] = res_df['created_at'].astype('datetime64[ns]')
        quest_db.insert_dataframe(
                            table_name='bse_eq_metadata',
                            df=res_df,
                            symbol_columns=['Token'],
                            timestamp_col='created_at'
                        )
        
        return {
            "status": "completed",
            "total_count": len(alltokens),
            "success_count": success_cnt,
            "error_count": err_cnt
        }

    except Exception as e:
        return {
            "status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }



if __name__ == '__main__':

    import os, sys
    import pandas as pd
    import django
    from django.conf import settings

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qore.settings")

    django.setup()

    res = bse_fetch_market_metadata(symb_slice=10)
    print(res)

