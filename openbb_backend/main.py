# Import required libraries
# import json
# from pathlib import Path
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse

from curses import raw
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
from typing import Optional
import pandas as pd
from datetime import datetime, timedelta
from contextlib import asynccontextmanager


# Import your calculator
from data import HoldingsTimelineCalculator  # Adjust import path

# Importing Databases
from databases import quest_db, sqlite_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    global _equities_cache
    df = quest_db.read_questdb_dataframe("""
        SELECT UNDERLYING_SYMBOL as symbol, SYMBOL_NAME as name, 'all' as sector, EXCH_ID as exchange
        FROM dhan_full_instruments_list
        WHERE EXCH_ID = 'NSE' AND SEGMENT = 'E'
    """)
    _equities_cache = df[['symbol', 'name', 'sector', 'exchange']].to_dict('records')
    print(f"Loaded {len(_equities_cache)} equities into cache")
    yield

# Initialize FastAPI application with metadata
app = FastAPI(
    title="Hello World",
    description="Hello World app for OpenBB Workspace",
    version="0.0.1",
    lifespan=lifespan
)

# Define allowed origins for CORS (Cross-Origin Resource Sharing)
# This restricts which domains can access the API
origins = [
    "https://pro.openbb.co",
]

# Configure CORS middleware to handle cross-origin requests
# This allows the specified origins to make requests to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # allow_origins = ["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# @app.get("/")
# def read_root():
#     """Root endpoint that returns basic information about the API"""
#     return {"Info": "Hello World example"}


# Widgets configuration file for the OpenBB Workspace
# it contains the information and configuration about all the
# widgets that will be displayed in the OpenBB Workspace
# @app.get("/widgets.json")
# def get_widgets():
#     """Widgets configuration file for the OpenBB Workspace
    
#     Returns:
#         JSONResponse: The contents of widgets.json file
#     """
#     # Read and return the widgets configuration file
#     return JSONResponse(
#         content=json.load((Path(__file__).parent.resolve() / "widgets.json").open())
#     )


# Apps configuration file for the OpenBB Workspace
# it contains the information and configuration about all the
# apps that will be displayed in the OpenBB Workspace
@app.get("/apps.json")
def get_apps():
    """Apps configuration file for the OpenBB Workspace
    
    Returns:
        JSONResponse: The contents of apps.json file
    """
    # Read and return the apps configuration file
    return JSONResponse(
        content=json.load((Path(__file__).parent.resolve() / "apps.json").open())
    )


# Hello World endpoint - for it to be recognized by the OpenBB Workspace
# it needs to be added to the widgets.json file endpoint
@app.get("/hello_world")
def hello_world(name: str = ""):
    """Returns a personalized greeting message.

    Args:
        name (str, optional): Name to include in the greeting. Defaults to empty string.

    Returns:
        str: A greeting message with the provided name in markdown format.
    """
    # Return a markdown-formatted greeting with the provided name
    return f"# Hello World {name}"


# ============================================================================
# DATA LOADING (adjust to your data source)
# ============================================================================

def load_trades_data():
    """Load trades data from your database/source"""
    # Replace with your actual data loading logic
    # Example: df = pd.read_sql("SELECT * FROM trades", conn)
    # For now, assuming you have this function
    # from your_data_module import get_trades_dataframe

    trades_df = sqlite_db.get_data("select * from users_auth_trades")
    trades_df['instrument_token'] = pd.to_numeric(trades_df['instrument_token'], errors='coerce')
    qdb_df = quest_db.read_questdb_dataframe(query= "select * from kite_instruments_list")

    merged = trades_df.merge(qdb_df[['instrument_token', 'exchange_token']], 
                left_on='instrument_token',
                right_on='instrument_token',
                how='left')


    merged['tag'] = merged.apply(lambda x: 'etf' if x['tradingsymbol'] in ['GOLDBEES', 'GOLDBEES-E', 'JUNIORBEES', 'LIQUIDCASE', 'NIFTYBEES'] else None, 
                                    axis = 1)
    

    return merged

