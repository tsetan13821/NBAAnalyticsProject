import json

from fastapi import APIRouter, Request, Response

from app.db import DbConn
from app.repositories import meta as meta_repo
from app.schemas.meta import Health, Meta, SeasonInfo

router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=Meta, summary="Dataset range and headline model metrics")
def get_meta(request: Request):
    meta = request.app.state.db_meta
    game = json.loads(meta["game_model_metrics"])
    live = json.loads(meta["game_live"] or "{}")
    return {
        "first_season": meta["first_season"],
        "last_season": meta["last_season"],
        "built_at": meta["built_at"],
        "rosters_as_of": meta["rosters_as_of"],
        "current_season": meta["current_season"] or None,
        "current_season_as_of": meta["current_season_as_of"] or None,
        "mvp_model": {"correct": int(meta["mvp_correct"]), "seasons": int(meta["mvp_seasons"])},
        "game_model": {
            **{k: game[k] for k in ("train_first_season", "train_last_season", "train_games", "test_season",
                                    "test_games")},
            "accuracy": game["held_out"]["accuracy"],
            "log_loss": game["held_out"]["log_loss"],
            "home_baseline": game["baselines"]["home_team"],
            "record_baseline": game["baselines"]["better_record"],
            "elo_baseline": game["baselines"]["elo"]["accuracy"],
        },
        "game_season": {
            "season": live["season"], "as_of": live["as_of"], "games_played": live["games_played"],
            "correct": live["correct_so_far"], "upcoming_games": live["upcoming_games"],
        } if live else None,
    }


@router.get("/seasons", response_model=list[SeasonInfo], summary="Seasons with champion and MVP")
def list_seasons(conn: DbConn):
    return meta_repo.list_seasons(conn)


@router.get("/health", response_model=Health, summary="Health check")
def health(conn: DbConn, request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    schema_version = conn.execute("PRAGMA user_version").fetchone()[0]
    return {"status": "ok", "schema_version": schema_version, "built_at": request.app.state.db_meta["built_at"]}
