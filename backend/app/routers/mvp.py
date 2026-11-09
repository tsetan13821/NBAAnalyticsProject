from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.db import DbConn
from app.errors import NotFoundError
from app.repositories import mvp as mvp_repo
from app.routers import NOT_FOUND
from app.schemas.common import SEASON_PATTERN
from app.schemas.mvp import MvpOverview, MvpRace

router = APIRouter(prefix="/mvp", tags=["mvp"])


@router.get("", response_model=MvpOverview, summary="MVP model accuracy across all seasons")
def get_mvp_overview(conn: DbConn):
    return mvp_repo.get_overview(conn)


@router.get("/{season}", response_model=MvpRace, responses=NOT_FOUND, summary="MVP race for one season")
def get_mvp_race(
    conn: DbConn,
    season: Annotated[str, Path(pattern=SEASON_PATTERN, examples=["2023-24"])],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    race = mvp_repo.get_race(conn, season, limit)
    if race is None:
        raise NotFoundError(f"No MVP predictions for season {season}")
    return race
