"""Absolute paths to project files, so scripts and pages work from any working directory."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "saved_models"

RAW_PLAYER_STATS = RAW_DIR / "nba_player_stats.csv"
MVP_DATA = PROCESSED_DIR / "mvp_data.csv"
CLUSTERED_PLAYERS = PROCESSED_DIR / "clustered_players_master.csv"
ALL_STARS_MASTER = PROCESSED_DIR / "all_stars_master.csv"
GAME_MATCHUPS = PROCESSED_DIR / "game_matchups.csv"
NEXT_GAME_MODEL = MODELS_DIR / "next_game_model.pkl"
