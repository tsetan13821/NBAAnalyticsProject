"""Absolute paths to project files, so scripts and pages work from any working directory."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "saved_models"

RAW_PLAYER_STATS = RAW_DIR / "nba_player_stats.csv"
PLAYER_BIO = RAW_DIR / "player_bio.csv"
CURRENT_SEASON_STATS = RAW_DIR / "current_season_stats.csv"
CURRENT_SEASON_STANDINGS = RAW_DIR / "current_season_standings.csv"
MVP_DATA = PROCESSED_DIR / "mvp_data.csv"
CLUSTERED_PLAYERS = PROCESSED_DIR / "clustered_players_master.csv"
ALL_STARS_MASTER = PROCESSED_DIR / "all_stars_master.csv"
GAME_MATCHUPS = PROCESSED_DIR / "game_matchups.csv"

# Game predictor (src/game_model): one gzipped file per season, so a refresh only rewrites the season in progress
GAMES_DIR = RAW_DIR / "games"
INJURIES_DIR = RAW_DIR / "injuries"
INJURY_PDF_CACHE = PROJECT_ROOT / "data" / "cache" / "injury_reports"  # downloaded PDFs; not committed


def team_games_path(season: str) -> Path:
    return GAMES_DIR / f"team_games_{season}.csv.gz"


def player_games_path(season: str) -> Path:
    return GAMES_DIR / f"player_games_{season}.csv.gz"


def injuries_path(season: str) -> Path:
    return INJURIES_DIR / f"injuries_{season}.csv.gz"


def schedule_path(season: str) -> Path:
    return GAMES_DIR / f"schedule_{season}.csv"


GAME_FEATURES = PROCESSED_DIR / "game_features.csv.gz"
GAME_MODEL = MODELS_DIR / "game_model.json"
GAME_MODEL_METRICS = MODELS_DIR / "game_model_metrics.json"
# The season in progress, from python -m src.game_model.live
GAME_PREDICTIONS = PROCESSED_DIR / "game_predictions.csv"
GAME_PLAYERS = PROCESSED_DIR / "game_players.csv"
LIVE_META = PROCESSED_DIR / "live_meta.json"
NEXT_GAME_MODEL = MODELS_DIR / "next_game_model.pkl"
NEXT_GAME_METRICS = MODELS_DIR / "next_game_metrics.json"

# Serving artifacts built by src/export_db.py (not committed; rebuilt from the files above)
SERVING_DIR = PROJECT_ROOT / "backend" / "data"
SERVING_DB = SERVING_DIR / "nba.db"
DB_SCHEMA = PROJECT_ROOT / "src" / "db_schema.sql"
