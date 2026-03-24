import os, sys
import django
from django.conf import settings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qore.settings")

django.setup()

from users_auth.models import UserProfile, Trades
from django.contrib.auth.models import User
from django.conf import settings
from django.db import IntegrityError
import pytz

from kiteconnect import KiteConnect
import pyotp
import requests
from urllib.parse import urlparse, parse_qs
import time
import pandas as pd

# Symbol
# Exchange
# Trade Type
# Quantity
# Price
# Trade ID
# Order ID
TIMEZONE = pytz.timezone('Asia/Kolkata')
trades_backfill = pd.read_excel("trades_compiled.xlsx")
trades_backfill['Order Execution Time'] = pd.to_datetime(trades_backfill['Order Execution Time'], errors='coerce')

all_profiles = UserProfile.objects.select_related('user').all()
for profile in all_profiles:

    kiteusername = profile.kite_username
    kitepwd = profile.kite_pwd
    totpsecret = profile.totp_key
    kiteapikey = profile.kite_api_key
    kiteapisecret = profile.kite_api_secret
    kiteaccesstoken = profile.access_token


    kite = KiteConnect(api_key=kiteapikey)
    kite.set_access_token(kiteaccesstoken)
    print(str(profile.user))
    if str(profile.user) != 'pratik':
        print('quitting')
        continue

    trades_to_backfill = []
    for idx, row in trades_backfill.iterrows():

        def make_timezone_aware(dt_obj):
            if dt_obj is None:
                return None
            # Check if it's a naive datetime object (tzinfo is None)
            if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
                return TIMEZONE.localize(dt_obj)
            return dt_obj # Already timezone-aware
            
        fill_ts = make_timezone_aware(row['Order Execution Time'])

        trade_instance = Trades(
                user=profile.user,
                trade_id=str(row['Trade ID']),
                
                # Core Transaction Details
                order_id=str(row['Order ID']),
                exchange_order_id='N/A_backfill',
                account_id='AGL883', 
                
                # Instrument Details
                tradingsymbol=row['Symbol'],
                instrument_token='UNKNOWN_TOKEN',
                exchange=row['Exchange'],
                product='CNC',
                
                # Financial Details
                quantity=int(row['Quantity']),
                average_price=row['Price'],
                transaction_type=row['Trade Type'],
                
                # Timestamps (now properly localized/timezone-aware)
                fill_timestamp=fill_ts,
                order_timestamp=None,
                exchange_timestamp=None,
                
                # Meta
                tag= None,
            )
        trades_to_backfill.append(trade_instance)
    
    if trades_to_backfill:
        created_trades = Trades.objects.bulk_create(
            trades_to_backfill, 
            ignore_conflicts=True
        )
        print(f"Successfully saved {len(created_trades)} backfill trades for {profile.user.username}.")
    else:
        print(f"No backfill trades to save for {profile.user.username}.")