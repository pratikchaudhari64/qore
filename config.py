# stonks/config.py
import os
from dotenv import dotenv_values

class AppConfig:
    """
    Holds application configuration loaded from a specified .env file.
    Variables are accessible as attributes (e.g., config.KITE_API_KEY).
    """
    def __init__(self, dotenv_path: str):
        self._load_from_dotenv(dotenv_path)

    def _load_from_dotenv(self, dotenv_path: str):
        """
        Loads key-value pairs from the specified .env file and sets them
        as attributes of this AppConfig instance.
        """
        if not os.path.exists(dotenv_path):
            print(f"Warning: .env file not found at '{dotenv_path}'. "
                  f"Configuration might be incomplete or missing. "
                  f"Please ensure the specified .env file exists.")
            env_vars = {} # Initialize empty if file not found
        else:
            env_vars = dotenv_values(dotenv_path) # Reads the .env file into a dictionary
            

        # Set each key-value pair as an attribute of this object
        for key, value in env_vars.items():
            # Basic type casting for common types (extend as needed)
            if isinstance(value, str):
                if value.lower() == 'true':
                    setattr(self, key, True)
                elif value.lower() == 'false':
                    setattr(self, key, False)
                elif value.isdigit():
                    setattr(self, key, int(value))
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)

# --- Global Configuration Instance ---
# This part determines which .env file is loaded when 'config.py' is imported.

# Get the path to the 'stonks' (project root) directory
# Assuming config.py is directly under 'stonks/'
project_root = os.path.dirname(os.path.abspath(__file__))

# Construct paths
daily_auth_dotenv_path = os.path.join(project_root, "data", "daily_auth", ".env")
db_auth_env = os.path.join(project_root, "data", ".env")
services_env = os.path.join(project_root, "services", ".env")
root_path = os.path.join(project_root, ".env")

# Create the global config instance using the specific path
CONFIG_AUTH = AppConfig(daily_auth_dotenv_path)
CONFIG_GLOBAL = AppConfig(root_path) 
CONFIG_GLOBAL_DB = AppConfig(db_auth_env) 
CONFIG_SERVICES = AppConfig(services_env) 

# print(dir(CONFIG_GLOBAL_DB))


__all__ = ['CONFIG_AUTH', 'CONFIG_GLOBAL', 'CONFIG_GLOBAL_DB', 'CONFIG_SERVICES']

# You can still add properties for specific keys for better IDE autocompletion and type hinting
# @property
# def KITE_API_KEY(self) -> str | None:
#     return getattr(self, 'KITE_API_KEY', None)
# ... (add other properties as needed)