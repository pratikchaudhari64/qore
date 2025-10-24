import json
import datetime
import os
import logging
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_sessions_file(SESSIONS_FILE_PATH: str):
    logger.info("clearing existing token..")
    sessions_path = SESSIONS_FILE_PATH
    with open(sessions_path, 'w') as f:
        f.truncate()