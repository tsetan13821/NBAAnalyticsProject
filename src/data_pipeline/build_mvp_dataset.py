import time

import pandas as pd
from nba_api.stats.endpoints import leaguestandings
from nba_api.stats.static import teams

from src.nba_reference import MVP_WINNERS, franchise_abbreviation
from src.paths import MVP_DATA, PROCESSED_DIR, RAW_PLAYER_STATS


def fetch_team_standings(seasons):
    """Fetches team standings for a list of seasons and returns a consolidated DataFrame.

    Teams are keyed by FRANCHISE_ABBREVIATION (the current abbreviation, e.g. OKC for the
    2007-08 SuperSonics), because the standings endpoint identifies teams by franchise ID.
    """
    all_standings = []
    team_dict = {team['id']: team['abbreviation'] for team in teams.get_teams()}

    print(f"Fetching team standings for {len(seasons)} seasons. This may take a moment to avoid rate limits...")

    for season in seasons:
        try:
            print(f"Fetching {season}...")
            df = leaguestandings.LeagueStandings(season=season, timeout=60).get_data_frames()[0]
            df['FRANCHISE_ABBREVIATION'] = df['TeamID'].map(team_dict)
            df['SEASON'] = season
            all_standings.append(df[['FRANCHISE_ABBREVIATION', 'SEASON', 'WINS', 'LOSSES', 'WinPCT', 'DiffPointsPG']])
            time.sleep(1.2)  # Avoid NBA API rate limiting
        except Exception as e:
            print(f"Error fetching data for {season}: {e}")

    return pd.concat(all_standings, ignore_index=True)


def build_mvp_dataset():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load Player Stats
    print("Loading player stats...")
    df_players = pd.read_csv(RAW_PLAYER_STATS)

    features_to_keep = [
        'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'SEASON', 'GP', 'MIN',
        'PTS', 'REB', 'AST', 'STL', 'BLK', 'DEF_RATING', 'AST_PCT', 'TS_PCT', 'USG_PCT', 'PIE', 'NET_RATING'
    ]
    available_cols = [col for col in features_to_keep if col in df_players.columns]
    df_players = df_players[available_cols].copy()
    df_players['FRANCHISE_ABBREVIATION'] = df_players['TEAM_ABBREVIATION'].map(franchise_abbreviation)

    # 2. Fetch Team Standings
    df_teams = fetch_team_standings(df_players['SEASON'].unique())

    # 3. Merge Player Stats with Team Standings
    print("Merging player stats with team standings...")
    df_merged = pd.merge(df_players, df_teams, on=['FRANCHISE_ABBREVIATION', 'SEASON'], how='left')

    unmatched = df_merged[df_merged['WINS'].isna()]
    if not unmatched.empty:
        summary = unmatched.groupby(['SEASON', 'TEAM_ABBREVIATION']).size()
        raise ValueError(
            f"{len(unmatched)} player-seasons have no matching team standings "
            f"(missing season fetch or unknown abbreviation):\n{summary}"
        )

    # 4. Add the IS_MVP Target Column
    print("Adding IS_MVP target column...")
    df_merged['IS_MVP'] = (df_merged['PLAYER_NAME'] == df_merged['SEASON'].map(MVP_WINNERS)).astype(int)

    labelled_seasons = set(df_merged.loc[df_merged['IS_MVP'] == 1, 'SEASON'])
    missing_labels = sorted(s for s in df_merged['SEASON'].unique() if s in MVP_WINNERS and s not in labelled_seasons)
    if missing_labels:
        print(f"Warning: MVP winner not found in player data for seasons: {missing_labels}")

    # 5. Drop rows lacking critical metrics
    df_merged.dropna(subset=['PIE', 'TS_PCT'], inplace=True)

    # 6. Save the new dataset
    print(f"Saving MVP dataset with {len(df_merged)} rows to {MVP_DATA}...")
    df_merged.to_csv(MVP_DATA, index=False)
    print("Done!")


if __name__ == "__main__":
    build_mvp_dataset()
