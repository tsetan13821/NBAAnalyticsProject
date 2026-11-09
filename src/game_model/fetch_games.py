"""Fetch regular-season team and player game logs from the NBA stats API.

    python -m src.game_model.fetch_games              # missing seasons, plus the season in progress
    python -m src.game_model.fetch_games --refresh    # every season again

One gzipped CSV per season and kind in data/raw/games/. A completed season never changes, so it is
only downloaded once; the season in progress is downloaded again on every run.

Team logs have one row per team per game (scores and the box-score totals needed for possessions);
player logs have one row per player per game played. A player who sat out has no row: that absence
is how the model knows who played.
"""
import argparse
import time

import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder, playergamelogs

from src.game_model.seasons import configured_seasons
from src.paths import GAMES_DIR, GZIP, player_games_path, team_games_path

TEAM_COLUMNS = [
    'SEASON_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'GAME_ID', 'GAME_DATE', 'MATCHUP', 'WL', 'MIN',
    'PTS', 'FGA', 'FTA', 'OREB', 'TOV', 'PLUS_MINUS',
]
PLAYER_COLUMNS = [
    'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION', 'GAME_ID', 'GAME_DATE', 'MIN',
    'PTS', 'FGM', 'FGA', 'FTM', 'FTA', 'OREB', 'DREB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PLUS_MINUS',
]
REQUEST_PAUSE_S = 1.0  # between calls, to stay well inside the API's rate limits
RETRIES = 3


def _with_retries(call, what):
    for attempt in range(1, RETRIES + 1):
        try:
            return call()
        except Exception as error:  # the API fails with timeouts and connection resets, not typed errors
            if attempt == RETRIES:
                raise RuntimeError(f"{what} failed after {RETRIES} attempts") from error
            wait = 5 * attempt
            print(f"  {what}: {error.__class__.__name__}, retrying in {wait}s")
            time.sleep(wait)


def fetch_team_games(season: str) -> pd.DataFrame:
    df = _with_retries(
        lambda: leaguegamefinder.LeagueGameFinder(
            season_nullable=season, league_id_nullable='00', season_type_nullable='Regular Season', timeout=90,
        ).get_data_frames()[0],
        f"team games {season}",
    )
    # SEASON_ID prefix 2 = regular season; the filter above should already guarantee it
    df = df[df['SEASON_ID'].astype(str).str.startswith('2')]
    df = df[TEAM_COLUMNS].copy()
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE']).dt.strftime('%Y-%m-%d')
    return df.sort_values(['GAME_DATE', 'GAME_ID', 'TEAM_ID']).reset_index(drop=True)


def fetch_player_games(season: str) -> pd.DataFrame:
    df = _with_retries(
        lambda: playergamelogs.PlayerGameLogs(
            season_nullable=season, season_type_nullable='Regular Season', timeout=90,
        ).get_data_frames()[0],
        f"player games {season}",
    )
    df = df[PLAYER_COLUMNS].copy()
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE']).dt.strftime('%Y-%m-%d')
    df['MIN'] = df['MIN'].round(2)
    return df.sort_values(['GAME_DATE', 'GAME_ID', 'TEAM_ID', 'PLAYER_ID']).reset_index(drop=True)


def check_team_games(df: pd.DataFrame, season: str) -> None:
    """Every game has exactly two team rows, one win and one loss."""
    per_game = df.groupby('GAME_ID')['WL'].agg(['size', lambda wl: set(wl)])
    bad = per_game[(per_game['size'] != 2) | (per_game['<lambda_0>'] != {'W', 'L'})]
    if len(bad):
        raise RuntimeError(f"{season}: {len(bad)} games without exactly one winner and one loser, e.g. {list(bad.index[:3])}")


def fetch_games(refresh: bool = False) -> None:
    seasons = configured_seasons()
    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [(s, team_games_path(s), fetch_team_games) for s in seasons.team]
    jobs += [(s, player_games_path(s), fetch_player_games) for s in seasons.player]

    for season, path, fetch in jobs:
        if path.exists() and not refresh and season != seasons.current:
            continue
        df = fetch(season)
        if df.empty:
            print(f"  {path.name}: no games yet")
            continue
        if fetch is fetch_team_games:
            check_team_games(df, season)
        df.to_csv(path, index=False, compression=GZIP)
        print(f"  {path.name}: {len(df):,} rows, {df['GAME_ID'].nunique():,} games")
        time.sleep(REQUEST_PAUSE_S)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--refresh', action='store_true', help="Download completed seasons again too.")
    fetch_games(refresh=parser.parse_args().refresh)
