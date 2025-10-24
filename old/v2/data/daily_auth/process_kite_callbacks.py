from fastapi.responses import HTMLResponse, JSONResponse
import logging
import datetime
from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException, InputException
import logging
import asyncio
import os, sys

import clear_invalid_session

from data import fetcher
import save_session_to_file

# Assume global_kc_instance, API_SECRET, REDIRECT_URI are defined globally
# Assume session_data_cache, save_session_to_file, clear_invalid_session are defined globally
# Assume perform_daily_data_operations is defined


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)





async def fetch_data(access_token: str, 
                    error: str | None,
                    API_SECRET: str,
                    REDIRECT_URI: str,
                    kc_instance: object,
                    session_file_name: str,
                    session_data_cache: dict) -> HTMLResponse | JSONResponse:
    
    """
    Processes the callback from Kite Connect after user login.
    Exchanges request_token for access_token, saves it, and returns a response.
    """

    # CHECKS IF ERROR RECEIVED FROM KITE
    if error:
        logger.error(f"Kite login failed with error: {error}")
        return HTMLResponse(
            status_code=400,
            content=f"""
            <html>
                <head><title>Login Failed</title></head>
                <body>
                    <h1>Kite Login Failed</h1>
                    <p>Error: {error}</p>
                    <p>Please re-initiate trigger.py</p>
                    <p>Check server logs for more details.</p>
                </body>
            </html>
            """
        )

    logger.info(f"Received request_token: {access_token}")

    # CHECKS IF TOKEN CAN BE USED WITH KITE API SAFELY
    try:
        kc_instance.set_access_token(access_token)
        
        # data = kc_instance.generate_session(request_token, api_secret=API_SECRET)
        # access_token = data["access_token"]
        # public_token = data["public_token"]
        # kite_user_id = data["user_id"]

        # logger.info(f"Successfully generated access_token for Kite user: {kite_user_id}")

        session_data_cache.clear()
        session_data_cache.update({
            "access_token": access_token,
            "public_token": public_token,
            "kite_user_id": kite_user_id,
            "last_updated": datetime.datetime.now(datetime.timezone.utc)
        })
        # logger.info("Kite session stored in in-memory cache.")
        save_session_to_file.save(session_data_cache, SESSION_FILE_NAME = session_file_name)
        logger.info("Kite session saved to file.")

        kc_instance.set_access_token(access_token)
        logger.info("Global KiteConnect instance updated with access token.")

        # --- Proceed with data fetching and strategy ---
        # await perform_daily_data_operations(kc_instance)
        # data_fetcher = fetcher.AuthData(kc_instance)
        # logger.info(f"data fetcher invoked: {data_fetcher.init_aleert}")
        # await asyncio.sleep(5)
        # profile = data_fetcher.test_fetchprofile()
        # holdings = data_fetcher.test_fetchholdings()
        # orders = data_fetcher.test_fetchorders()

        # data_fetcher = fetcher.AuthData(kc_instance=kc_instance)
        # holdings = data_fetcher.test_fetchholdings()
        # print(holdings)
        logger.info(f"Process completed at: {datetime.datetime.now(datetime.timezone.utc).astimezone(tz=None).strftime('%Y-%m-%d %H:%M:%S IST')}")
        return HTMLResponse(
            status_code=200,
            content=f"""
            <html>
                <head><title>Kite Login Success and Slept for 5s</title></head>
                <body>
                    <p>Access Token available for user: <b>{kite_user_id}</b>.</p>

                    <p>You can close this page now and make requests to /frontpage</p>
                </body>
            </html>
            """
        )

    except (TokenException, InputException) as e:
        logger.error(f"KiteConnect token generation failed (likely expired/invalid request_token): {e}", exc_info=True)
        clear_invalid_session.clear_sessions_file(session_file_name)
        return HTMLResponse(
            status_code=401,
            content=f"""
            <html>
                <head><title>Login Failed</title></head>
                <body>
                    <h1>Kite Login Failed: Time Limit Exceeded or Invalid Token</h1>
                    <p>It seems you could not complete the login on Kite within the allowed time, or the provided token was invalid.</p>
                    <p>Please re-initiate trigger.py to fetch new request_token</p>
                    <p>Error details: {e}</p>
                </body>
            </html>
            """
        )
    except Exception as e:
        logger.error(f"Unexpected error during access token generation or initial data fetch: {e}", exc_info=True)
        return HTMLResponse(
            status_code=500,
            content=f"""
            <html>
                <head><title>Server Error</title></head>
                <body>
                    <h1>Internal Server Error</h1>
                    <p>An unexpected error occurred during the login process.</p>
                    <p>Please re-initiate trigger.py</p>
                    <p>Please check the server logs for more details or contact support.</p>
                    <p>Error: {e}</p>
                </body>
            </html>
            """
        )
