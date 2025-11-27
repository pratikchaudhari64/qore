

def dhanapifetch_hist_data(security_id: str, exchange_segment: str, dhan_client):
     
    import datetime as dt

    today = dt.date.today()
    today_date_str = today.strftime('%Y-%m-%d')    

    dhan = dhan_client

    try:
        daily_data = dhan.historical_daily_data(
            security_id=security_id,               # Example: Security ID for a scrip (e.g., HDFC Bank)
            exchange_segment=exchange_segment,        # NSE Equity segment
            instrument_type='EQUITY',         # Instrument Type
            from_date='1990-01-01',           # Start date in 'YYYY-MM-DD' format
            to_date=today_date_str              # End date in 'YYYY-MM-DD' format (non-inclusive)
        )
        
        return daily_data
    except Exception as e:
        return daily_data

def fetch_hist_data_and_store(slice_i = None):

    import market_data.quest_db as quest_db
    from market_data.models import APICredentials
    from dhanhq import dhanhq
    import time
    from tqdm import tqdm
    import pandas as pd
    import json

    dhan_creds = APICredentials.objects.get(provider='dhan')
    dhan = dhanhq(dhan_creds.metadata.get('client_id'), dhan_creds.access_token)

    sql = """
        with kite_instr_list as
            (
            SELECT (exchange_token)::int as exch_token ,*
            from kite_instruments_list
            ),

        query as
            (
            select 
            kite_instr_list.tradingsymbol, kite_instr_list.instrument_type, kite_instr_list.exchange, kite_instr_list.segment, kite_instr_list.exch_token, kite_instr_list.exchange_token,
            kite_instr_list.name,
            dhan_full_instruments_list.*
            from kite_instr_list
            left join dhan_full_instruments_list on kite_instr_list.exch_token = dhan_full_instruments_list.SECURITY_ID
            where 1=1
            and kite_instr_list.instrument_type = 'EQ'
            and kite_instr_list.exchange in ('NSE', 'BSE')
            and kite_instr_list.segment in ('NSE', 'BSE')
            and dhan_full_instruments_list.SECURITY_ID is not null
            and dhan_full_instruments_list.INSTRUMENT = 'EQUITY'
            )
        
        select exch_token::varchar, concat(exchange, '_EQ') as exchange_segment from query;
        """

    result = quest_db.execute_query(sql)
    all_exch_tokens = result['dataset']
    
    # drop tables if exist
    tables = ['daily_historical_prices', 'dhan_api_fetch_errors']
    for table in tables:
        sql = f"DROP TABLE IF EXISTS {table};"
        quest_db.execute_query(sql)

    if slice_i == None:
        exch_tokens = all_exch_tokens
    else:
        exch_tokens = all_exch_tokens[:slice_i]
    errors = []
    success_count = 0
    for i in tqdm(exch_tokens):
        output = dhanapifetch_hist_data(security_id=i[0], exchange_segment=i[1], dhan_client=dhan)

        if output['status'] == 'success':
            data_pull = pd.DataFrame(output['data'])
            data_pull['timestamp'] = pd.to_datetime(data_pull['timestamp'], unit='s').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
            data_pull.loc[:, 'security_id'] = i[0]
            # print(data_pull)
            quest_db.insert_dataframe(
                        table_name='daily_historical_prices',
                        df=data_pull,
                        symbol_columns=['security_id'],
                        timestamp_col='timestamp'
                    )
            success_count+=1
        else:
            errors.append([i[0], i[1], output])
        
        time.sleep(0.28)
    
    print(f"total symbols: {len(exch_tokens)}")
    print(f"total errors: {len(errors)}")
    print(f"total success count: {success_count}")
    errors_df = pd.DataFrame(errors, columns=['security_id', 'exchange_segment', 'error_response'])
    
    if not errors_df.empty:
        errors_df['created_at'] = pd.to_datetime('now')
        errors_df['error_response'] = errors_df['error_response'].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)
        try:
            quest_db.insert_dataframe(
                table_name='dhan_api_fetch_errors',
                df=errors_df,
                # symbol_columns=None,  # or whatever columns make sense
                timestamp_col='created_at'
            )
        except Exception as e:
            print(e)
        finally: 
            pass

    return exch_tokens, errors, success_count, errors_df
    

if __name__== '__main__':
    import os, sys
    import pandas as pd
    import django
    from django.conf import settings

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qore.settings")

    django.setup()

    exch_tokens, errors, success_count, errors_df = fetch_hist_data_and_store(slice_i=1000)

    # import market_data.quest_db as quest_db
    # from market_data.models import APICredentials
    # from dhanhq import dhanhq
    # import time

    # dhan_creds = APICredentials.objects.get(provider='dhan')
    # dhan = dhanhq(dhan_creds.metadata.get('client_id'), dhan_creds.access_token)

    # sql = """
    #     with kite_instr_list as
    #         (
    #         SELECT (exchange_token)::int as exch_token ,*
    #         from kite_instruments_list
    #         ),

    #     query as
    #         (
    #         select 
    #         kite_instr_list.tradingsymbol, kite_instr_list.instrument_type, kite_instr_list.exchange, kite_instr_list.segment, kite_instr_list.exch_token, kite_instr_list.exchange_token,
    #         kite_instr_list.name,
    #         dhan_full_instruments_list.*
    #         from kite_instr_list
    #         left join dhan_full_instruments_list on kite_instr_list.exch_token = dhan_full_instruments_list.SECURITY_ID
    #         where 1=1
    #         and kite_instr_list.instrument_type = 'EQ'
    #         and kite_instr_list.exchange in ('NSE', 'BSE')
    #         and kite_instr_list.segment in ('NSE', 'BSE')
    #         and dhan_full_instruments_list.SECURITY_ID is not null
    #         and dhan_full_instruments_list.INSTRUMENT = 'EQUITY'
    #         )
        
    #     select exch_token::varchar, concat(exchange, '_EQ') as exchange_segment from query;
    #     """

    # result = quest_db.execute_query(sql)
    # all_exch_tokens = result['dataset']
    
    # table = 'daily_historical_prices'
    # sql = f"DROP TABLE IF EXISTS {table};"
    # quest_db.execute_query(sql)
    
    # errors = []
    # for i in all_exch_tokens[:2]:
    #     output = fetch_hist_data(security_id=i[0], exchange_segment=i[1], dhan_client=dhan)

    #     if output['status'] == 'success':
    #         data_pull = pd.DataFrame(output['data'])
    #         data_pull['timestamp'] = pd.to_datetime(data_pull['timestamp'], unit='s').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    #         data_pull.loc[:, 'security_id'] = i[0]
    #         print(data_pull)
    #         quest_db.insert_dataframe(
    #                     table_name='daily_historical_prices',
    #                     df=data_pull,
    #                     symbol_columns=['security_id'],
    #                     timestamp_col='timestamp'
    #                 )
    #     else:
    #         errors.append([i[0], i[1], output])
        
    #     time.sleep(0.4)
    
    # print(f"total symbols: {len(all_exch_tokens)}")
    # print(f"total errors: {len(errors)}")
    # print(f"errors: {errors}")