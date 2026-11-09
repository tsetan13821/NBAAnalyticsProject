"""Fetch official NBA.com bio data (listed position, height, weight, draft, country) and current
team for every player in the raw stats file, in a single PlayerIndex API call.

The current team comes from NBA.com's rosters on the day this runs (CURRENT_TEAM is blank for
players not on a roster: retired players and free agents). ROSTERS_AS_OF records that day, so the
site can say how fresh it is. Re-run this to pick up trades and signings.

    python -m src.data_pipeline.fetch_player_bio
"""
from datetime import date

import pandas as pd
from nba_api.stats.endpoints import playerindex

from src.paths import CURRENT_SEASON_STATS, PLAYER_BIO, RAW_PLAYER_STATS

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
    if CURRENT_SEASON_STATS.exists():  # players who have only played in the season under way
        player_ids |= set(pd.read_csv(CURRENT_SEASON_STATS)['PLAYER_ID'])

    index = playerindex.PlayerIndex(historical_nullable=1, timeout=60).get_data_frames()[0]
    index = index[index['PERSON_ID'].isin(player_ids)]
    bio = index[list(COLUMNS)].rename(columns=COLUMNS)

    # ROSTER_STATUS is 1 for players on a current roster; for everyone else TEAM_* is their last team.
    on_roster = index['ROSTER_STATUS'].eq(1)
    bio['CURRENT_TEAM'] = index['TEAM_ABBREVIATION'].where(on_roster)
    bio['ROSTERS_AS_OF'] = date.today().isoformat()

    bio['HEIGHT_IN'] = bio.pop('HEIGHT').map(height_to_inches)
    bio['WEIGHT_LB'] = pd.to_numeric(bio.pop('WEIGHT'), errors='coerce')
    for col in ('DRAFT_YEAR', 'DRAFT_ROUND', 'DRAFT_NUMBER'):
        bio[col] = pd.to_numeric(bio[col], errors='coerce').astype('Int64')  # NULL = undrafted

    missing = player_ids - set(bio['PLAYER_ID'])
    if missing:
        print(f"Warning: no bio data for {len(missing)} players: {sorted(missing)[:10]}")

    bio = bio.sort_values('PLAYER_ID')
    bio.to_csv(PLAYER_BIO, index=False)
    print(f"Saved bio data for {len(bio)} players ({int(on_roster.sum())} on a current roster) to {PLAYER_BIO}")


if __name__ == "__main__":
    fetch_player_bio()
