from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Archetype, PlayerRef, Season, TeamRef, Tier


class TeamRecord(BaseModel):
    season: Season
    wins: int
    losses: int
    win_pct: float
    conference_rank: int
    in_progress: bool = Field(description="True for the season under way: the numbers are so far, not final")


class TeamSummary(TeamRef):
    city: str
    nickname: str
    conference: Literal["East", "West"]
    latest: TeamRecord


class TeamSeason(TeamRecord):
    team_abbr_then: str
    conference: Literal["East", "West"]
    point_diff_pg: float
    is_champion: bool


class TeamDetail(TeamSummary):
    championships: list[Season]
    total_wins: int
    total_losses: int
    seasons: list[TeamSeason]


class RosterPlayer(BaseModel):
    player: PlayerRef
    games: int
    min_pg: float
    pts_pg: float
    reb_pg: float
    ast_pg: float
    ts_pct: float
    archetype: Archetype | None
    tier: Tier | None


class Roster(BaseModel):
    team: TeamRef
    season: Season
    players: list[RosterPlayer]


class FormGame(BaseModel):
    date: str
    opponent_abbr: str
    is_home: bool
    won: bool
    win_pct: float  # running win % after this game


class TeamForm(BaseModel):
    team: TeamRef
    season: Season
    wins: int
    losses: int
    win_pct: float
    home_win_pct: float | None
    road_win_pct: float | None
    games: list[FormGame]
