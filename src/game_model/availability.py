"""Player value, and how much of it each team has available for a game.

Value. Each game, a player's box score is summed into a Game Score (John Hollinger's single-number
summary: points, shooting efficiency, rebounds, assists, steals, blocks, fouls and turnovers). A
player's *rate* is his Game Score per minute; his *value* is how far that rate is above replacement
level (the 20th percentile of regular players that season, roughly a deep-bench player) times the
minutes he usually plays. Before each game, the rate uses only earlier games: this season so far,
pulled toward last season's rate (or replacement level for newcomers) while he has played few minutes.
A star at full minutes is worth 13-20 points of Game Score a game over his replacement; a player who
barely plays, about nothing.

Availability. For each team and game the module adds up value three ways:
    full     every player on the roster (the team at full strength)
    recent   each player weighted by the share of the team's last ten games he played (what the team
             has actually been fielding, which its Elo and form already reflect)
    tonight  each player weighted by his chance of playing tonight: from his status if the pre-game
             injury report lists him; if not, from how often he has sat out recently *without* being
             listed (a player dropped from the rotation is not on the report but won't play much)
The model's injury input is tonight - recent. A star out for two months counts as about nothing
(the team's results already show his absence); a star missing his first game counts in full; a star
returning counts as a boost. Minutes are capped at 240 a game, handed out to the best players first,
so a deep bench adds nothing while the starters are healthy and fills in when they are not.

Roster. A player belongs to the team he last played for. In the first five games of a season, last
season's players count too (until they play for someone else); after that, only players who have
played for the team this season.
"""
from collections import defaultdict, deque
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.paths import injuries_path, player_games_path

TEAM_MINUTES = 240.0
RATE_PRIOR_MINUTES = 400.0  # a season's rate counts as much as last season's after this many minutes
MINUTES_GAMES = 10  # expected minutes: recent games played, newest weighted most
MINUTES_HALF_LIFE = 4.0
PRIOR_SEASON_MIN_MINUTES = 200.0  # less than this last season and he is treated as a newcomer
REPLACEMENT_PERCENTILE = 20
REPLACEMENT_MIN_MINUTES = 500
ROTATION_MINUTES = 15.0  # play rates are measured on rotation players (see measured_play_rates)
FALLBACK_REPLACEMENT_RATE = 0.28  # typical value, for a season with too little data to measure it
PARTICIPATION_GAMES = 10
ROSTER_CARRYOVER_GAMES = 5

# Chance of playing for each injury-report status. Replaced by the rates measured in the training
# seasons (see measured_play_rates) when those are available.
DEFAULT_PLAY_RATES = {'Out': 0.0, 'Doubtful': 0.05, 'Questionable': 0.55, 'Probable': 0.95, 'Available': 1.0}


def game_score(df: pd.DataFrame) -> pd.Series:
    return (df['PTS'] + 0.4 * df['FGM'] - 0.7 * df['FGA'] - 0.4 * (df['FTA'] - df['FTM'])
            + 0.7 * df['OREB'] + 0.3 * df['DREB'] + df['STL'] + 0.7 * df['AST'] + 0.7 * df['BLK']
            - 0.4 * df['PF'] - df['TOV'])


def load_player_games(seasons: list[str]) -> pd.DataFrame:
    frames = []
    for season in seasons:
        path = player_games_path(season)
        if path.exists():
            frames.append(pd.read_csv(path, dtype={'GAME_ID': str}).assign(SEASON=season))
    df = pd.concat(frames, ignore_index=True)
    df['GMSC'] = game_score(df)
    return df


def load_injuries(seasons: list[str]) -> pd.DataFrame:
    frames = [pd.read_csv(injuries_path(s)) for s in seasons if injuries_path(s).exists()]
    if not frames:
        return pd.DataFrame(columns=['GAME_DATE', 'TEAM_ABBR', 'PLAYER_ID', 'STATUS'])
    df = pd.concat(frames, ignore_index=True).dropna(subset=['PLAYER_ID'])
    df['PLAYER_ID'] = df['PLAYER_ID'].astype(int)
    # A player listed twice for one game (rare: two reports merged) keeps his first listing
    return df.drop_duplicates(['GAME_DATE', 'TEAM_ABBR', 'PLAYER_ID'])


