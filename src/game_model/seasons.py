"""Season labels ("2024-25") and the season ranges the game model uses, from config/config.yaml."""
from dataclasses import dataclass

from src.data_collection import load_config


def season_start_year(season: str) -> int:
    return int(season[:4])


def season_label(start_year: int) -> str:
    """2024 -> "2024-25" """
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def seasons_between(first: str, last: str) -> list[str]:
    """Every season from first to last, inclusive, oldest first."""
    return [season_label(year) for year in range(season_start_year(first), season_start_year(last) + 1)]


def season_from_id(season_id: int | str) -> str:
    """NBA.com SEASON_ID 22024 (regular season starting 2024) -> "2024-25" """
    return season_label(int(str(season_id)[-4:]))


@dataclass(frozen=True)
class GameModelSeasons:
    team: list[str]
    """Seasons with team game logs (the earliest only warm up the Elo ratings)."""
    player: list[str]
    """Seasons with player game logs (the earliest only give players their prior-season values)."""
    injury: list[str]
    """Seasons with pre-game injury reports: the seasons the model can train and be tested on."""
    completed: str
    """The last completed season."""
    current: str | None
    """The season under way, if any. Fetched like the others, never used for training."""


def configured_seasons(config: dict | None = None) -> GameModelSeasons:
    config = config or load_config()
    collection, game = config['data_collection'], config['game_model']
    completed, current = collection['end_season'], collection.get('current_season')
    last = current or completed
    return GameModelSeasons(
        team=seasons_between(game['first_season'], last),
        player=seasons_between(game['player_first_season'], last),
        injury=seasons_between(game['injury_first_season'], last),
        completed=completed,
        current=current,
    )
