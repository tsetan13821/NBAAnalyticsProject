"""Fetch the season in progress: every player's stats so far and the current standings.

    python -m src.data_pipeline.fetch_current_season

The season comes from `data_collection.current_season` in the config. It is kept apart from the
completed seasons in data/raw/nba_player_stats.csv, so the models (which need finished seasons and
known award winners) never see it; src/export_db.py merges it into the serving database marked as
in progress. Anyone who has played at least one game is included, because the usual 20-game minimum
would leave nobody early in a season.

Re-run it (then `python -m src.export_db`) to bring the numbers up to date.
"""
from datetime import date

from src.data_collection import configured_features, fetch_season_data, load_config, select_columns
from src.data_pipeline.build_mvp_dataset import fetch_team_standings
from src.paths import CURRENT_SEASON_STANDINGS, CURRENT_SEASON_STATS


def fetch_current_season():
    config = load_config()
    season = config['data_collection'].get('current_season')
    if not season:
        print("No current_season in the config (off-season); nothing to fetch.")
        return

    stats = fetch_season_data(season, config['data_collection']['season_type'])
    if stats.empty:
        raise RuntimeError(f"No player stats returned for {season}")
    stats = select_columns(stats[stats['GP'] >= 1], configured_features(config))
    stats = stats.sort_values('PLAYER_NAME').reset_index(drop=True)

    standings = fetch_team_standings([season])
    if len(standings) != 30:
        raise RuntimeError(f"Expected standings for 30 teams in {season}, got {len(standings)}")
    standings['AS_OF'] = date.today().isoformat()

    stats.to_csv(CURRENT_SEASON_STATS, index=False)
    standings.sort_values('FRANCHISE_ABBREVIATION').to_csv(CURRENT_SEASON_STANDINGS, index=False)
    print(f"Saved {len(stats)} players' {season} stats to {CURRENT_SEASON_STATS}")
    print(f"Saved {season} standings (as of {standings['AS_OF'].iloc[0]}) to {CURRENT_SEASON_STANDINGS}")


if __name__ == "__main__":
    fetch_current_season()
