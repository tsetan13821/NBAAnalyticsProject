"""Shared feature helpers.

The raw dataset (data/raw/nba_player_stats.csv) stores counting stats as SEASON TOTALS
(nba_api's default PerMode). Rates and percentages (TS_PCT, USG_PCT, PIE, ...) are already
per-possession and need no conversion.
"""
import pandas as pd

COUNTING_STATS = ['MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV']


def _position_from_per_game(reb, ast, blk):
    if reb >= 8.5 or (reb >= 7.5 and blk >= 1.2): return "Center (C)"
    if reb >= 6.5:
        return "Small Forward (SF)" if ast >= 5.0 else "Power Forward (PF)"
    if ast >= 5.5: return "Point Guard (PG)"
    if reb >= 5.5: return "Small Forward (SF)"
    if ast >= 3.5: return "Point Guard (PG)"
    return "Shooting Guard (SG)"


def infer_career_positions(df_totals: pd.DataFrame) -> pd.Series:
    """Infer one position per player from career per-game averages.

    Expects season-total counting stats (the raw dataset). Returns a Series indexed by PLAYER_ID.
    """
    career = df_totals.groupby('PLAYER_ID')[['GP', 'REB', 'AST', 'BLK']].sum()
    career = career.div(career['GP'].clip(lower=1), axis=0)
    return pd.Series(
        [_position_from_per_game(r.REB, r.AST, r.BLK) for r in career.itertuples()],
        index=career.index,
        name='INFERRED_POS',
    )


def to_per_game(df: pd.DataFrame, columns=COUNTING_STATS) -> pd.DataFrame:
    """Return a copy of df with season-total counting stats converted to per-game averages."""
    out = df.copy()
    games = out['GP'].clip(lower=1)
    for col in columns:
        if col in out.columns:
            out[col] = out[col] / games
    return out