def replacement_rates(player_games: pd.DataFrame) -> dict[str, float]:
    totals = player_games.groupby(['SEASON', 'PLAYER_ID'])[['GMSC', 'MIN']].sum()
    regular = totals[totals['MIN'] >= REPLACEMENT_MIN_MINUTES]
    rates = regular['GMSC'] / regular['MIN']
    return rates.groupby(level='SEASON').quantile(REPLACEMENT_PERCENTILE / 100).to_dict()


def measured_play_rates(availability: pd.DataFrame) -> dict[str, float]:
    """
    Share of players listed with each status who then played, from the per-player rows. Only rotation
    players count: two-way and deep-bench players are listed too ("Available" after a G League stint)
    and often don't get in the game whatever their health, which would make every status look less
    likely to play than it is for the players who matter.
    """
    listed = availability.dropna(subset=['STATUS'])
    listed = listed[listed['EXP_MIN'] >= ROTATION_MINUTES]
    rates = listed.groupby('STATUS')['PLAYED'].mean().to_dict()
    return {status: round(rates.get(status, default), 3) for status, default in DEFAULT_PLAY_RATES.items()}


@dataclass
class _Player:
    season_gmsc: float = 0.0
    season_min: float = 0.0
    prior_rate: float | None = None
    prior_mpg: float | None = None
    recent_min: deque = field(default_factory=lambda: deque(maxlen=MINUTES_GAMES))
    team: str | None = None
    last_season_team: str | None = None


def _expected_minutes(p: _Player) -> float:
    if not p.recent_min:
        return p.prior_mpg or 0.0
    weights = 0.5 ** (np.arange(len(p.recent_min))[::-1] / MINUTES_HALF_LIFE)
    recent = float(np.dot(weights, list(p.recent_min)) / weights.sum())
    if p.prior_mpg is None or len(p.recent_min) >= 5:
        return recent
    share = len(p.recent_min) / 5
    return share * recent + (1 - share) * p.prior_mpg


def _rate(p: _Player, replacement: float) -> float:
    prior = p.prior_rate if p.prior_rate is not None else replacement
    return (p.season_gmsc + prior * RATE_PRIOR_MINUTES) / (p.season_min + RATE_PRIOR_MINUTES)


def _capped(rates: np.ndarray, minutes: np.ndarray, weights: np.ndarray) -> float:
    """Value above replacement of the minutes a team can play: the best players' minutes first, up to 240."""
    order = np.argsort(-rates)
    expected = (minutes * weights)[order]
    before = np.cumsum(expected) - expected
    kept = np.clip(TEAM_MINUTES - before, 0, expected)
    return float(np.dot(rates[order], kept))