def get_portfolio_timeline():
    """Get calculated portfolio timeline"""
    trades_df = load_trades_data()
    calculator = HoldingsTimelineCalculator(trades_df)
    portfolio = calculator.calculate_timeline(
        account_id='AGL883',
        granularity='daily'
    )
    return portfolio

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_portfolio_data(portfolio):
    """Extract full portfolio data for charting"""
    dates = []
    invested = []
    market = []
    
    for entry in portfolio['timeline']:
        dates.append(entry['date'])
        invested.append(entry['summary']['total_invested_value'])
        market.append(entry['summary']['total_market_value'])
    
    return dates, invested, market

def extract_bucket_data(portfolio, bucket_name):
    """Extract bucket-specific data, starting from bucket inception"""
    bucket_data = []
    
    for entry in portfolio['timeline']:
        if bucket_name in entry['buckets']:
            bucket_data.append({
                'date': entry['date'],
                'invested': entry['buckets'][bucket_name]['invested_value'],
                'market': entry['buckets'][bucket_name]['market_value']
            })
    
    if not bucket_data:
        return [], [], []
    
    dates = [d['date'] for d in bucket_data]
    invested = [d['invested'] for d in bucket_data]
    market = [d['market'] for d in bucket_data]
    
    return dates, invested, market

def create_performance_chart(dates, invested, market, title):
    """Create Plotly chart for portfolio/bucket performance"""
    fig = go.Figure()
    
    # Trace 1: Invested Value (cream/off-white)
    fig.add_trace(go.Scatter(
        x=dates,
        y=invested,
        mode='lines',
        name='Invested Value',
        line=dict(width=2, color='#F5F5DC'),
        hovertemplate='<b>Invested</b><br>₹%{y:,.2f}<extra></extra>'
    ))
    
    # Trace 2: Market Value (blue)
    fig.add_trace(go.Scatter(
        x=dates,
        y=market,
        mode='lines',
        name='Market Value',
        line=dict(width=2, color='#2E5090'),
        hovertemplate='<b>Market</b><br>₹%{y:,.2f}<extra></extra>'
    ))
    
    # Layout configuration
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Value (₹)',
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        yaxis=dict(
            tickformat=',.0f',  # Format with commas, no decimals
            tickprefix='₹'
        )
    )
    
    return fig

def fetch_ohlc_data(symbol, exchange='NSE', interval='1d', start='1975-01-01', end='2025-12-31', segment='E'):
        daily_price_sql1 = f"""
                    SELECT SECURITY_ID, UNDERLYING_SYMBOL, SYMBOL_NAME, EXCH_ID
                    FROM dhan_full_instruments_list
                    WHERE EXCH_ID = '{exchange}' AND UNDERLYING_SYMBOL = '{symbol}'  AND SEGMENT = '{segment}';
                    """
        security_id = quest_db.execute_query(sql_query = daily_price_sql1)['dataset'][0][0]
        print(f"security_id: {security_id}")
        daily_price_sql2 = f"""
                    SELECT timestamp as date, open, high, low, close, volume, '{symbol}' AS symbol, '{exchange}' AS exchange
                    FROM daily_historical_prices 
                    WHERE security_id = {security_id} AND timestamp >= '{start}' AND timestamp <= '{end}'; 
                    """ 

        return quest_db.read_questdb_dataframe(query= daily_price_sql2)

def resolve_dates(range: str, start_date=None, end_date=None):
    today = pd.Timestamp.today().normalize()

    range = range.upper()

    if range == "1M":
        return today - pd.DateOffset(months=1), today
    if range == "3M":
        return today - pd.DateOffset(months=3), today
    if range == "6M":
        return today - pd.DateOffset(months=6), today
    if range == "YTD":
        return pd.Timestamp(today.year, 1, 1), today
    if range == "1Y":
        return today - pd.DateOffset(years=1), today
    if range == "3Y":
        return today - pd.DateOffset(years=3), today
    if range == "5Y":
        return today - pd.DateOffset(years=5), today
    if range == "LTD":
        return pd.Timestamp("2000-01-01"), today

    raise ValueError(f"Invalid range: {range}")

