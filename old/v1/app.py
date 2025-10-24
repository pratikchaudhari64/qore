import os
from dotenv import load_dotenv
import logging
import threading
from datetime import date, datetime
from decimal import Decimal
from utils import rupee_format, indian_comma_format
import time

from flask import Flask, request, jsonify, session, render_template, Response, stream_with_context
from kiteconnect import KiteConnect
from jinja2 import Environment, FileSystemLoader
from engine.ollama import OllamaEngine

# Set up basic logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
env = Environment(loader=FileSystemLoader("templates"))

# Base settings
PORT = 8000
HOST = "127.0.0.1"
CHAT_MODEL = "llama3.2:3b"
# CHAT_MODEL = "gemma3:12b-it-qat"

# def serializer(obj): return isinstance(obj, (date, datetime, Decimal)) and str(obj)  # noqa

# Access variables
KITE_API_KEY = os.getenv("API_KEY")
KITE_API_SECRET = os.getenv("API_SECRET")

# Create a redirect url
redirect_url = "http://{host}:{port}/login".format(host=HOST, port=PORT)
# Login url
login_url = "https://kite.zerodha.com/connect/login?api_key={api_key}".format(api_key=KITE_API_KEY)
# Kite connect console url
console_url = "https://developers.kite.trade/apps/{api_key}".format(api_key=KITE_API_KEY)

# App
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.jinja_env.filters['rupee_format'] = rupee_format
app.jinja_env.filters['indian_comma_format'] = indian_comma_format

# Ollama engine definition
ai_agent = OllamaEngine(model_name=CHAT_MODEL)


# index_template = """
#     <div>Make sure your app with api_key - <b>{api_key}</b> has set redirect to <b>{redirect_url}</b>.</div>
#     <div>If not you can set it from your <a href="{console_url}">Kite Connect developer console here</a>.</div>
#     <a href="{login_url}"><h1>Login to generate access token.</h1></a>"""

login_template = """
    <h2 style="color: green">Success</h2>
    <div>Access token: <b>{access_token}</b></div>
    <h4>User login data</h4>
    <pre>{user_data}</pre>
    <a target="_blank" href="/holdings.json"><h4>Fetch user holdings</h4></a>
    <a target="_blank" href="/orders.json"><h4>Fetch user orders</h4></a>
    <a target="_blank" href="/mf_holdings.json"><h4>Fetch user mutual fund holdings</h4></a>
    <a target="_blank" href="https://kite.trade/docs/connect/v1/"><h4>Checks Kite Connect docs for other calls.</h4></a>
        <a href="/logout"><h4 style="color: red">Logout</h4></a>
    """

def get_kite_client():
    """Returns a kite client object
    """
    kite = KiteConnect(api_key=KITE_API_KEY)
    if "access_token" in session:
        kite.set_access_token(session["access_token"])
    return kite

@app.route("/")
def index():
    return render_template("index.html", login_url=login_url)

@app.route("/login")
def login():

    if "access_token" in session:
        kite = get_kite_client()
        profile = kite.profile()
        holdings = kite.holdings()
        mf_holdings = kite.mf_holdings()
        metrics = calculate_metrics(holdings)
        metrics_mf = calculate_metrics_mf(mf_holdings)
        return render_template('console_home.html', holdings=holdings, metrics_mf=metrics_mf, metrics=metrics, user_shortname=profile["user_shortname"])
    
    request_token = request.args.get("request_token")
    if not request_token:
        return """
            <span style="color: red">
                Error while generating request token.
            </span>
            <a href='/'>Try again.<a>"""
    kite = get_kite_client()
    try:
        data = kite.generate_session(request_token, api_secret=KITE_API_SECRET)
        session["access_token"] = data["access_token"]
    except Exception as e:
        return f"<span style='color: red'>Login failed: {str(e)}</span><a href='/'>Try again</a>"

    profile = kite.profile()
    holdings = kite.holdings()
    mf_holdings = kite.mf_holdings()
    metrics = calculate_metrics(holdings)
    metrics_mf = calculate_metrics_mf(mf_holdings)
    # Render the equity.html template with holdings and metrics
    return render_template('console_home.html', holdings=holdings, metrics_mf=metrics_mf, metrics=metrics, user_shortname=profile["user_shortname"])

@app.route("/equity")
def equity():
    if "access_token" in session:
        kite = get_kite_client()
        profile = kite.profile()
        holdings = kite.holdings()
        metrics = calculate_metrics(holdings)
        return render_template('equity_holdings.html', holdings=holdings, metrics=metrics, user_shortname=profile["user_shortname"])
    
    request_token = request.args.get("request_token")
    if not request_token:
        return """
            <span style="color: red">
                Error while generating request token.
            </span>
            <a href='/'>Try again.<a>"""
    kite = get_kite_client()
    try:
        data = kite.generate_session(request_token, api_secret=KITE_API_SECRET)
        session["access_token"] = data["access_token"]
    except Exception as e:
        return f"<span style='color: red'>Login failed: {str(e)}</span><a href='/'>Try again</a>"

    profile = kite.profile()
    holdings = kite.holdings()
    mf_holdings = kite.mf_holdings()
    metrics = calculate_metrics(holdings)
    metrics_mf = calculate_metrics_mf(mf_holdings)
    # Render the equity.html template with holdings and metrics
    return render_template('equity_holdings.html', holdings=holdings, metrics=metrics, user_shortname=profile["user_shortname"])

