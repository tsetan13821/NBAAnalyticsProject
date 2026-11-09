"""Shared feature helpers.

The raw dataset (data/raw/nba_player_stats.csv) stores counting stats as SEASON TOTALS
(nba_api's default PerMode). Rates and percentages (TS_PCT, USG_PCT, PIE, ...) are already
per-possession and need no conversion.
"""
import pandas as pd

COUNTING_STATS = ['MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV']


def to_per_game(df: pd.DataFrame, columns=COUNTING_STATS) -> pd.DataFrame:
    """Return a copy of df with season-total counting stats converted to per-game averages."""
    out = df.copy()
    games = out['GP'].clip(lower=1)
    for col in columns:
        if col in out.columns:
            out[col] = out[col] / games
    return out
