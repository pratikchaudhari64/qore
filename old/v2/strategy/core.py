# strategy/core.py

import uuid
from datetime import datetime

class Strategy:
    """
    Represents a portfolio strategy/action (buy, sell, rebalance, etc.).
    """
    def __init__(
        self,
        id=None,
        timestamp=None,
        type='',
        assets=None,
        status='current',
        note='',
        research=None,
        tags=None,
        challenger_strategies=None,
        freeze_timestamp=None
    ):
        self.id = id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.type = type
        self.assets = assets or []  # List of dicts: [{symbol, qty, price, weight}]
        self.status = status
        self.note = note
        self.research = research or {}
        self.tags = tags or []
        self.challenger_strategies = challenger_strategies or []
        self.freeze_timestamp = freeze_timestamp

    def freeze(self, freeze_time=None):
        """Locks strategy as immutable (frozen)."""
        self.status = 'frozen'
        self.freeze_timestamp = freeze_time or datetime.utcnow().isoformat()

    def is_frozen(self):
        return self.status == 'frozen'

    def is_current(self):
        return self.status == 'current'

    def is_challenger(self):
        return self.status == 'challenger'

    def to_dict(self):
        """Serializes object for DB/API/JSON usage."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type,
            "assets": self.assets,
            "status": self.status,
            "note": self.note,
            "research": self.research,
            "tags": self.tags,
            "challenger_strategies": self.challenger_strategies,
            "freeze_timestamp": self.freeze_timestamp
        }

    @staticmethod
    def from_dict(data):
        """Creates a Strategy object from dictionary (e.g., DB row)."""
        return Strategy(
            id=data.get('id'),
            timestamp=data.get('timestamp'),
            type=data.get('type', ''),
            assets=data.get('assets', []),
            status=data.get('status', 'current'),
            note=data.get('note', ''),
            research=data.get('research', {}),
            tags=data.get('tags', []),
            challenger_strategies=data.get('challenger_strategies', []),
            freeze_timestamp=data.get('freeze_timestamp')
        )
