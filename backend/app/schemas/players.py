from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Archetype, PlayerRef, Season, TeamRef, Tier


class PlayerSummary(PlayerRef):
    position: str | None = Field(description="NBA.com listed position, e.g. 'G-F'", examples=["G"])
    first_season: Season
    last_season: Season
    latest_team: TeamRef


class SeasonStats(BaseModel):
    games: int
    min_pg: float
    pts_pg: float
    reb_pg: float
    ast_pg: float
    stl_pg: float
    blk_pg: float
    tov_pg: float
    fg_pct: float
    fg3_pct: float
    ft_pct: float
    ts_pct: float
    efg_pct: float
    usg_pct: float
    pie: float
    off_rating: float
    def_rating: float
    net_rating: float
    ast_to: float
    oreb_pct: float
    dreb_pct: float
    ast_pct: float
    reb_pct: float


class PlayerSeason(SeasonStats):
    season: Season
    team_abbr: str = Field(description="Current franchise abbreviation")
    team_abbr_then: str = Field(description="Abbreviation used that season, e.g. 'SEA'")
    archetype: Archetype | None = Field(
        description="NULL when below the archetype thresholds (20 games, 15 minutes per game, 12% usage)"
    )
    tier: Tier | None


class CareerAverages(BaseModel):
    games: int
    min_pg: float
    pts_pg: float
    reb_pg: float
    ast_pg: float
    stl_pg: float
    blk_pg: float


class PlayerProfile(PlayerSummary):
    height_in: int | None
    weight_lb: int | None
    country: str | None
    college: str | None
    draft_year: int | None = Field(description="NULL for undrafted players")
    draft_round: int | None
    draft_number: int | None
    seasons_played: int
    mvp_seasons: list[Season]
    career: CareerAverages
    seasons: list[PlayerSeason]


class SimilarPlayer(BaseModel):
    rank: int
    player: PlayerRef
    team_abbr: str
    archetype: Archetype | None
    tier: Tier | None
    distance: float = Field(description="Euclidean distance between archetype scores; lower is more similar")
    pts_pg: float
    reb_pg: float
    ast_pg: float


class SimilarPlayers(BaseModel):
    season: Season
    player: PlayerRef
    archetype: Archetype
    tier: Tier
    similar: list[SimilarPlayer]


MetricKey = Literal[
    "min_pg", "pts_pg", "reb_pg", "ast_pg", "stl_pg", "blk_pg", "tov_pg",
    "fg_pct", "fg3_pct", "ft_pct", "ts_pct", "efg_pct", "usg_pct", "pie",
    "off_rating", "def_rating", "net_rating", "ast_to", "oreb_pct", "dreb_pct", "ast_pct", "reb_pct",
]


class MetricInfo(BaseModel):
    key: MetricKey
    label: str = Field(examples=["Points"])
    format: Literal["per_game", "percent", "rating", "ratio"]
    higher_is_better: bool


class ComparedPlayer(BaseModel):
    player: PlayerRef
    team_abbr: str
    peer_group: Literal["ALL", "G", "F", "C"] = Field(description="Group the percentiles are relative to")
    stats: dict[MetricKey, float]
    percentiles: dict[MetricKey, float] = Field(
        description="0-100; higher is always better (turnovers and defensive rating are inverted)"
    )


class PlayerComparison(BaseModel):
    season: Season
    peer_group: Literal["ALL", "POSITION"]
    metrics: list[MetricInfo]
    players: list[ComparedPlayer]
