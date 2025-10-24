"""
common/time_utils.py
Date and timezone handling utilities for QORE.
"""

from datetime import datetime
import pytz

def get_now_ist():
    """
    Returns the current time in IST (India Standard Time) as a naive datetime object.
    """
    tz = pytz.timezone('Asia/Kolkata')
    now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
    now_ist = now_utc.astimezone(tz)
    return now_ist.replace(tzinfo=None)

def today_ist_str():
    """
    Returns today's date string in IST (YYYY-MM-DD).
    """
    now = get_now_ist()
    return now.date().isoformat()

def iso_to_datetime(iso_str):
    """
    Converts an ISO 8601 date/time string to a naive datetime object.
    """
    return datetime.fromisoformat(iso_str)
