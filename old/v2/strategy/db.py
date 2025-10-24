# strategy/db.py

import psycopg2
import os
from strategy.core import Strategy

DB_URI = os.environ.get('QORE_DB_URI', 'postgresql://username:password@localhost:5432/qore')

def get_connection():
    return psycopg2.connect(DB_URI)

def fetch_strategies_for_date(target_date):
    """
    Returns a tuple:
    (list of frozen Strategy objects up to target_date, current Strategy object (if any))
    """
    conn = get_connection()
    cur = conn.cursor()
    # Fetch frozen strategies (status='frozen', timestamp <= date)
    cur.execute(
        """
        SELECT * FROM strategies
        WHERE status='frozen' AND DATE(timestamp) <= %s
        ORDER BY timestamp
        """,
        (target_date,)
    )
    frozen_rows = cur.fetchall()
    frozen = []
    for row in frozen_rows:
        strategy = Strategy.from_dict(dict(zip([desc[0] for desc in cur.description], row)))
        frozen.append(strategy)

    # Fetch current strategy (status='current', timestamp == date)
    cur.execute(
        """
        SELECT * FROM strategies
        WHERE status='current' AND DATE(timestamp) = %s
        LIMIT 1
        """,
        (target_date,)
    )
    row = cur.fetchone()
    current = Strategy.from_dict(dict(zip([desc[0] for desc in cur.description], row))) if row else None

    cur.close()
    conn.close()
    return frozen, current

def insert_strategy(strategy_obj):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO strategies (
            id, strategy_id, timestamp, freeze_timestamp, type, status,
            assets, note, research, tags, challenger_strategies
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            strategy_obj.id,
            strategy_obj.id,
            strategy_obj.timestamp,
            strategy_obj.freeze_timestamp,
            strategy_obj.type,
            strategy_obj.status,
            strategy_obj.assets,
            strategy_obj.note,
            strategy_obj.research,
            strategy_obj.tags,
            strategy_obj.challenger_strategies
        )
    )
    conn.commit()
    cur.close()
    conn.close()

def update_strategy(strategy_obj):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE strategies SET
            freeze_timestamp = %s,
            type = %s,
            status = %s,
            assets = %s,
            note = %s,
            research = %s,
            tags = %s,
            challenger_strategies = %s
        WHERE id = %s
        """,
        (
            strategy_obj.freeze_timestamp,
            strategy_obj.type,
            strategy_obj.status,
            strategy_obj.assets,
            strategy_obj.note,
            strategy_obj.research,
            strategy_obj.tags,
            strategy_obj.challenger_strategies,
            strategy_obj.id
        )
    )
    conn.commit()
    cur.close()
    conn.close()
