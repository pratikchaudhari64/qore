import json
import datetime
import os
import logging
import sys
import webbrowser



current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


from fastapi.responses import RedirectResponse
from fastapi import HTTPException
import logging
from kiteconnect import KiteConnect
import pyotp
import config

totpsecret = config.CONFIG_AUTH.KITE_TOTP_SECRET

# Assume global_kc_instance (global KiteConnect object) and REDIRECT_URI (global string)
# are defined and accessible in the scope where this function is placed.
# For example, in your main.py.

async def initiate(kc_instance: object) -> RedirectResponse:
    """Generates the Kite login URL and returns a redirect response."""
    logger.info("initiating login with OTP!.. COMPLETE WITHIN 30s!")
    totp = pyotp.TOTP(totpsecret)
    otp = totp.now()
    print(f"OTP!: {otp}")
    try:
        login_url = kc_instance.login_url()
        logger.info(f"Redirecting to Kite login URL: {login_url}")
        webbrowser.open(login_url)
        
        return RedirectResponse(url=login_url)
    except Exception as e:
        logger.error(f"Error generating login URL: {e}", exc_info=True)
        # Raising HTTPException here ensures FastAPI catches it and returns a 500
        # if the login URL generation itself fails (e.g., bad API key config).
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate login: {e}"
        )