def ohlc_resample(df: pd.DataFrame):
    span_days = (df['date'].max() - df['date'].min()).days

    if span_days <= 400:
        return df

    if span_days <= 2500:
        rule = "W"

    else:
        rule = "M"

    ohlc = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }

    return df.set_index("date").resample(rule).agg(ohlc).dropna().reset_index()


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
def read_root():
    """Root endpoint"""
    return {"Info": "Portfolio Analytics API for OpenBB Workspace"}

@app.get("/widgets.json")
def get_widgets():
    """Widgets configuration"""
    return JSONResponse(
        content=json.load((Path(__file__).parent.resolve() / "widgets.json").open())
    )




# @app.get("/portfolio_timeline")
# def portfolio_timeline():
#     """
#     Full portfolio performance: Invested vs Market Value over time.
#     No parameters - fixed to account AGL883.
#     """
#     try:
#         print("starting portfolio timeline fetch")
#         # Get portfolio data
#         portfolio = get_portfolio_timeline()
#         # print(portfolio)
#         # Extract data
#         dates, invested, market = extract_portfolio_data(portfolio)
        
#         if not dates:
#             raise HTTPException(status_code=404, detail="No portfolio data found")
        
#         # Create chart
#         fig = create_performance_chart(
#             dates, invested, market,
#             title="Portfolio Performance"
#         )
        
#         # Return Plotly JSON
#         return json.loads(fig.to_json())
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.get("/bucket_timeline")
# def bucket_timeline(bucket: str):
#     """
#     Bucket-specific performance: Invested vs Market Value over time.
    
#     Args:
#         bucket: Bucket name (e.g., 'etf', 'untagged', 'smallcap')
#     """
#     try:
#         # Get portfolio data
#         portfolio = get_portfolio_timeline()
        
#         # Extract bucket data
#         dates, invested, market = extract_bucket_data(portfolio, bucket)
        
#         if not dates:
#             # Bucket exists but has no data
#             fig = go.Figure()
#             fig.add_annotation(
#                 text=f"No holdings in '{bucket}' bucket",
#                 xref="paper", yref="paper",
#                 x=0.5, y=0.5,
#                 showarrow=False,
#                 font=dict(size=16, color="gray")
#             )
#             return json.loads(fig.to_json())
        
#         # Create chart
#         fig = create_performance_chart(
#             dates, invested, market,
#             title=f"Bucket Performance: {bucket}"
#         )
        
#         # Return Plotly JSON
#         return json.loads(fig.to_json())
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.get("/portfolio_timeline")
def portfolio_timeline():
    """
    Full portfolio performance: Invested vs Market Value over time.
    Returns raw data for OpenBB to chart.
    """
    try:
        print("Starting portfolio timeline fetch")
        
        # Get portfolio data
        portfolio = get_portfolio_timeline()
        
        # Convert to list of dictionaries
        data = []
        for entry in portfolio['timeline']:
            data.append({
                'date': entry['date'],
                'invested_value': entry['summary']['total_invested_value'],
                'market_value': entry['summary']['total_market_value'],
                'unrealized_pnl': entry['summary']['total_unrealized_pnl'],
                'unique_symbols': entry['summary']['unique_symbols']
            })
        
        print(f"Returning {len(data)} days of portfolio data")
        return data
    
    except Exception as e:
        print(f"Error in portfolio_timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bucket_timeline")
