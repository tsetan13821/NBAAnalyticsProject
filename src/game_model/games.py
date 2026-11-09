"""One row per game, with everything known about both teams before tip-off.

Built from the team game logs in a single pass in date order, so every number for a game uses only
games that finished earlier (no look-ahead):

- Elo ratings: updated after every game by the margin, carried into each new season pulled a quarter of
  the way back to average. They need no games in the current season, so early-season games can be used.
- This season's net rating (points scored minus allowed per 100 possessions) and recent form (the
  same over the last ten games, recent games weighted more), both shrunk toward zero when few games
  have been played.
- Schedule: days of rest, back-to-backs, three games in four nights, distance travelled from the last
  game and clock change.

Crowds: the 2019-20 restart was played in the Orlando bubble (no home court at all) and most of
2020-21 had few or no fans. Both are flagged so the model can learn a smaller home edge for them.
"""
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from src.game_model.arenas import distance_km, tz_shift
from src.game_model.seasons import season_from_id
from src.paths import team_games_path

ELO_START = 1500.0
ELO_K = 20.0
ELO_HOME = 100.0  # Elo points of home edge with a normal crowd (~3.5 points of margin)
ELO_CARRY = 0.75  # share of last season's distance from average kept into the new season
ELO_PER_POINT = 28.0  # Elo difference worth one point of expected margin

BUBBLE_START = date(2020, 7, 30)  # 2019-20 restart in Orlando: every game at a neutral site, no fans
REDUCED_CROWD_SEASONS = {'2020-21'}

NET_SHRINK_GAMES = 10  # net rating counts fully only after about this many games
FORM_GAMES = 10
FORM_HALF_LIFE = 5.0
MAX_REST_DAYS = 5


def load_team_games(seasons: list[str]) -> pd.DataFrame:
    frames = [pd.read_csv(team_games_path(s), dtype={'GAME_ID': str}) for s in seasons if team_games_path(s).exists()]
    return pd.concat(frames, ignore_index=True)


def to_games(team_games: pd.DataFrame) -> pd.DataFrame:
    """Team rows -> one row per game with home and away sides, score margin and possessions."""
    df = team_games.copy()
    # "LAL vs. BOS": LAL is home; "LAL @ BOS": BOS is home. For neutral-site games both rows read
    # "X @ Y", so the home team comes from the matchup text, never from the row's own wording.
    home_abbr = np.where(
        df['MATCHUP'].str.contains(' vs. '),
        df['MATCHUP'].str.split(' vs. ').str[0],
        df['MATCHUP'].str.split(' @ ').str[-1],
    )
    df['IS_HOME'] = df['TEAM_ABBREVIATION'] == home_abbr
    df['POSS'] = df['FGA'] + 0.44 * df['FTA'] - df['OREB'] + df['TOV']
    neutral = df.groupby('GAME_ID')['MATCHUP'].transform(lambda m: (~m.str.contains(' vs. ')).all())
    df['NEUTRAL_SITE'] = neutral

    keep = ['GAME_ID', 'TEAM_ABBREVIATION', 'PTS', 'POSS']
    home = df[df['IS_HOME']][['SEASON_ID', 'GAME_DATE', 'NEUTRAL_SITE', *keep]]
    away = df[~df['IS_HOME']][keep]
    games = home.merge(away, on='GAME_ID', suffixes=('_HOME', '_AWAY'))
    games = games.rename(columns={
        'TEAM_ABBREVIATION_HOME': 'HOME', 'TEAM_ABBREVIATION_AWAY': 'AWAY',
        'PTS_HOME': 'HOME_PTS', 'PTS_AWAY': 'AWAY_PTS',
    })
    games['SEASON'] = games['SEASON_ID'].map(season_from_id)
    games['MARGIN'] = games['HOME_PTS'] - games['AWAY_PTS']
    games['POSS'] = (games['POSS_HOME'] + games['POSS_AWAY']) / 2
    games['HOME_WIN'] = (games['MARGIN'] > 0).astype(int)
    played = pd.to_datetime(games['GAME_DATE']).dt.date
    games['BUBBLE'] = (games['SEASON'] == '2019-20') & (played >= BUBBLE_START)
    games['REDUCED_CROWD'] = games['SEASON'].isin(REDUCED_CROWD_SEASONS)
    columns = ['GAME_ID', 'SEASON', 'GAME_DATE', 'HOME', 'AWAY', 'HOME_PTS', 'AWAY_PTS', 'MARGIN', 'POSS',
               'HOME_WIN', 'NEUTRAL_SITE', 'BUBBLE', 'REDUCED_CROWD']
    return games[columns].sort_values(['GAME_DATE', 'GAME_ID']).reset_index(drop=True)


