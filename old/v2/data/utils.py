"""
data/utils.py
Utility functions related to asset and strategy data handling.
"""

from typing import List

def extract_unique_symbols(strategies: List[dict]) -> List[str]:
    """
    Extract all unique asset symbols from a list of strategy objects (dicts).
    Args:
        strategies: List of dicts, each with (possibly) an 'assets' list.
    Returns:
        List of unique asset symbols.
    """
    symbols = set()
    for strat in strategies:
        for asset in strat.get('assets', []):
            symbol = asset.get('symbol') if isinstance(asset, dict) else None
            if symbol:
                symbols.add(symbol)
    return list(symbols)
