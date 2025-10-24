# past/db.py

import psycopg2
import os
from strategy.core import Strategy

# Database connection string can be set via environment variable for security.
DB_URI = os.environ.get('QORE_DB_URI', 'postgresql://username:password@localhost:5432/qore')

def get_connection():
    """
    Open a connection to the PostgreSQL database.
    Returns:
        psycopg2 connection object
    """
    return psycopg2.connect(DB_URI)

def fetch_all_frozen_strategies():
    """
    Retrieve all frozen strategies (status='frozen'), ordered by timestamp.
    Returns:
        List of Strategy objects (frozen only)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM strategies
        WHERE status = 'frozen'
        ORDER BY timestamp
        """
    )
    rows = cur.fetchall()
    frozen_strategies = []
    columns = [desc[0] for desc in cur.description]
    for row in rows:
        data = dict(zip(columns, row))
        frozen_strategies.append(Strategy.from_dict(data))
    cur.close()
    conn.close()
    return frozen_strategies

def fetch_frozen_strategies_for_dates(start_date, end_date):
    """
    Fetch frozen strategies between two dates (inclusive).
    Args:
        start_date, end_date: ISO-format date strings or datetime objects
    Returns:
        List of Strategy objects
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM strategies
        WHERE status = 'frozen'
          AND DATE(timestamp) BETWEEN %s AND %s
        ORDER BY timestamp
        """,
        (start_date, end_date)
    )
    rows = cur.fetchall()
    frozen_strategies = []
    columns = [desc[0] for desc in cur.description]
    for row in rows:
        data = dict(zip(columns, row))
        frozen_strategies.append(Strategy.from_dict(data))
    cur.close()
    conn.close()
    return frozen_strategies
