from typing import Annotated, get_args

from fastapi import APIRouter, Path, Query

from app.db import DbConn
from app.errors import NotFoundError
from app.repositories import teams as teams_repo
from app.routers import NOT_FOUND
from app.schemas.common import SEASON_PATTERN
from app.schemas.teams import FranchiseLeaders, LeaderStat, Roster, TeamDetail, TeamForm, TeamSummary

router = APIRouter(prefix="/teams", tags=["teams"])

TeamAbbr = Annotated[str, Path(min_length=2, max_length=3, examples=["BOS"])]
SeasonQuery = Annotated[
    str | None, Query(pattern=SEASON_PATTERN, description="Defaults to the latest available season")
]


def _team_ref_or_404(conn, abbr: str) -> dict:
    team = teams_repo.get_team_ref(conn, abbr)
    if team is None:
        raise NotFoundError(f"Team {abbr} not found")
    return team


@router.get("", response_model=list[TeamSummary], summary="All franchises with their latest record")
def list_teams(conn: DbConn):
    return teams_repo.list_teams(conn)


@router.get("/{abbr}", response_model=TeamDetail, responses=NOT_FOUND, summary="Franchise history")
def get_team(conn: DbConn, abbr: TeamAbbr):
    team = teams_repo.get_team(conn, abbr.upper())
    if team is None:
        raise NotFoundError(f"Team {abbr.upper()} not found")
    return team


@router.get("/{abbr}/roster", response_model=Roster, responses=NOT_FOUND, summary="Players on a team in a season")
def get_roster(conn: DbConn, abbr: TeamAbbr, season: SeasonQuery = None):
    abbr = abbr.upper()
    team = _team_ref_or_404(conn, abbr)
    season = season or teams_repo.latest_season(conn, abbr)
    players = teams_repo.get_roster(conn, abbr, season)
    if not players:
        raise NotFoundError(f"No {abbr} players found for {season}")
    return {"team": team, "season": season, "players": players}


@router.get(
    "/{abbr}/leaders", response_model=FranchiseLeaders, responses=NOT_FOUND,
    summary="The franchise's career leaders since the first season in the data",
)
def get_leaders(
    conn: DbConn,
    abbr: TeamAbbr,
    by: Annotated[LeaderStat, Query(description=f"Rank by total {', '.join(get_args(LeaderStat))}")] = "points",
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    abbr = abbr.upper()
    team = _team_ref_or_404(conn, abbr)
    return {
        "team": team, "by": by, "since": teams_repo.first_season(conn, abbr),
        "leaders": teams_repo.get_leaders(conn, abbr, by, limit),
    }


@router.get(
    "/{abbr}/form", response_model=TeamForm, responses=NOT_FOUND, summary="Game-by-game record (2020-21 onward)"
)
def get_form(conn: DbConn, abbr: TeamAbbr, season: SeasonQuery = None):
    abbr = abbr.upper()
    team = _team_ref_or_404(conn, abbr)
    season = season or teams_repo.latest_form_season(conn)
    form = teams_repo.get_form(conn, abbr, season)
    if form is None:
        raise NotFoundError(f"No game data for {abbr} in {season}")
    return {"team": team, **form}
