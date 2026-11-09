"""Rebuild every dataset and model in dependency order.

    python -m src.pipeline                 # rebuild from the cached raw data (no player-stats API calls)
    python -m src.pipeline --fetch         # also re-download raw player stats and game results from the NBA API

Order:
    1. data_collection        -> data/raw/nba_player_stats.csv         (only with --fetch)
    2. build_mvp_dataset      -> data/processed/mvp_data.csv           (calls the standings API)
    3. player_clustering      -> data/processed/*_data.csv, clustered_players_master.csv
    4. all_star_prediction    -> data/processed/all_stars_*.csv        (needs mvp_data.csv)
    5. next_game_prediction   -> saved_models/next_game_model.pkl      (re-fetches games only with --fetch)
    6. mvp_prediction         -> prints leave-one-season-out accuracy  (needs mvp_data.csv)
"""
import argparse

from src import data_collection
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
    steps += [
        ("Build MVP dataset", build_mvp_dataset),
        ("Player clustering", run_clustering_pipeline),
        ("All-Star selections", run_all_star_pipeline),
        ("Next-game model", lambda: train_next_game_model(refresh=args.fetch)),
        ("MVP model evaluation", run_loocv_cli),
    ]

    for i, (name, step) in enumerate(steps, 1):
        print(f"\n=== [{i}/{len(steps)}] {name} ===")
        step()


if __name__ == "__main__":
    main()