def bucket_timeline(bucket: str):
    """
    Bucket-specific performance: Invested vs Market Value over time.
    Returns raw data for OpenBB to chart.
    """
    try:
        print(f"Fetching bucket timeline for: {bucket}")
        
        # Get portfolio data
        portfolio = get_portfolio_timeline()
        
        # Extract bucket-specific data
        data = []
        for entry in portfolio['timeline']:
            if bucket in entry['buckets']:
                data.append({
                    'date': entry['date'],
                    'invested_value': entry['buckets'][bucket]['invested_value'],
                    'market_value': entry['buckets'][bucket]['market_value'],
                    # 'unrealized_pnl': entry['buckets'][bucket]['unrealized_pnl'],
                    'unique_symbols': entry['buckets'][bucket]['unique_symbols']
                })
        
        if not data:
            # Return empty dataset
            return []
        
        print(f"Returning {len(data)} days of bucket data for '{bucket}'")
        return data
    
    except Exception as e:
        print(f"Error in bucket_timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/available_buckets")
def available_buckets():
    """
    Get list of available investment buckets for dropdown.
    Dynamically discovered from portfolio data.
    """
    try:
        # Get portfolio data
        portfolio = get_portfolio_timeline()
        
        # Collect all unique bucket names
        bucket_names = set()
        for entry in portfolio['timeline']:
            bucket_names.update(entry['buckets'].keys())
        
        # Format for OpenBB dropdown
        options = [
            {"label": bucket, "value": bucket}
            for bucket in sorted(bucket_names)
        ]
        
        return options
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/stock/chart")
def get_stock_chart(
    symbol: str = Query("RELIANCE", description="Stock symbol"),
    # start_date: str = Query('2025-01-01', description="Start date (YYYY-MM-DD)"),
    # end_date: str = Query('2025-12-31', description="End date (YYYY-MM-DD)"),
    time_period: str = Query("1Y", description="Time period (e.g., 1M, 3M, 6M, YTD, 1Y, 3Y, 5Y, LTD)"),
    raw: bool = Query(False, description="Return raw data instead of chart"),
    theme: str = "dark"
):
    
    start_date, end_date = resolve_dates(time_period)
    df = fetch_ohlc_data(symbol, start=start_date, end=end_date)
    df['date'] = pd.to_datetime(df['date'], utc=False)
    df = ohlc_resample(df)
    
    if raw:
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        return df[['date', 'close', 'volume']].to_dict(orient='records')

    price_min = df['close'].min()
    price_max = df['close'].max()
    pad = (price_max - price_min) * 0.05

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.75, 0.25],
        subplot_titles=(f'{symbol} Price', 'Volume')
    )

    # -------- Price Line --------
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['close'],
        mode='lines',
        name='Close',
        line=dict(color='#1A73E8', width=2),
        fill='tozeroy',
        fillcolor='rgba(26,115,232,0.12)'
    ), row=1, col=1)

    # -------- Volume Bars --------
    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['volume'],
        name='Volume',
        marker=dict(
            color='rgba(26,115,232,0.35)',
            line=dict(width=0)
        )
    ), row=2, col=1)

    # -------- Layout (Dark Mode) --------
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',

        hovermode='x unified',
        dragmode='select',
        selectdirection="h",

        # newselection=dict(
        #     line=dict(color='#1A73E8', width=1),
        #     fillcolor='rgba(26,115,232,0.12)'
        # ),
        activeselection=dict(
            fillcolor='rgba(115,155,22,0.18)'
        ),

        margin=dict(l=60, r=30, t=40, b=40),
        showlegend=False,

        title=dict(
            text=f'{symbol} Stock Price & Volume',
            x=0.01,
            font=dict(size=16, color='#E8EAED')
        )
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor='rgba(255,255,255,0.05)',
        zeroline=False
    )

    fig.update_yaxes(
        range=[price_min - pad, price_max + pad],
        showgrid=True,
        gridcolor='rgba(255,255,255,0.05)',
        zeroline=False,
        row=1, col=1
    )

    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        row=2, col=1
    )

    return json.loads(fig.to_json())


