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

# Assume SESSION_FILE_PATH is defined globally as in the config snippet

def get_file(SESSION_FILE_NAME: str) -> dict | None:

    SESSION_FILE_PATH = os.path.join(current_dir, f"{SESSION_FILE_NAME}")
    if not os.path.exists(SESSION_FILE_PATH):
        logger.info(f"Session file not found at: {SESSION_FILE_PATH}")
        return None
    try:
        with open(SESSION_FILE_PATH, "r") as f:
            try:
                with open(SESSION_FILE_PATH, "r") as f:
                    data = json.load(f)
                    logger.info(f"file content: {data}")
                    # Convert string back to datetime if necessary
                    if 'last_updated' in data and isinstance(data['last_updated'], str):
                        try:
                            data['last_updated'] = datetime.datetime.fromisoformat(data['last_updated'])
                        except ValueError:
                            pass # Ignore if format is wrong, keep as string
                    logger.info(f"Kite session loaded from {SESSION_FILE_PATH}")
                    return data
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding session JSON file: {e}")
                return None
            except Exception as e:
                logger.error(f"Error loading session from file: {e}")
                return None
            # Convert string back to datetime if necessary
            # if 'last_updated' in data and isinstance(data['last_updated'], str):
            #     try:
            #         data['last_updated'] = datetime.datetime.fromisoformat(data['last_updated'])
            #     except ValueError:
            #         pass # Ignore if format is wrong, keep as string
            # logger.info(f"Kite session loaded from {SESSION_FILE_PATH}")
            # return data
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding session JSON file: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading session from file: {e}")
        return None
