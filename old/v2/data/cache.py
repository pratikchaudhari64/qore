"""
data/cache.py
In-memory cache utility for improving speed and reducing redundant DB/API calls.
"""

import time

class DataCache:
    """Simple expiry-based in-memory cache for asset/strategy data."""

    def __init__(self, expiry_seconds: int = 300):
        # expiry_seconds: how long (in seconds) each cache entry is valid
        self.expiry = expiry_seconds
        self.cache_dict = {}

    def set(self, key, value):
        # Store value in cache with current timestamp
        self.cache_dict[key] = {'value': value, 'timestamp': time.time()}

    def get(self, key):
        """
        Retrieve value from cache if not expired, else return None.
        """
        record = self.cache_dict.get(key)
        if record:
            if (time.time() - record['timestamp']) < self.expiry:
                return record['value']
            else:
                # Remove expired cache entry
                self.cache_dict.pop(key)
        return None

    def clear(self):
        """Clears all cache entries."""
        self.cache_dict.clear()
