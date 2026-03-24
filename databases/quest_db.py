from questdb.ingress import Sender, IngressError, TimestampNanos  # <-- 1. Import TimestampNanos
import pandas as pd
import requests
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '..', 'src_django', 'qore', '.env')
load_dotenv(dotenv_path=env_path)


# --- Configuration ---
# 3. Get the variables from the environment using os.getenv()
ILP_CONF = os.getenv("ILP_CONF")
HTTP_URL = os.getenv("HTTP_URL") 

def insert_data(table_name: str, rows: list[dict], symbol_columns: list = None, timestamp_col: str = 'ts'):
    """
    (C)REATE: Inserts rows of data into a QuestDB table using ILP.
    This function is ideal for bulk-inserting data fetched from APIs.
    Creates Table if it does not exist.

    Args:
        table_name (str): The name of the target table.
        rows (list[dict]): A list of dictionaries, where each dict represents a row (e.g., one candle).
        symbol_columns (list, optional): A list of column names to be treated as SYMBOLs (e.g., ['ticker']).
        timestamp_col (str, optional): The dict key for the designated timestamp.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    if not rows:
        print("Warning: No rows provided to insert.")
        return True

    symbol_columns = symbol_columns or []

    try:
        with Sender.from_conf(ILP_CONF) as sender:
            for row in rows:
                symbols = {k: v for k, v in row.items() if k in symbol_columns}
                columns = {k: v for k, v in row.items() if k not in symbol_columns and k != timestamp_col}
                
                if timestamp_col not in row:
                    print(f"Error: Timestamp column '{timestamp_col}' not found in row: {row}")
                    continue

                # 2. Convert the integer to a TimestampNanos object, multiplying by 1000
                #    to convert from microseconds to nanoseconds.
                #timestamp_nanos = TimestampNanos(row[timestamp_col] * 1000) # adjust for nanos or datetime accordingly.
                timestamp_nanos = pd.to_datetime(row[timestamp_col], unit='ns')
                sender.row(
                    table_name,
                    symbols=symbols,
                    columns=columns,
                    at=timestamp_nanos)  
            
            sender.flush()
        print(f"Successfully inserted {len(rows)} rows into '{table_name}'.")
        return True
    except IngressError as e:
        print(f"QuestDB Ingress Error: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during insert: {e}")
        return False

def insert_dataframe(table_name: str, df: pd.DataFrame, symbol_columns: list = None, timestamp_col: str = 'ts'):
    """
    (C)REATE: Inserts data from a Pandas DataFrame into QuestDB.

    Args:
        table_name (str): The name of the target table.
        df (pd.DataFrame): The DataFrame containing the data to insert.
        symbol_columns (list, optional): A list of column names to be treated as SYMBOLs.
        timestamp_col (str, optional): The column name for the designated timestamp.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    if df.empty:
        print("Warning: DataFrame is empty, nothing to insert.")
        return True
    
    symbol_columns = symbol_columns or []
    
    try:
        with Sender.from_conf(ILP_CONF) as sender:
            # The `dataframe` method handles the conversion and insertion efficiently.
            df[timestamp_col] = pd.to_datetime(df[timestamp_col], unit='ns')
            sender.dataframe(
                df,
                table_name=table_name,
                symbols=symbol_columns,
                at=timestamp_col)
        print(f"Successfully inserted DataFrame with {len(df)} rows into '{table_name}'.")
        return True
    except IngressError as e:
        print(f"QuestDB Ingress Error: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during DataFrame insert: {e}")
        return False

def execute_query(sql_query: str):
    """(R)EAD, (U)PDATE, (D)ELETE: Executes any SQL query via the REST API."""
    try:
        response = requests.get(f"{HTTP_URL}/exec", params={'query': sql_query})
        response_json = response.json()

        if 'error' in response_json:
            print(f"QuestDB returned an error: {response_json['error']}")
            # return None
            return {"Error": response_json['error']}
        
        response.raise_for_status()
        return response_json
    
    except requests.exceptions.RequestException as e:
        print(f"Error executing query: {e}")
        # return None
        return {"Error":str(e)}

def read_questdb_dataframe(query):
    result = execute_query(sql_query = query)

    if result is None or 'Error' in result:
        return pd.DataFrame({'error': [result.get('Error', 'Unknown error') if result else 'Query returned None']})

    columns_names = pd.DataFrame(result['columns'])['name'].tolist()

    return pd.DataFrame(result['dataset'], columns=columns_names)


if __name__ == '__main__':
    # Example usage:
    sql_query = "SELECT * FROM kite_instruments_list;"

    result = execute_query(sql_query)
    if result is not None:
        print("Query executed successfully:")
        print(result)