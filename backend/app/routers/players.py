from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query

from app.db import DbConn
from app.errors import NotFoundError
from app.repositories import players as players_repo
from app.routers import NOT_FOUND
from app.schemas.common import SEASON_PATTERN, Page, PositionGroup
from app.schemas.players import PlayerComparison, PlayerProfile, PlayerSummary, SimilarPlayers
from app.services import players as players_service

router = APIRouter(prefix="/players", tags=["players"])

SeasonQuery = Annotated[str | None, Query(pattern=SEASON_PATTERN, examples=["2023-24"])]


@router.get("", response_model=Page[PlayerSummary], summary="Search players")
def search_players(
    conn: DbConn,
    q: Annotated[str | None, Query(max_length=50, description="Name search; accents and case are ignored")] = None,
    position_group: PositionGroup | None = None,
    season: SeasonQuery = None,
    team: Annotated[str | None, Query(min_length=2, max_length=3, description="Played for this franchise")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total = players_repo.search_players(
        conn, query=q, position_group=position_group, season=season,
        team=team.upper() if team else None, limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# Declared before /{player_id} so "compare" is not parsed as a player id.
@router.get("/compare", response_model=PlayerComparison, responses=NOT_FOUND, summary="Compare players")
def compare_players(
    conn: DbConn,
    ids: Annotated[list[int], Query(min_length=2, max_length=4, description="Repeat the parameter: ?ids=1&ids=2")],
    season: Annotated[
        str | None, Query(pattern=SEASON_PATTERN, description="Defaults to the latest season they all played")
    ] = None,
    peer_group: Annotated[
        Literal["ALL", "POSITION"],
        Query(description="Percentiles vs all players, or vs each player's own position group"),
    ] = "ALL",
):
    return players_service.compare_players(conn, ids, season, peer_group)


@router.get("/{player_id}", response_model=PlayerProfile, responses=NOT_FOUND, summary="Player profile")
def get_player(conn: DbConn, player_id: Annotated[int, Path(ge=1)]):
    profile = players_repo.get_profile(conn, player_id)
    if profile is None:
        raise NotFoundError(f"Player {player_id} not found")
    return profile


@router.get("/{player_id}/similar", response_model=SimilarPlayers, responses=NOT_FOUND, summary="Similar players")
def get_similar_players(
    conn: DbConn,
    player_id: Annotated[int, Path(ge=1)],
    season: Annotated[
        str | None,
        Query(pattern=SEASON_PATTERN, description="Defaults to the player's latest season with archetype data"),
    ] = None,
):
    result = players_repo.get_similar(conn, player_id, season)
    if result is None:
        suffix = f" in {season}" if season else ""
        raise NotFoundError(f"No archetype data for player {player_id}{suffix}")
    return result