@app.get("/stocks/financial_reports")
def get_financial_reports(
    symbol: str = Query("RELIANCE"),
    statement: str = Query("pnl")  # "pnl" | "cash_flow" | "balance_sheet"
):
    query_map = {
        "pnl":           f"SELECT timestamp, items FROM pnl WHERE symbol = '{symbol}' ORDER BY timestamp",
        "cash_flow":     f"SELECT timestamp, items FROM cf WHERE symbol = '{symbol}' ORDER BY timestamp",
        "balance_sheet": f"SELECT timestamp, items FROM bs WHERE symbol = '{symbol}' ORDER BY timestamp",
    }

    query = query_map.get(statement, query_map["pnl"])
    df = quest_db.read_questdb_dataframe(query)

    if df.empty:
        return []

    df = df.copy()
    df["year"] = pd.to_datetime(df["timestamp"]).dt.year
    df["items"] = df["items"].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
    expanded = pd.json_normalize(df["items"].tolist())
    expanded.insert(0, "year", df["year"].values)
    expanded["year"] = df["year"].astype(str)
    expanded = expanded.replace({float('nan'): None})  # convert NaN to null
    return expanded.to_dict("records")

# @app.get("stock/holding")
# def get_holding(symbol: str):
#     # Replace with your real data logic
#     data = get_portfolio_data(symbol.upper())  # your function

#     markdown = f"""
#         ## {data['symbol']} — Portfolio Holding

#         | Metric | Value |
#         |---|---|
#         | **Ticker** | {data['symbol']} |
#         | **Shares Held** | {data['quantity']:,} |
#         | **Avg. Buy Price** | ${data['avg_price']:.2f} |
#         | **Total Invested** | ${data['total_invested']:,.2f} |
#         | **Current Price** | ${data['current_price']:.2f} |
#         | **Current Value** | ${data['current_value']:,.2f} |
#         | **Unrealized P&L** | ${data['unrealized_pnl']:,.2f} ({data['pnl_pct']:.2f}%) |
#         | **% of Portfolio** | {data['portfolio_weight']:.2f}% |
#         | **First Purchased** | {data['first_purchase_date']} |
#         | **Last Updated** | {data['last_updated']} |
#     """

#     return JSONResponse(content={"content": markdown})
    

