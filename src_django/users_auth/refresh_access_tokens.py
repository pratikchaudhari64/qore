import os, sys
import django
from django.conf import settings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qore.settings")

django.setup()

from users_auth.models import UserProfile
from django.contrib.auth.models import User
from django.conf import settings

from kiteconnect import KiteConnect
import pyotp
import requests
from urllib.parse import urlparse, parse_qs
import time


all_profiles = UserProfile.objects.select_related('user').all()
for profile in all_profiles:

    kiteusername = profile.kite_username
    kitepwd = profile.kite_pwd
    totpsecret = profile.totp_key
    kiteapikey = profile.kite_api_key
    kiteapisecret = profile.kite_api_secret
    print(kiteusername, kitepwd, totpsecret, kiteapikey, kiteapisecret)
    
    session = requests.Session()
    kite = KiteConnect(api_key=kiteapikey)

    try:
        request_id = session.post("https://kite.zerodha.com/api/login", 
                            {"user_id": kiteusername, "password": kitepwd}).json()["data"]["request_id"]
        
        resp = session.post("https://kite.zerodha.com/api/twofa", 
                            {"user_id": kiteusername, "request_id": request_id, "twofa_value": pyotp.TOTP(totpsecret).now()})
        
        api_session = session.get(f"https://kite.trade/connect/login?api_key={kiteapikey}")
        
        parsed = urlparse(api_session.url)

        request_token = parse_qs(parsed.query)["request_token"][0]
        kitesession_data = kite.generate_session(request_token, api_secret=kiteapisecret)
        access_token = kitesession_data['access_token']
        
        profile.access_token = access_token  # Assign the new token to the model instance
        profile.save()
        print(f"Database updated for {profile.user.username} with token: {profile.access_token}.")
        time.sleep(2)
    except Exception as e:
        print(f"Error while refreshing access token: {type(e)}: {e}")
    #     raise