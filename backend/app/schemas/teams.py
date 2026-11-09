from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Archetype, PlayerRef, Season, TeamRef, Tier


class TeamRecord(BaseModel):
    season: Season
    wins: int
    losses: int
    win_pct: float
    conference_rank: int
    point_diff_pg: float = Field(description="Points scored minus points allowed, per game")
    in_progress: bool = Field(description="True for the season under way: the numbers are so far, not final")


class TeamSummary(TeamRef):
    city: str
    nickname: str
    conference: Literal["East", "West"]
    latest: TeamRecord
    titles: int = Field(description="Championships since the first season in the data")


class TeamSeason(TeamRecord):
    team_abbr_then: str = Field(description="The abbreviation the franchise used that season, e.g. 'SEA'")
    conference: Literal["East", "West"]
    is_champion: bool


class FranchiseMvp(BaseModel):
    season: Season
    player: PlayerRef


class TeamDetail(TeamSummary):
    first_season: Season = Field(description="First season in the data")
    championships: list[Season]
    total_wins: int
    total_losses: int
    seasons: list[TeamSeason] = Field(description="Oldest first")
    mvps: list[FranchiseMvp] = Field(description="MVP awards won by the franchise's players, oldest first")


LeaderStat = Literal["points", "rebounds", "assists", "games"]


class FranchiseLeader(BaseModel):
    player: PlayerRef
    seasons: int
    first_season: Season
    last_season: Season
    games: int
    points: int
    rebounds: int
    assists: int
    pts_pg: float = Field(description="Points per game over his seasons with the franchise")
    on_roster: bool = Field(description="On the franchise's roster today")


class FranchiseLeaders(BaseModel):
    team: TeamRef
    by: LeaderStat
    since: Season = Field(description="Totals count from this season (the first in the data)")
    leaders: list[FranchiseLeader]


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
