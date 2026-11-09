"""Shared, cached data loaders for the dashboard pages.

Importing this module also puts the project root on sys.path so pages can import from `src`,
whichever directory `streamlit run` was started from.
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import joblib  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from src import paths  # noqa: E402
from src.features import to_per_game  # noqa: E402


def _read_csv(path):
    return pd.read_csv(path) if Path(path).exists() else None


@st.cache_data
def load_player_stats():
    """Raw player seasons with counting stats converted to per-game averages."""
    df = _read_csv(paths.RAW_PLAYER_STATS)
    return None if df is None else to_per_game(df)


@st.cache_data
def load_raw_player_totals():
    """Raw player seasons with counting stats as season totals."""
    return _read_csv(paths.RAW_PLAYER_STATS)


@st.cache_data
def load_mvp_data():
    df = _read_csv(paths.MVP_DATA)
    if df is not None:
        df['PLAYER_NAME'] = df['PLAYER_NAME'].astype(str).str.strip()
        df['SEASON'] = df['SEASON'].astype(str).str.strip()
    return df


@st.cache_data
def load_clustered_players():
    """Clustered player seasons (counting stats are already per game)."""
    return _read_csv(paths.CLUSTERED_PLAYERS)


@st.cache_data
def load_all_stars():
    """Model All-Star selections with counting stats converted to per-game averages."""
    df = _read_csv(paths.ALL_STARS_MASTER)
    return None if df is None else to_per_game(df)


@st.cache_data
def load_game_matchups():
    df = _read_csv(paths.GAME_MATCHUPS)
    if df is not None:
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
        df = df.sort_values(['GAME_DATE', 'GAME_ID']).reset_index(drop=True)
    return df


@st.cache_resource
def load_next_game_model():
    return joblib.load(paths.NEXT_GAME_MODEL) if paths.NEXT_GAME_MODEL.exists() else None