@app.route("/mf")
def mf():
    if "access_token" in session:
        kite = get_kite_client()
        profile = kite.profile()
        mf_holdings = kite.mf_holdings()
        metrics_mf = calculate_metrics_mf(mf_holdings)
        return render_template('mf_holdings.html', mf_holdings=mf_holdings, metrics_mf=metrics_mf, user_shortname=profile["user_shortname"])
    
    request_token = request.args.get("request_token")
    if not request_token:
        return """
            <span style="color: red">
                Error while generating request token.
            </span>
            <a href='/'>Try again.<a>"""
    kite = get_kite_client()
    try:
        data = kite.generate_session(request_token, api_secret=KITE_API_SECRET)
        session["access_token"] = data["access_token"]
    except Exception as e:
        return f"<span style='color: red'>Login failed: {str(e)}</span><a href='/'>Try again</a>"

    profile = kite.profile()
    mf_holdings = kite.mf_holdings()
    metrics_mf = calculate_metrics_mf(mf_holdings)
    # Render the equity.html template with holdings and metrics
    return render_template('mf_holdings.html', mf_holdings=mf_holdings, metrics_mf=metrics_mf, user_shortname=profile["user_shortname"])

@app.route("/chat")
def chat():
    # if "access_token" in session:
    #     kite = get_kite_client()
    #     profile = kite.profile()

    # return render_template('chat_home.html', user_shortname=profile["user_shortname"], MODEL_NAME=CHAT_MODEL)
    return render_template('chat_home.html', user_shortname="Aditya", MODEL_NAME=CHAT_MODEL)


@app.route("/chat/stream", methods=["POST"])
def chat_stream():

    data = request.get_json()

    # Validate request
    if not data or "prompt" not in data:
        return Response("Invalid request: missing prompt.", status=400)
    
    prompt = request.json.get('prompt')

    def generate():
        for token in ai_agent.stream_ollama_response(prompt):
            # print("Streamed:", token, flush=True)  # <== Force flush for real-time logging
            yield token
    
    # def generate():
    #     for word in ["Hello", ",", " world", "!"]:
    #         time.sleep(0.2)
    #         yield word

    return Response(stream_with_context(generate()), mimetype='text/plain')

@app.route("/logout")
def logout():
    ai_agent.stop_ollama_model()
    session.clear()
    return render_template('logout.html')


def calculate_metrics(holdings):
    """
    Calculate key metrics from holdings data.
    Args:
        holdings (list): List of holdings from kite.holdings() or kite.mf_holdings()
    Returns:
        dict: Metrics like total_invested, current_value, returns, xirr, alpha, beta
    """
    if not holdings:
        return {
            'total_invested': 0.00,
            'current_value': 0.00,
            'returns': 0.00,
            'xirr': 0.00,
            'alpha': 0.00,
            'beta': 0.00
        }

    # Calculate total invested and current value
    total_invested = sum(holding['quantity'] * holding['average_price'] for holding in holdings)
    current_value = sum(holding['quantity'] * holding['last_price'] for holding in holdings)

    # Calculate returns as a percentage
    returns = ((current_value - total_invested) / total_invested) * 100 if total_invested > 0 else 0

    # Placeholder for XIRR, alpha, and beta
    # XIRR requires transaction dates and cash flows (not available in holdings data)
    xirr = 12.5  # Placeholder; use a library like 'xirr' with transaction data
    alpha = 2.3  # Placeholder; requires benchmark returns
    beta = 1.1   # Placeholder; requires covariance with market

    return {
        'total_invested': round(total_invested, 2),
        'current_value': round(current_value, 2),
        'returns': round(returns, 2),
        'xirr': round(xirr, 2),
        'alpha': round(alpha, 2),
        'beta': round(beta, 2)
    }

def calculate_metrics_mf(mf_holdings):
    """
    Calculate key metrics from mutual fund holdings data (kite.mf_holdings()).
    Args:
        mf_holdings (list): List of MF holdings from kite.mf_holdings()
    Returns:
        dict: Metrics like total_invested, current_value, returns, xirr, alpha, beta
    """
    if not mf_holdings:
        return {
            'total_invested': 0.00,
            'current_value': 0.00,
            'returns': 0.00,
            'xirr': 0.00,
            'alpha': 0.00,
            'beta': 0.00
        }

    # Calculate total invested and current value
    # Usually, average_price is the purchase NAV, last_price is current NAV
    total_invested = 0
    current_value = 0

    for holding in mf_holdings:
        quantity = holding.get('quantity', 0)
        average_price = holding.get('average_price') or holding.get('purchase_nav') or 0
        last_price = holding.get('last_price') or holding.get('nav') or 0

        total_invested += quantity * average_price
        current_value += quantity * last_price

    # Calculate returns as a percentage
    returns = ((current_value - total_invested) / total_invested) * 100 if total_invested > 0 else 0

    # Placeholder for XIRR, alpha, and beta as these require transaction and benchmark data
    xirr = 12.5  # Placeholder
    alpha = 2.3  # Placeholder
    beta = 1.1   # Placeholder

    return {
        'total_invested': round(total_invested, 2),
        'current_value': round(current_value, 2),
        'returns': round(returns, 2),
        'xirr': round(xirr, 2),
        'alpha': round(alpha, 2),
        'beta': round(beta, 2)
    }


if __name__ == "__main__":
    threading.Thread(target=ai_agent.launch_model).start()
    logging.info("Starting server: http://{host}:{port}".format(host=HOST, port=PORT))
    app.run(host=HOST, port=PORT, debug=True)