@app.get("/stock/candlestick")
def get_candlestick(
    symbol: str,
    exchange: str = "NSE",
    interval: str = "1d",
    period: str = "ytd",
    start_date: str = None,
    end_date: str = None,
    raw: bool = False,
    theme: str = "dark"
):
    # 1. Calculate date range based on period
    end = datetime.now()
    
    period_mapping = {
        # "wtd": timedelta(days=7),
        "mtd": timedelta(days=30),
        "ytd": None,  # Calculate to year start
        "r12m": timedelta(days=365),
        "r3y": timedelta(days=365*3),
        "r5y": timedelta(days=365*5),
        "ltd": None,  # All available data
        "custom": None  # Use start_date/end_date
    }
    
    if period == "ytd":
        start = datetime(end.year, 1, 1)
    elif period == "custom":
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    elif period == "ltd":
        start = '1975-01-01'  # Get all data
    else:
        start = end - period_mapping[period]
    
    # 2. Fetch data from your data source
    # df = fetch_ohlc_data(symbol, exchange, interval, start, end)

    df = fetch_ohlc_data(symbol, exchange, start=start, end=end)
    df['date'] = pd.to_datetime(df['date']).dt.date
    
    # 3. If raw mode, return data as list of dicts
    if raw:
        return df.to_dict(orient="records")
    
    # 4. Create Plotly candlestick chart
    colors = {
        "dark": {
            "bg": "#151518",
            "text": "#FFFFFF",
            "grid": "rgba(51, 51, 51, 0.3)",
            "increasing": "#26a69a",
            "decreasing": "#ef5350"
        },
        "light": {
            "bg": "#FFFFFF",
            "text": "#333333",
            "grid": "rgba(221, 221, 221, 0.3)",
            "increasing": "#26a69a",
            "decreasing": "#ef5350"
        }
    }[theme]
    
    fig = go.Figure(data=[
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            increasing_line_color=colors["increasing"],
            decreasing_line_color=colors["decreasing"],
            increasing_fillcolor=colors["increasing"],
            decreasing_fillcolor=colors["decreasing"],
            name=f"{symbol}.{exchange}"
        )
    ])
    
    fig.update_layout(
        title={
            'text': f"{symbol} ({exchange}) - Candlestick Chart",
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        xaxis_rangeslider_visible=True,
        paper_bgcolor=colors["bg"],
        plot_bgcolor=colors["bg"],
        font=dict(color=colors["text"]),
        xaxis=dict(gridcolor=colors["grid"]),
        yaxis=dict(gridcolor=colors["grid"]),
        hovermode='x unified',
        dragmode='zoom'
    )
    
    # 5. Configure toolbar
    config = {
        'displayModeBar': True,
        'scrollZoom': True,
        'responsive': True,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
        'displaylogo': False
    }
    
    figure_json = json.loads(fig.to_json())
    figure_json['config'] = config
    
    return figure_json

# @app.get("/stock/search")
# def search_stocks(
#     query: str = Query("", min_length=0),
#     exchange: str = Query(None),
#     limit: int = Query(20, ge=1, le=50000)
# ):
#     """
#     Search for stock symbols and company names.
    
#     Returns matching stocks from NSE/BSE based on the search query.
#     """
#     # Example: Search in your database or call external API
#     # This is a mock implementation
#     def fetch_equities_list(exchange='NSE', segment='E'):
#         daily_price_sql1 = f"""
#                     SELECT UNDERLYING_SYMBOL as symbol, SYMBOL_NAME as name, 'all' as sector, EXCH_ID as exchange
#                     FROM dhan_full_instruments_list
#                     WHERE EXCH_ID = '{exchange}' AND SEGMENT = '{segment}';
#                     """
#         # security_id = quest_db.execute_query(sql_query = daily_price_sql1)['dataset'][0][0]
#         # print(f"security_id: {security_id}")
#         # daily_price_sql2 = f"""
#         #             SELECT timestamp as date, open, high, low, close, volume, '{symbol}' AS symbol, '{exchange}' AS exchange
#         #             FROM daily_historical_prices 
#         #             WHERE security_id = {security_id} AND timestamp >= '{start}' AND timestamp <= '{end}'; 
#         #             """ 

#         return quest_db.read_questdb_dataframe(query= daily_price_sql1)

#     df = fetch_equities_list(exchange if exchange else 'NSE', segment='E')

#     stocks_db = df[['symbol', 'name', 'sector', 'exchange']].to_dict('records')
    
#     # Filter by query
#     query_lower = query.lower()
#     filtered_stocks = [
#         s for s in stocks_db
#         if not query_lower
#         or query_lower in s["symbol"].lower()
#         or query_lower in s["name"].lower()
#     ]
    
#     # Filter by exchange if provided
#     if exchange:
#         filtered_stocks = [
#             stock for stock in filtered_stocks
#             if stock["exchange"] == exchange.upper()
#         ]
    
#     # Limit results
#     filtered_stocks = filtered_stocks[:limit]
    
#     # Format response
#     results = [
#         {
#             "label": f"{stock['symbol']} - {stock['name']}",
#             "value": stock['symbol'],
#             "extraInfo": {
#                 "description": stock['sector'],
#                 "rightOfDescription": stock['exchange']
#             }
#         }
#         for stock in filtered_stocks
#     ]
    
#     return results




@app.get("/stock/search")
def search_stocks(query: str = Query("", min_length=0), exchange: str = Query(None)):
    query_lower = query.lower()
    filtered = [
        s for s in _equities_cache
        if not query_lower
        or query_lower in s["symbol"].lower()
        or query_lower in s["name"].lower()
    ]
    if exchange:
        filtered = [s for s in filtered if s["exchange"] == exchange.upper()]
    return [
        {
            "label": f"{s['symbol']} - {s['name']}",
            "value": s['symbol'],
            "extraInfo": { "description": s['sector'], "rightOfDescription": s['exchange'] }
        }
        for s in filtered  # no limit — return all so client-side search works
    ]