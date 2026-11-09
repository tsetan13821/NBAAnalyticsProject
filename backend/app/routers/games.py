import json
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from app.db import DbConn
from app.repositories import games as games_repo
from app.routers import BAD_REQUEST, NOT_FOUND
from app.schemas.games import GameDetail, GameModelDetails, GameResults, UpcomingGames
from app.services import games as games_service
from app.services.game_model import GameModel

router = APIRouter(prefix="/games", tags=["games"])


def get_model(request: Request) -> GameModel:
    return request.app.state.game_model


Model = Annotated[GameModel, Depends(get_model)]


@router.get("/upcoming", response_model=UpcomingGames, summary="Predictions for the coming week")
def upcoming_games(conn: DbConn, request: Request):
    live = json.loads(request.app.state.db_meta.get("game_live") or "{}")
    return {
        "season": live.get("season"), "as_of": live.get("as_of"), "injury_report": live.get("injury_report"),
        "games": games_repo.list_upcoming(conn),
    }


@router.get("/results", response_model=GameResults, summary="This season's games, as predicted beforehand")
def game_results(
    conn: DbConn,
    team: Annotated[str | None, Query(min_length=2, max_length=3, description="Only this team's games")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    team = team.upper() if team else None
    items, total = games_repo.list_results(conn, team, limit, offset)
    return {
        "items": items, "total": total, "limit": limit, "offset": offset,
        "record": games_service.track_record(conn, team),
    }


# Declared before /{game_id} so "model" is not parsed as a game id.
@router.get("/model", response_model=GameModelDetails, summary="The game model's inputs and evaluation")
def game_model(request: Request, model: Model):
    return games_service.model_details(model, request.app.state.db_meta["game_model_metrics"])


@router.get(
    "/{game_id}", response_model=GameDetail, responses={**NOT_FOUND, **BAD_REQUEST},
    summary="One game: prediction, why, and who is available",
)
def get_game(
    conn: DbConn,
    model: Model,
    game_id: Annotated[str, Path(pattern=r"^\d{10}$", examples=["0022600150"])],
    out: Annotated[list[int] | None, Query(description="What if these players sit out (repeat the parameter)")] = None,
    in_: Annotated[
        list[int] | None, Query(alias="in", description="What if these players play (repeat the parameter)")
    ] = None,
):
    return games_service.game_detail(conn, model, game_id, out or [], in_ or [])
