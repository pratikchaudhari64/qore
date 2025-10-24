# db_module.py

import os, sys
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

from questdb.ingress import Sender, TimestampNanos
import psycopg
import requests
import json
from stonks import config


conn_str = config.CONFIG_GLOBAL_DB.CONN_STRING
conn_url = config.CONFIG_GLOBAL_DB.REQ_CONN_URL
req_url = config.CONFIG_GLOBAL_DB.REQUESTS_URL
questdb_user = config.CONFIG_GLOBAL_DB.QUESTDB_HTTP_USERNAME
questdb_pwd = config.CONFIG_GLOBAL_DB.QUESTDB_HTTP_PASSWORD


def check_table_exists(table_name: str) -> bool:
    """
    Uses PostgreSQL wire protocol to check table existence.
    """
    # with psycopg.connect(conn_str) as conn:
    #     with conn.cursor() as cur:
    #         # query = f"SELECT EXISTS (SELECT * FROM {table_name} limit 1);"
    #         # query = f"SELECT count(*) FROM pg_tables WHERE tablename = {table_name}"
    #         query = f"SHOW COLUMNS FROM {table_name};"
    #         print(query)
    #         cur.execute(
    #             query
    #         )
    #         exists = cur.fetchone()[0]
    query = f"SHOW COLUMNS FROM {table_name};"
    # query = "select * from trades limit 5;"
    resp = read_questdb_req(readsql_query=query)
    resp_json = json.loads(resp)
    if "error" in resp_json.keys():
        return False
    else:
        return True
    

def insert_dataframe_to_questdb(df, table_name: str, 
                                timestamp_col: str, req_conn_url: str):
    """
    Inserts all rows from DataFrame to QuestDB if the table exists. Otherwise, returns an error.
    """
    # conn_str e.g.: 'user=admin password=quest host=localhost port=8812 dbname=qdb'
    # conn_str = "user=admin password=quest host=localhost port=8812 dbname=qdb"
    print('checking if table exists')
    if check_table_exists(table_name=table_name):
        logger.info(f"{table_name} exists!")
    else:
        return logger.warning(f"insertion not done for: {table_name}")
    

    # Insert using QuestDB native ingestion for speed
    logger.info(f"inserting into {table_name} now... with {req_conn_url}")
    try: 
        with Sender.from_conf(req_conn_url) as sender:
            sender.dataframe(df, table_name=table_name, at = timestamp_col)
            sender.flush()
            logger.info(f"Inserted {len(df)} rows to '{table_name}' successfully.")
            return True, None
    except Exception as err:
        return False, err


def read_questdb_req(readsql_query, req_url = req_url):
    params = {
        "query": readsql_query,
        "fmt": "json"   # You can also use "csv"
    }
    response = requests.get(url = req_url, 
                            params=params,
                            auth=(questdb_user, questdb_pwd))
    data = response.json()
    return json.dumps(data, indent=2)


def del_questdb_req(delsql_query, req_url = req_url):
    '''Use TRUNCATE TABLE'''
    params = {
        "query": delsql_query,
        "fmt": "json"   
    }
    try:
        response = requests.get(url = req_url, 
                                params=params,
                                auth=(questdb_user, questdb_pwd))
        
        return response.json()
    except:
        logger.warning("failed to run")
        return None



def create_table_with_columns(conn_str: str, table_name: str, 
                              columns: dict, ):
    """
    Creates a table with the specified column names/types, timestamp, and partitioning.
    - columns: dict of {column_name: data_type}, e.g., {"ts": "TIMESTAMP", "symbol": "SYMBOL", "price": "DOUBLE"}
    """
    col_defs = [f"{col} {typ}" for col, typ in columns.items()]
    cols_str = ", ".join(col_defs)
    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
      {cols_str}
    ) TIMESTAMP (time_period_ts) PARTITION BY DAY WAL; 
    """
    print(conn_str)
    print(sql)
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()
    print(f"Table '{table_name}' created or already exists.")

if __name__ == "__main__":

    # columns_for_financials_table = {
    #     "time_period_ts": "TIMESTAMP",  # This will be your designated timestamp column
    #     "stock_ticker": "SYMBOL",
    #     "pnl": "STRING",
    #     "balance_sheet": "STRING",
    #     "cash_flows": "STRING"
    # }
    # create_table_with_columns(
    #         conn_str=conn_str,
    #         table_name='financial_statements',
    #         columns=columns_for_financials_table
    #     )
    
    # columns = {"timestamp": "TIMESTAMP", 
    #            "symbol": "SYMBOL", 
    #            "industry": "VARCHAR", 
    #            "close": "DOUBLE"}
    # create_table_with_columns(conn_str, 
    #                           "daily_holdings", 
    #                           columns, 
    #                           timestamp_col="timestamp", 
    #                         )

    # resp = del_questdb_req(delsql_query="TRUNCATE TABLE daily_holdings;")
    # print(resp)
    # import pandas as pd
    # from datetime import datetime
    # df = pd.read_csv("C:/Users/pratc/Downloads/nse_official_industry_mapping.csv")
    # df.loc[:, 'timestamp'] = datetime.now()
    # # df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ns')
    # df['timestamp'] = df['timestamp'].astype('datetime64[ns]') # Then explicitly cast to nanosecond precision
    # print(df['timestamp'].dtype)

    # columns = {
    #     "timestamp": "TIMESTAMP",
    #     "mes_code": "SYMBOL",
    #     "macro_econ_sector": "VARCHAR",
    #     "sect_code": "SYMBOL",
    #     "sector": "VARCHAR",
    #     "industry_code": "SYMBOL",
    #     "industry": "VARCHAR",
    #     "basic_industry_code": "SYMBOL",
    #     "basic_industry": "VARCHAR",
    #     "definition": "VARCHAR"
    # }

    # create_table_with_columns(conn_str, 
    #                           "market_daily", 
    #                           columns 
    #                         )
    
    # resp = insert_dataframe_to_questdb(df, table_name= 'nse_official_industry_map',
    #                                    timestamp_col="timestamp", req_conn_url=conn_url)
    # print(resp)


    # sql_query = "select * from trades;"
    
    # url = "http://localhost:9000/exec"

    # # Provide the query parameters
    # params = {
    #     "query": sql_query,
    #     "fmt": "json"   # You can also use "csv"
    # }
    # print(read_questdb_req(url, params=params))

    pass