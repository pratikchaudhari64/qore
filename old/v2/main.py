# main.py
from flask import Flask, jsonify, request
from datetime import datetime
import pytz

# Import your main modules -- these would be implemented as detailed in your project tree.
from data.fetcher import fetch_dashboard_data
from strategy.core import fetch_strategies_for_date
from past.analytics import PastStrategies

app = Flask(__name__)

def get_today_ist():
    now_utc = datetime.utcnow()
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = now_utc.replace(tzinfo=pytz.utc).astimezone(ist)
    return now_ist.date().isoformat()

@app.route('/dashboard')
def dashboard():
    today = get_today_ist()

    # Retrieve frozen and current strategies for today (list of objects)
    frozen_strategies, current_strategy = fetch_strategies_for_date(today)
    strategy_objects = frozen_strategies + ([current_strategy] if current_strategy else [])

    # Fetch asset/stock data needed for these strategies
    stock_data = fetch_dashboard_data(strategy_objects)

    # Use past strategies module for analytics/visuals
    past = PastStrategies()
    for strat in frozen_strategies:
        past.add_frozen_strategy(strat)

    graphs = past.generate_graphs(stock_data=stock_data)
    metrics = past.calculate_metrics(stock_data=stock_data)

    response = {
        "date": today,
        "frozen_strategy_count": len(frozen_strategies),
        "current_strategy": current_strategy.to_dict() if current_strategy else None,
        "graphs": graphs,
        "metrics": metrics,
        "stock_data": stock_data
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
