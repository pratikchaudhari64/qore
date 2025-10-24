# trigger.py

import requests
import subprocess
import time
import logging
import os, sys
import webbrowser
import asyncio
import json

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

import config

# --- Configuration ---
FASTAPI_BASE_URL = config.CONFIG_AUTH.FASTAPI_BASE_URL
DAILY_AUTH_ENDPOINT = config.CONFIG_AUTH.DAILY_AUTH_ENDPOINT
HEALTH_CHECK_ENDPOINT = config.CONFIG_AUTH.HEALTH_CHECK_ENDPOINT
FASTAPI_APP_PATH = config.CONFIG_AUTH.FASTAPI_APP_PATH
FASTAPI_HOST = config.CONFIG_AUTH.FASTAPI_HOST
FASTAPI_PORT = str(config.CONFIG_AUTH.FASTAPI_PORT)
SESSION_FILE_NAME = config.CONFIG_AUTH.SESSION_FILE_NAME



import initiate_kite_login, load_session_from_file, save_session_to_file
# --- Functions ---

async def is_server_running(FASTAPI_BASE_URL) -> bool:
    """Checks if the FastAPI server is running by attempting a GET request."""
    try:
        print(f"...Making request to {FASTAPI_BASE_URL}")
        resp = requests.get(FASTAPI_BASE_URL, timeout=10)
        print(f"server response: {resp.status_code}, {resp.content}")
        return True

    except requests.exceptions.ConnectionError:
        logger.warning("Server is not reachable (ConnectionError).")
        return False
    except requests.exceptions.Timeout:
        logger.warning("Server connection timed out.")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during server check: {e}")
        return False


def start_fastapi_server(FASTAPI_APP_PATH, FASTAPI_HOST, FASTAPI_PORT):
    """Starts the FastAPI server in a new subprocess."""
    logger.info(f"""Server not running. 
    Attempting to start FastAPI server:
    uvicorn {FASTAPI_APP_PATH} --host {FASTAPI_HOST} --port {FASTAPI_PORT}""")
    
    # Use subprocess.Popen to run the command in the background
    # stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL suppresses output from the server process
    # You might want to remove these for debugging server startup issues.
    server_process = subprocess.Popen(
        ["uvicorn", FASTAPI_APP_PATH, "--host", FASTAPI_HOST, "--port", str(FASTAPI_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    logger.info(f"FastAPI server process started with PID: {server_process.pid}")
    return server_process



# --- Main Logic ---
if __name__ == "__main__":
    # check if session_file_name exists. if does not create a blank file with session_file_name
    # if exists, then below
    SESSION_FILE_PATH = os.path.join(current_dir, f"{SESSION_FILE_NAME}")
    if not os.path.exists(SESSION_FILE_PATH):
        with open(SESSION_FILE_PATH, 'w') as f:
            json.dump({"access_token": "dummy"}, f)
        loaded_session_data = load_session_from_file.get_file(SESSION_FILE_NAME)
    else: # if file already exists
        loaded_session_data = load_session_from_file.get_file(SESSION_FILE_NAME)
    

    logger.info(f"loaded sessions file: {loaded_session_data}")
    # check if server running at root
    if not asyncio.run(is_server_running(FASTAPI_BASE_URL)):
        print(f"Server not running. Invoking server as a subprocess...")
        server_proc = start_fastapi_server(FASTAPI_APP_PATH, FASTAPI_HOST, FASTAPI_PORT)
        print(f"sending signal {asyncio.run(is_server_running(FASTAPI_BASE_URL))}")

        # perform data fetch operations here
        # start with making a call to /daily_auth with loaded_sesion_data
        # right now, the trigger.py handles root server open/close after checking if live
        # /daily_auth to handle next steps, based on loaded_access_token.
        # if loaded_access_token has valid access_token, then fetch data
        # if not valid access_token, then initiate kite login and store the new loaded access_token
        # 
        response = requests.get(DAILY_AUTH_ENDPOINT, params= loaded_session_data)
        print(f"response: {response.status_code}")
        print(f"sent to: {response.url};")
        # print(f"response text/content if exists: {response.content}")
        print(f"headers: {response.headers.get('message')}")
        print(f"complete auth with OTP in 4000s. Server cloases after 4000s")


        print("waiting 4000s to terminate")
        time.sleep(4000)
        server_proc.terminate()
        time.sleep(5)
        print("terminated..")
        pass
    else:
        logger.info(f"Root server running at {FASTAPI_BASE_URL}")
        response = requests.get(DAILY_AUTH_ENDPOINT, params= loaded_session_data)
        print(response.status_code)
        # print(dir(response))
        # options = ['apparent_encoding', 'close', 'connection', 'content', 'cookies', 'elapsed', 'encoding', 'headers', 'history', 
        # 'is_permanent_redirect', 'is_redirect', 'iter_content', 'iter_lines', 'json', 'links', 'next', 'ok', 'raise_for_status',
        # 'raw', 'reason', 'request', 'status_code', 'text', 'url']
        # print(f"response text/content if exists: {response.content}")
        print(f"sent to: {response.url};")
        print(f"headers: {response.headers.get('message')}")
        print(f"sent to: {response.url}; Check /daily_auth or /frontpage for latest client-side update")
        # for opt in options:
        #     print(opt, response.options[opt])
        
    # check if server is running at root, by making a request to app_path at host:port.
    # if running alreasy, prepare to make reqeust to /daily_auth
    # if not, then invoke to start the server programatically, and be able to kill the process
