"""
common/config.py
Configuration loader for environment variables and settings.
"""

import os

def get_env_var(key, default=None):
    """
    Returns the value of an environment variable, or a default if not found.
    """
    return os.environ.get(key, default)

def get_db_uri():
    """
    Returns the database URI for the QORE app.
    """
    return get_env_var('QORE_DB_URI', 'postgresql://username:password@localhost:5432/qore')

def get_app_secret():
    """
    Returns the app's secret key for Flask or other secrets.
    """
    return get_env_var('QORE_APP_SECRET', 'dev-secret')
