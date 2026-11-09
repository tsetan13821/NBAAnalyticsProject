from pydantic import BaseModel, Field

from app.schemas.common import PlayerRef, Season, TeamRef


class MvpSeasonResult(BaseModel):
    season: Season
    era: int = Field(description="1 = 2000-01 to 2007-08, 2 = 2008-09 onward (each era has its own feature set)")
    predicted: PlayerRef
    actual: PlayerRef
    actual_rank: int = Field(description="Where the real MVP ranked in the model's list")
    correct: bool
    candidates: int


class EraAccuracy(BaseModel):
    era: int
    label: str
    seasons: int
    correct: int


class MvpOverview(BaseModel):
    correct: int
    total: int
    top3: int = Field(description="Seasons where the real MVP was in the model's top 3")
    eras: list[EraAccuracy]
    seasons: list[MvpSeasonResult]


class CandidateStats(BaseModel):
    games: int
    pts_pg: float
    reb_pg: float
    ast_pg: float
    ts_pct: float
    pie: float


class MvpCandidate(BaseModel):
    rank: int
    player: PlayerRef
    team: TeamRef
    model_score: float = Field(description="Raw model output (not a calibrated probability)")
    score_share: float = Field(description="model_score normalised to sum to 1 within the season")
    is_mvp: bool
    stats: CandidateStats
    team_win_pct: float
    team_conference_rank: int


class MvpRace(BaseModel):
    season: Season
    era: int
    correct: bool
    actual_rank: int
    candidates: list[MvpCandidate]
