import os
import sys
import pickle
import logging

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

daily_auth_dotenv_path = os.path.join(project_root, "data", "daily_auth", ".env")
db_auth_env = os.path.join(project_root, "data", ".env")
services_env = os.path.join(project_root, "services", ".env")
root_env = os.path.join(project_root, ".env")

from dhanhq import dhanhq
import config
import json
import sourcedefender
from dhan_token_automate import GetAccessToken
from data.utils import update_env_variable

dhan_mobile = config.CONFIG_AUTH.DHAN_MOBILE
dhan_clientid = config.CONFIG_GLOBAL.DHAN_CLIENTID

dhanapikey = config.CONFIG_GLOBAL.DHAN_API_KEY
dhanapisecret = config.CONFIG_GLOBAL.DHAN_API_SECRET
dhantotpsecret = config.CONFIG_AUTH.DHAN_TOTP_SECRET
dhan_user_pin = config.CONFIG_AUTH.DHAN_USER_PIN

access_token = GetAccessToken(dhan_mobile, dhan_clientid, dhanapikey, dhanapisecret, dhantotpsecret, dhan_user_pin)

update_env_variable("DHAN_DATA_API_ACCESS_TOKEN", access_token, daily_auth_dotenv_path)

