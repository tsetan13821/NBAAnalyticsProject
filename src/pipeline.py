"""Rebuild every dataset and model in dependency order.

    python -m src.pipeline                 # rebuild from the cached raw data (no player-stats API calls)
    python -m src.pipeline --fetch         # also re-download raw player stats, game logs, the schedule and
                                           # injury reports from the NBA

Order:
    1. data_collection        -> data/raw/nba_player_stats.csv         (only with --fetch)
       fetch_current_season   -> data/raw/current_season_*.csv         (only with --fetch; season in progress)
       fetch_player_bio       -> data/raw/player_bio.csv               (only with --fetch; bio and current teams)
       game_model.fetch_games, .schedule, .injury_reports
                              -> data/raw/games/, data/raw/injuries/   (only with --fetch; game logs, schedule,
                                                                        injury reports for the game model)
    2. build_mvp_dataset      -> data/processed/mvp_data.csv           (calls the standings API)
    3. player_clustering      -> data/processed/*_data.csv, clustered_players_master.csv
    4. all_star_prediction    -> data/processed/all_stars_*.csv        (needs mvp_data.csv)
    5. next_game_prediction   -> saved_models/next_game_model.pkl      (the Streamlit app's simpler model)
    6. game_model.train       -> saved_models/game_model.json          (features, training and evaluation)
    7. game_model.live        -> data/processed/game_predictions.csv   (the season in progress)
    8. mvp_prediction         -> prints leave-one-season-out accuracy  (needs mvp_data.csv)
    9. export_db              -> backend/data/nba.db                   (the serving database for the API)

To refresh only the game predictions (new results, the latest injury report), run
    python -m src.game_model.live && python -m src.export_db
"""
import argparse

from src import data_collection
from src.data_pipeline.fetch_current_season import fetch_current_season
from src.data_pipeline.fetch_player_bio import fetch_player_bio
from src.export_db import main as export_serving_db
from src.game_model.fetch_games import fetch_games
from src.game_model.injury_reports import fetch_injury_reports
from src.game_model.live import build_live
from src.game_model.schedule import main as fetch_schedule
from src.game_model.train import train_game_model
from src.data_pipeline.build_mvp_dataset import build_mvp_dataset
from src.models.all_star_prediction import run_all_star_pipeline
from src.models.mvp_prediction import run_loocv_cli
from src.models.next_game_prediction import train_next_game_model
from src.models.player_clustering import run_clustering_pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--fetch', action='store_true', help="Re-download raw player stats and game results from the NBA API.")
    args = parser.parse_args()

    steps = []
    if args.fetch:
        steps.append(("Collect raw player stats", data_collection.main))
        steps.append(("Fetch the season in progress", fetch_current_season))
        steps.append(("Fetch player bio data and current teams", fetch_player_bio))
        steps.append(("Fetch team and player game logs", fetch_games))
        steps.append(("Fetch the schedule", fetch_schedule))
        steps.append(("Fetch injury reports", fetch_injury_reports))
    steps += [
        ("Build MVP dataset", build_mvp_dataset),
        ("Player clustering", run_clustering_pipeline),
        ("All-Star selections", run_all_star_pipeline),
        ("Next-game model (Streamlit)", lambda: train_next_game_model(refresh=args.fetch)),
        ("Game model: train and evaluate", train_game_model),
        ("Game model: the season in progress", lambda: build_live(fetch=False)),
        ("MVP model evaluation", run_loocv_cli),
        ("Export serving database", export_serving_db),
    ]

    for i, (name, step) in enumerate(steps, 1):
        print(f"\n=== [{i}/{len(steps)}] {name} ===")
        step()


if __name__ == "__main__":
    main()
