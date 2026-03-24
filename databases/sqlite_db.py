import sqlite3
import pandas as pd


def get_data(query):
    try:
        with sqlite3.connect("../src_django/db.sqlite3") as conn:
            df = pd.read_sql_query(query, conn)
            # conn.close()
            return df
    except Exception as e:
        return e
    finally:
        conn.close()

def execute_query(query, params=None):
    """
    Executes an action query (INSERT, UPDATE, DELETE, ALTER, DROP).
    Returns the number of rows affected or the error.
    """
    conn = None
    try:
        # Using a context manager for the connection
        with sqlite3.connect("../src_django/db.sqlite3") as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # This is the crucial part for non-SELECT queries
            conn.commit()
            
            return f"Success: {cursor.rowcount} rows affected."
    except Exception as e:
        return f"Error: {e}"
    finally:
        if conn:
            conn.close()