def elo_home_edge(row) -> float:
    if row['BUBBLE'] or row['NEUTRAL_SITE']:
        return 0.0
    return ELO_HOME / 2 if row['REDUCED_CROWD'] else ELO_HOME


def elo_win_probability(diff: float) -> float:
    """Chance the side `diff` Elo points stronger (home edge included) wins."""
    return 1 / (1 + 10 ** (-diff / 400))


@dataclass
class _TeamSeason:
    """A team's running state within one season."""
    games: int = 0
    wins: int = 0
    margin: float = 0.0
    poss: float = 0.0
    recent: deque = field(default_factory=lambda: deque(maxlen=FORM_GAMES))  # margin per 100 possessions
    last_date: date | None = None
    last_site: str | None = None  # arena (team abbreviation) of the last game
    dates: deque = field(default_factory=lambda: deque(maxlen=3))


def _form(recent: deque) -> float:
    if not recent:
        return 0.0
    weights = 0.5 ** (np.arange(len(recent))[::-1] / FORM_HALF_LIFE)  # newest game weighs 1
    value = float(np.dot(weights, list(recent)) / weights.sum())
    return value * len(recent) / (len(recent) + 3)  # a couple of games say little


def add_team_state(games: pd.DataFrame) -> pd.DataFrame:
    """
    Elo, season-to-date record and net rating, form and schedule for both teams, before each game.
    Games not played yet (MARGIN missing) get the same pre-game columns, from the latest results.
    """
    elo: dict[str, float] = defaultdict(lambda: ELO_START)
    seasons: dict[tuple[str, str], _TeamSeason] = defaultdict(_TeamSeason)
    current_season = None
    out: dict[str, list] = defaultdict(list)

    for row in games.itertuples(index=False):
        row = row._asdict()
        if row['SEASON'] != current_season:
            current_season = row['SEASON']
            for team in list(elo):
                elo[team] = ELO_START + ELO_CARRY * (elo[team] - ELO_START)
        day = date.fromisoformat(row['GAME_DATE'])
        site = row['HOME']

        for side in ('HOME', 'AWAY'):
            team = row[side]
            state = seasons[(row['SEASON'], team)]
            out[f'{side}_ELO'].append(elo[team])
            out[f'{side}_GP'].append(state.games)
            out[f'{side}_WIN_PCT'].append(state.wins / state.games if state.games else 0.5)
            net = 100 * state.margin / state.poss if state.poss else 0.0
            out[f'{side}_NET'].append(net * state.games / (state.games + NET_SHRINK_GAMES))
            out[f'{side}_FORM'].append(_form(state.recent))
            rest = (day - state.last_date).days if state.last_date else MAX_REST_DAYS
            out[f'{side}_REST'].append(min(rest, MAX_REST_DAYS))
            out[f'{side}_B2B'].append(int(rest == 1))
            out[f'{side}_3IN4'].append(int(sum((day - d).days <= 3 for d in state.dates) >= 2))
            origin = state.last_site or team
            out[f'{side}_TRAVEL_KM'].append(distance_km(origin, site) if rest < MAX_REST_DAYS else 0.0)
            out[f'{side}_TZ_SHIFT'].append(tz_shift(origin, site) if rest < MAX_REST_DAYS else 0)

        if pd.isna(row['MARGIN']):
            # Not played yet (an upcoming game): the schedule moves on, ratings and records don't
            for side in ('HOME', 'AWAY'):
                state = seasons[(row['SEASON'], row[side])]
                state.last_date, state.last_site = day, site
                state.dates.append(day)
            continue

        # Elo update, margin-of-victory multiplier as in FiveThirtyEight's NBA Elo
        edge = elo_home_edge(row)
        diff = elo[row['HOME']] + edge - elo[row['AWAY']]
        expected = elo_win_probability(diff)
        won = 1.0 if row['MARGIN'] > 0 else 0.0
        winner_diff = diff if won else -diff
        multiplier = (abs(row['MARGIN']) + 3) ** 0.8 / (7.5 + 0.006 * winner_diff)
        shift = ELO_K * multiplier * (won - expected)
        elo[row['HOME']] += shift
        elo[row['AWAY']] -= shift

        for side, sign in (('HOME', 1), ('AWAY', -1)):
            state = seasons[(row['SEASON'], row[side])]
            margin = sign * row['MARGIN']
            state.games += 1
            state.wins += int(margin > 0)
            state.margin += margin
            state.poss += row['POSS']
            state.recent.append(100 * margin / row['POSS'])
            state.last_date, state.last_site = day, site
            state.dates.append(day)

    return pd.concat([games.reset_index(drop=True), pd.DataFrame(out)], axis=1)


def build_games(seasons: list[str]) -> pd.DataFrame:
    return add_team_state(to_games(load_team_games(seasons)))
