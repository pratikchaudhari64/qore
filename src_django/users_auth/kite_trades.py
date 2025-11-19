import os, sys
import django
from django.conf import settings

if __name__ == '__main__':
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

TIMEZONE = pytz.timezone('Asia/Kolkata')
def fetch_trades():
    fetch_successes = []
    fetch_errors = []
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

        try:
            trades = kite.trades()
        except Exception as e:
            err_dict = {profile.user.username: "Error fetching trades"}
            fetch_errors.append(err_dict)
            print(f"Error fetching trades for user {profile.user.username}: {e}")
            continue
        
        trades_df = pd.DataFrame(trades)
        if trades_df.empty:
            success_dict = {profile.user.username: "No trades for the day"}
            fetch_successes.append(success_dict)
            print(f"No trades for the day for: {profile.user.username}.")
            continue

        # 1. Prepare data for model insertion
        new_trades = []
        
        # Get existing trade IDs for conflict checking
        existing_trade_ids = set(Trades.objects.filter(
            user=profile.user, 
            trade_id__in=trades_df['trade_id'].astype(str).tolist() # Cast to str for consistency
        ).values_list('trade_id', flat=True))
        
        # Iterate over the DataFrame rows
        for index, row in trades_df.iterrows():
            trade_id = str(row['trade_id'])
            
            # Skip if the trade already exists for this user
            if trade_id in existing_trade_ids:
                continue
                
            # 🔑 Timezone Localization Logic 🔑
            
            def make_timezone_aware(dt_obj):
                if dt_obj is None:
                    return None
                # Check if it's a naive datetime object (tzinfo is None)
                if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
                    return TIMEZONE.localize(dt_obj)
                return dt_obj # Already timezone-aware
                
            fill_ts = make_timezone_aware(row['fill_timestamp'])
            order_ts = make_timezone_aware(row['order_timestamp'])
            exchange_ts = make_timezone_aware(row['exchange_timestamp'])

            # 2. Map Kite data to your Django model fields
            trade_instance = Trades(
                user=profile.user,
                trade_id=trade_id,
                
                # Core Transaction Details
                order_id=str(row['order_id']),
                exchange_order_id=str(row['exchange_order_id']),
                account_id=str(row['account_id']), 
                
                # Instrument Details
                tradingsymbol=row['tradingsymbol'],
                instrument_token=str(row['instrument_token']),
                exchange=row['exchange'],
                product=row['product'],
                
                # Financial Details
                quantity=int(row['quantity']),
                average_price=row['average_price'],
                transaction_type=row['transaction_type'],
                
                # Timestamps (now properly localized/timezone-aware)
                fill_timestamp=fill_ts,
                order_timestamp=order_ts,
                exchange_timestamp=exchange_ts,
                
                # Meta
                tag= None,
            )
            new_trades.append(trade_instance)

        # 3. Efficiently save the new trades to the database
        if new_trades:
            created_trades = Trades.objects.bulk_create(
                new_trades, 
                ignore_conflicts=True
            )
            print(f"Successfully saved {len(created_trades)} new trades for {profile.user.username}.")
            
            success_dict = {profile.user.username: f"Successfully saved {len(created_trades)} new trades for {profile.user.username}."}
            fetch_successes.append(success_dict)
        else:
            success_dict = {profile.user.username: "No new trades to save"}
            fetch_successes.append(success_dict)
            # print(f"No new trades to save for {profile.user.username}.")
    
    return fetch_successes, fetch_errors

if __name__ == '__main__':
    successes, errors = fetch_trades()
    print(successes, errors)
    