import json

from fastapi import APIRouter, Request, Response

from app.db import DbConn
from app.repositories import meta as meta_repo
from app.schemas.meta import Health, Meta, SeasonInfo

router = APIRouter(tags=["meta"])


def _season_from_id(season_id: int) -> str:
    start = int(str(season_id)[-4:])
    return f"{start}-{str(start + 1)[-2:]}"


@router.get("/meta", response_model=Meta, summary="Dataset range and headline model metrics")
def get_meta(request: Request):
    meta = request.app.state.db_meta
    next_game = json.loads(meta["next_game_metrics"])
    return {
        "first_season": meta["first_season"],
        "last_season": meta["last_season"],
        "built_at": meta["built_at"],
        "rosters_as_of": meta["rosters_as_of"],
        "current_season": meta["current_season"] or None,
        "current_season_as_of": meta["current_season_as_of"] or None,
        "mvp_model": {"correct": int(meta["mvp_correct"]), "seasons": int(meta["mvp_seasons"])},
        "next_game_model": {
            "train_first_season": _season_from_id(next_game["train_first_season_id"]),
            "train_last_season": _season_from_id(next_game["test_season_id"] - 1),
            "train_games": next_game["train_games"],
            "test_season": _season_from_id(next_game["test_season_id"]),
            "test_games": next_game["test_games"],
            "accuracy": next_game["accuracy"],
            "home_baseline": next_game["home_baseline"],
            "record_baseline": next_game["record_baseline"],
        },
    }


@router.get("/seasons", response_model=list[SeasonInfo], summary="Seasons with champion and MVP")
def list_seasons(conn: DbConn):
    return meta_repo.list_seasons(conn)


@router.get("/health", response_model=Health, summary="Health check")
def health(conn: DbConn, request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    schema_version = conn.execute("PRAGMA user_version").fetchone()[0]
    return {"status": "ok", "schema_version": schema_version, "built_at": request.app.state.db_meta["built_at"]}
