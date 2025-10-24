"""
common/logger.py
Simple logging setup for development and production.
"""

import logging

def get_logger(name='qore', level=logging.INFO):
    """
    Initializes and returns a logger with a standard format.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        fmt = '[%(asctime)s] %(levelname)s %(name)s: %(message)s'
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
