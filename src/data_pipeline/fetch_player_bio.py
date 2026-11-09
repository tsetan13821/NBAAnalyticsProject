"""Fetch official NBA.com bio data (listed position, height, weight, draft, country) for every
player in the raw stats file, in a single PlayerIndex API call.

    python -m src.data_pipeline.fetch_player_bio
"""
import pandas as pd
from nba_api.stats.endpoints import playerindex

from src.paths import PLAYER_BIO, RAW_PLAYER_STATS

COLUMNS = {
    'PERSON_ID': 'PLAYER_ID',
    'POSITION': 'POSITION',
    'HEIGHT': 'HEIGHT',
    'WEIGHT': 'WEIGHT',
    'COUNTRY': 'COUNTRY',
    'COLLEGE': 'COLLEGE',
    'DRAFT_YEAR': 'DRAFT_YEAR',
    'DRAFT_ROUND': 'DRAFT_ROUND',
    'DRAFT_NUMBER': 'DRAFT_NUMBER',
}


def height_to_inches(height):
    """'6-11' -> 83. Returns None for missing or malformed values."""
    try:
        feet, inches = str(height).split('-')
        return int(feet) * 12 + int(inches)
    except ValueError:
        return None


def fetch_player_bio():
    player_ids = set(pd.read_csv(RAW_PLAYER_STATS)['PLAYER_ID'])

    index = playerindex.PlayerIndex(historical_nullable=1, timeout=60).get_data_frames()[0]
    bio = index[index['PERSON_ID'].isin(player_ids)][list(COLUMNS)].rename(columns=COLUMNS)

    bio['HEIGHT_IN'] = bio.pop('HEIGHT').map(height_to_inches)
    bio['WEIGHT_LB'] = pd.to_numeric(bio.pop('WEIGHT'), errors='coerce')
    for col in ('DRAFT_YEAR', 'DRAFT_ROUND', 'DRAFT_NUMBER'):
        bio[col] = pd.to_numeric(bio[col], errors='coerce').astype('Int64')  # NULL = undrafted

    missing = player_ids - set(bio['PLAYER_ID'])
    if missing:
        print(f"Warning: no bio data for {len(missing)} players: {sorted(missing)[:10]}")

    bio = bio.sort_values('PLAYER_ID')
    bio.to_csv(PLAYER_BIO, index=False)
    print(f"Saved bio data for {len(bio)} players to {PLAYER_BIO}")


if __name__ == "__main__":
    fetch_player_bio()
