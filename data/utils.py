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

def update_env_variable(key, value, env_path=".env"):
    """
    Updates or adds a key-value pair in a .env file.
    If the key exists, its value is updated. If not, it's added.
    """
    lines = []
    found_key = False
    try:
        with open(env_path, "r") as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found_key = True
                else:
                    lines.append(line)
    except FileNotFoundError:
        pass # .env file doesn't exist yet, will be created

    if not found_key:
        lines.append(f'{key}="{value}"\n')

    with open(env_path, "w") as f:
        f.writelines(lines)
    


