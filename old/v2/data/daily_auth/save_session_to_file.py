import json
import datetime
import os, sys
import logging # Assume logger is configured as in previous snippet

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Assume SESSION_FILE_PATH is defined globally as in the config snippet

def save(data: dict, 
         SESSION_FILE_NAME: str):
    """Saves the session data to a local JSON file."""
    SESSION_FILE_PATH = os.path.join(current_dir, f"{SESSION_FILE_NAME}")
    try:
        # Convert datetime objects to string for JSON serialization
        # if 'last_updated' in data and isinstance(data['last_updated'], datetime.datetime):
        #     data['last_updated'] = data['last_updated'].isoformat()
        
        with open(SESSION_FILE_PATH, "w") as f:
            print(f"Storing to {SESSION_FILE_PATH}")
            json.dump(data, f, indent=4)
        logger.info(f"Kite session saved to {SESSION_FILE_PATH}")
    except Exception as e:
        logger.error(f"Error saving session to file: {e}")