def team_availability(
    games: pd.DataFrame,
    player_games: pd.DataFrame,
    injuries: pd.DataFrame,
    play_rates: dict[str, float] = DEFAULT_PLAY_RATES,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Walk the games in date order. Returns
      - per game: {HOME,AWAY}_{FULL,RECENT,TONIGHT,ACTUAL}_VALUE (ACTUAL uses who really played, for comparison)
      - per player and game (rostered players only): value, expected minutes, status, chance of playing,
        recent participation and whether he played
    `games` must have GAME_ID, SEASON, GAME_DATE, HOME and AWAY, sorted by date.
    """
    replacement = replacement_rates(player_games)
    by_game = {gid: g for gid, g in player_games.groupby('GAME_ID', sort=False)}
    status = {(r.GAME_DATE, r.TEAM_ABBR, r.PLAYER_ID): r.STATUS for r in injuries.itertuples(index=False)}
    listed_by_game: dict[tuple, list] = defaultdict(list)
    for key in status:
        listed_by_game[key[:2]].append(key)

    players: dict[int, _Player] = defaultdict(_Player)
    members: dict[str, set] = defaultdict(set)  # team -> players whose latest game this season was for it
    carried: dict[str, set] = defaultdict(set)  # team -> last season's players (until they play this season)
    # per team, its last games: (players who played, players listed on that game's injury report)
    team_recent: dict[str, deque] = defaultdict(lambda: deque(maxlen=PARTICIPATION_GAMES))
    team_games_this_season: dict[str, int] = defaultdict(int)
    season = None
    game_rows: dict[str, list] = defaultdict(list)
    player_rows: list[dict] = []

    for game in games.itertuples(index=False):
        if game.SEASON != season:
            _start_season(players, team_recent, team_games_this_season, season)
            carried = defaultdict(set)
            for pid, p in players.items():
                if p.last_season_team:
                    carried[p.last_season_team].add(pid)
            members = defaultdict(set)
            season = game.SEASON
        repl = replacement.get(season, float(np.mean(list(replacement.values()))) if replacement else FALLBACK_REPLACEMENT_RATE)
        box = by_game.get(game.GAME_ID)
        played_now = set(box['PLAYER_ID']) if box is not None else set()

        for side in ('HOME', 'AWAY'):
            team = game._asdict()[side]
            carry = team_games_this_season[team] < ROSTER_CARRYOVER_GAMES
            roster = list(members[team])
            if carry:
                roster += [pid for pid in carried[team] if players[pid].team is None]
            recent_sets = list(team_recent[team])
            rates, minutes, recent_w, tonight_w, actual_w = [], [], [], [], []
            for pid in roster:
                p = players[pid]
                exp_min = _expected_minutes(p)
                above = _rate(p, repl) - repl
                value = above * exp_min
                participation = (sum(pid in played for played, _ in recent_sets) / len(recent_sets)) if recent_sets else 1.0
                listed = status.get((game.GAME_DATE, team, pid))
                if listed:
                    chance = play_rates.get(listed, 1.0)
                elif recent_sets:
                    benched = sum(pid not in played and pid not in injured for played, injured in recent_sets)
                    chance = 1.0 - benched / len(recent_sets)
                else:
                    chance = 1.0
                played = pid in played_now
                rates.append(above)
                minutes.append(exp_min)
                recent_w.append(participation)
                tonight_w.append(chance)
                actual_w.append(float(played))
                player_rows.append({
                    'GAME_ID': game.GAME_ID, 'TEAM': team, 'PLAYER_ID': pid, 'VALUE': value, 'EXP_MIN': exp_min,
                    'PARTICIPATION': participation, 'STATUS': listed, 'CHANCE': chance, 'PLAYED': played,
                })
            v, m = np.array(rates), np.array(minutes)
            ones = np.ones_like(v)
            game_rows[f'{side}_FULL_VALUE'].append(_capped(v, m, ones) if len(v) else 0.0)
            game_rows[f'{side}_RECENT_VALUE'].append(_capped(v, m, np.array(recent_w)) if len(v) else 0.0)
            game_rows[f'{side}_TONIGHT_VALUE'].append(_capped(v, m, np.array(tonight_w)) if len(v) else 0.0)
            game_rows[f'{side}_ACTUAL_VALUE'].append(_capped(v, m, np.array(actual_w)) if len(v) else 0.0)
            game_rows[f'{side}_ROSTER_SIZE'].append(len(roster))

        # After the game: record who played, for whom, and their box scores
        if box is not None:
            for side in ('HOME', 'AWAY'):
                team = game._asdict()[side]
                listed_now = {pid for (day, t, pid) in listed_by_game.get((game.GAME_DATE, team), ())}
                team_recent[team].append((set(box.loc[box['TEAM_ABBREVIATION'] == team, 'PLAYER_ID']), listed_now))
                team_games_this_season[team] += 1
            for row in box.itertuples(index=False):
                p = players[row.PLAYER_ID]
                if p.team != row.TEAM_ABBREVIATION:
                    if p.team:
                        members[p.team].discard(row.PLAYER_ID)
                    members[row.TEAM_ABBREVIATION].add(row.PLAYER_ID)
                p.team = row.TEAM_ABBREVIATION
                p.season_gmsc += row.GMSC
                p.season_min += row.MIN
                p.recent_min.append(row.MIN)

    per_game = pd.concat([games[['GAME_ID']].reset_index(drop=True), pd.DataFrame(game_rows)], axis=1)
    return per_game, pd.DataFrame(player_rows)


def _start_season(players, team_recent, team_games_this_season, finished_season):
    """New season: last season's rate and minutes become priors; rosters carry over until players move."""
    for p in players.values():
        if p.season_min >= PRIOR_SEASON_MIN_MINUTES:
            p.prior_rate = p.season_gmsc / p.season_min
            p.prior_mpg = float(np.mean(p.recent_min)) if p.recent_min else p.prior_mpg
        elif finished_season is not None:
            # Barely played last season: keep an older prior only if there is one, else newcomer
            p.prior_mpg = float(np.mean(p.recent_min)) if p.recent_min else p.prior_mpg
        p.last_season_team = p.team
        p.team = None
        p.season_gmsc = p.season_min = 0.0
        p.recent_min.clear()
    team_recent.clear()
    team_games_this_season.clear()
