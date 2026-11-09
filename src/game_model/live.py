"""Predictions for the season in progress: every game played so far (as predicted before it) and the
upcoming week, from the latest data.

    python -m src.game_model.live              # refresh this season's games, schedule and injury reports first
    python -m src.game_model.live --no-fetch   # use what is already downloaded (no network at all)

Upcoming games run through exactly the same code as the training games (src.game_model.games and
.availability): they get every pre-game input, from the latest results, without updating anything.
Their injury statuses come from the latest official report; games further ahead than the report
covers, and teams that haven't submitted yet, carry the team's latest Out and Doubtful players forward
(an injured player usually stays out a few days). Run it again closer to tip-off for fresher statuses;
.github/workflows/refresh-games.yml does that on a schedule. A download that fails (NBA.com is often
slow, or blocks cloud servers) is reported and skipped, and the run carries on with the files on disk.

Writes:
    data/processed/game_predictions.csv     this season's games: inputs, predicted margin and win
                                            chance, and the result once played
    data/processed/game_players.csv         each rostered player in those games: value, usual minutes,
                                            injury status and chance of playing (for what-if changes)
    data/processed/live_meta.json           when the data and the injury report are from
"""
import argparse
import json
from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.game_model.availability import (
    load_injuries,
    load_player_games,
    team_availability,
)
from src.game_model.features import add_features
from src.game_model.fetch_games import fetch_games
from src.game_model.games import add_team_state, load_team_games, to_games
from src.game_model.injury_reports import (
    download_report,
    fetch_injury_reports,
    match_players,
    parse_report,
)
from src.game_model.predict import load_model, predict
from src.game_model.schedule import fetch_schedule
from src.game_model.seasons import configured_seasons
from src.paths import (
    GAME_PLAYERS,
    GAME_PREDICTIONS,
    LIVE_META,
    injuries_path,
    player_games_path,
    schedule_path,
)

HORIZON_DAYS = 7
REPORT_LOOKBACK_HOURS = 18
CARRIED_STATUSES = ('Out', 'Doubtful')


def now_eastern() -> pd.Timestamp:
    return pd.Timestamp.now(tz='America/New_York')


def latest_report(now: pd.Timestamp, offline: bool = False):
    """The most recent injury report published by `now` (reports come every 15 minutes in 2026-27)."""
    slot = now.floor('15min')
    for _ in range(REPORT_LOOKBACK_HOURS * 4):
        path = download_report(slot.date(), slot.hour, slot.minute, offline=offline)
        if path:
            return path, slot
        slot -= pd.Timedelta(minutes=15)
    return None, None


def upcoming_games(season: str, played_ids: set[str], today: date) -> pd.DataFrame:
    schedule = pd.read_csv(schedule_path(season), dtype={'GAME_ID': str})
    end = (today + timedelta(days=HORIZON_DAYS)).isoformat()
    ahead = schedule[~schedule['GAME_ID'].isin(played_ids) & (schedule['STATUS'] != 'final')
                     & (schedule['GAME_DATE'] >= today.isoformat()) & (schedule['GAME_DATE'] < end)]
    return ahead.assign(SEASON=season, HOME_PTS=np.nan, AWAY_PTS=np.nan, MARGIN=np.nan, POSS=np.nan,
                        HOME_WIN=np.nan, BUBBLE=False, REDUCED_CROWD=False)


LISTING_COLUMNS = ['GAME_DATE', 'TEAM_ABBR', 'PLAYER_ID', 'STATUS', 'REASON']


def upcoming_statuses(report: pd.DataFrame, archive: pd.DataFrame, games: pd.DataFrame,
                      played: pd.DataFrame) -> pd.DataFrame:
    """
    Statuses for upcoming games. Where a report lists the team for that game (the latest one, else an
    earlier one archived today), those statuses. Otherwise (a game further ahead, or a team whose entry
    still says NOT YET SUBMITTED) the Out and Doubtful players from the team's most recent listing are
    carried forward. Deciding per team, not per date, matters: a team that hasn't submitted yet would
    otherwise have nobody listed, and a star out for weeks would count as playing.

    A team with nobody injured isn't in the report at all, so a listing is only carried forward if the
    team hasn't played since (`played`: games already played, with GAME_DATE, HOME and AWAY).
    """
    submitted = set(zip(report['GAME_DATE'], report['TEAM_ABBR'], strict=True))
    earlier = archive[[(d, t) not in submitted for d, t in zip(archive['GAME_DATE'], archive['TEAM_ABBR'], strict=True)]]
    history = pd.concat([earlier[LISTING_COLUMNS], report[LISTING_COLUMNS]], ignore_index=True)
    by_listing = {key: rows for key, rows in history.groupby(['GAME_DATE', 'TEAM_ABBR'])}
    days_by_team = history.groupby('TEAM_ABBR')['GAME_DATE'].unique().to_dict()
    last_played = pd.concat([played[['GAME_DATE', 'HOME']].rename(columns={'HOME': 'TEAM'}),
                             played[['GAME_DATE', 'AWAY']].rename(columns={'AWAY': 'TEAM'})]
                            ).groupby('TEAM')['GAME_DATE'].max().to_dict()

    rows = []
    for game in games.itertuples(index=False):
        for team in (game.HOME, game.AWAY):
            listed = by_listing.get((game.GAME_DATE, team))
            source = 'report'
            if listed is None:
                before = [day for day in days_by_team.get(team, []) if day < game.GAME_DATE]
                if not before or max(before) < last_played.get(team, ''):
                    continue
                listed = by_listing[(max(before), team)]
                listed = listed[listed['STATUS'].isin(CARRIED_STATUSES)]
                source = 'carried'
            for r in listed.itertuples(index=False):
                rows.append({'GAME_DATE': game.GAME_DATE, 'TEAM_ABBR': team, 'PLAYER_ID': int(r.PLAYER_ID),
                             'STATUS': r.STATUS, 'REASON': r.REASON, 'STATUS_SOURCE': source})
    return pd.DataFrame(rows, columns=[*LISTING_COLUMNS, 'STATUS_SOURCE'])


def _fetch_step(name: str, step) -> str | None:
    """Run one download; on failure (NBA.com is often slow or blocks cloud servers) keep the data on disk."""
    try:
        step()
        return None
    except Exception as error:  # noqa: BLE001 - any failure: carry on with what is on disk
        print(f"  {name} failed, using the data on disk: {error}")
        return name


def _player_names(seasons: list[str]) -> pd.DataFrame:
    """Latest spelling of every name (a player rostered from last season may not have played this one yet)."""
    frames = [pd.read_csv(player_games_path(s), usecols=['PLAYER_ID', 'PLAYER_NAME']) for s in seasons
              if player_games_path(s).exists()]
    return pd.concat(frames).drop_duplicates('PLAYER_ID', keep='last')


def _reasons(season: str, statuses: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Injury reason and where the status came from: the archive for played games, the live report ahead."""
    columns = ['GAME_ID', 'TEAM', 'PLAYER_ID', 'REASON', 'STATUS_SOURCE']
    sides = pd.concat([games[['GAME_ID', 'GAME_DATE', 'HOME']].rename(columns={'HOME': 'TEAM'}),
                       games[['GAME_ID', 'GAME_DATE', 'AWAY']].rename(columns={'AWAY': 'TEAM'})])
    frames = []
    if injuries_path(season).exists():
        archive = pd.read_csv(injuries_path(season)).dropna(subset=['PLAYER_ID']).assign(STATUS_SOURCE='report')
        frames.append(archive[['GAME_DATE', 'TEAM_ABBR', 'PLAYER_ID', 'REASON', 'STATUS_SOURCE']])
    frames.append(statuses[['GAME_DATE', 'TEAM_ABBR', 'PLAYER_ID', 'REASON', 'STATUS_SOURCE']])
    listed = pd.concat(frames, ignore_index=True).rename(columns={'TEAM_ABBR': 'TEAM'})
    listed['PLAYER_ID'] = listed['PLAYER_ID'].astype(int)
    listed = listed.drop_duplicates(['GAME_DATE', 'TEAM', 'PLAYER_ID'], keep='last')
    return sides.merge(listed, on=['GAME_DATE', 'TEAM'])[columns]


def build_live(fetch: bool = True) -> dict:
    seasons = configured_seasons()
    season = seasons.current
    if not season:
        print("No season in progress: nothing to predict.")
        return {}
    failed = []
    if fetch:
        failed = [name for name, step in (
            ('game logs', fetch_games),
            ('schedule', lambda: fetch_schedule(season).to_csv(schedule_path(season), index=False)),
            ('injury report archive', fetch_injury_reports),
        ) if _fetch_step(name, step)]

    now = now_eastern()
    today = now.date()
    try:
        report_path, report_time = latest_report(now, offline=not fetch)
    except Exception as error:  # noqa: BLE001 - fall back to the latest report already downloaded
        print(f"  latest injury report failed, using the latest one on disk: {error}")
        failed.append('latest injury report')
        report_path, report_time = latest_report(now, offline=True)
    report = pd.DataFrame(columns=LISTING_COLUMNS)
    if report_path:
        parsed = parse_report(report_path)
        parsed['report'] = report_time.strftime('%H:%M')
        report = match_players(parsed, season).rename(columns={'date': 'GAME_DATE', 'status': 'STATUS', 'reason': 'REASON'})
        report = report.dropna(subset=['PLAYER_ID'])
    archive = pd.DataFrame(columns=LISTING_COLUMNS)
    if injuries_path(season).exists():
        archive = pd.read_csv(injuries_path(season)).dropna(subset=['PLAYER_ID'])

    played = to_games(load_team_games(seasons.team))
    ahead = upcoming_games(season, set(played['GAME_ID']), today)
    games = pd.concat([played, ahead.drop(columns=['TIP_ET', 'STATUS'])], ignore_index=True)
    games = games.sort_values(['GAME_DATE', 'GAME_ID']).reset_index(drop=True)
    games = add_team_state(games)
    games = games[games['SEASON'].isin(seasons.player)].reset_index(drop=True)

    statuses = upcoming_statuses(report, archive, ahead, played)
    injuries = pd.concat([load_injuries(seasons.injury), statuses[['GAME_DATE', 'TEAM_ABBR', 'PLAYER_ID', 'STATUS']]],
                         ignore_index=True)
    # A live status replaces the archived one for the same game (the archive only has earlier reports)
    injuries = injuries.drop_duplicates(['GAME_DATE', 'TEAM_ABBR', 'PLAYER_ID'], keep='last')

    model = load_model()
    per_game, per_player = team_availability(games, load_player_games(seasons.player), injuries, model['play_rates'])
    df = add_features(games.merge(per_game, on='GAME_ID'))
    df = df[df['SEASON'] == season].copy()
    df['PRED_MARGIN'], df['HOME_WIN_PROB'] = predict(df, model)
    df = df.merge(ahead[['GAME_ID', 'TIP_ET']], on='GAME_ID', how='left')
    df['PLAYED'] = df['MARGIN'].notna()

    keep = ['GAME_ID', 'SEASON', 'GAME_DATE', 'TIP_ET', 'HOME', 'AWAY', 'PLAYED', 'HOME_PTS', 'AWAY_PTS', 'MARGIN', 'HOME_WIN',
            'PRED_MARGIN', 'HOME_WIN_PROB', *model['features'], 'HOME_ELO', 'AWAY_ELO', 'HOME_GP', 'AWAY_GP',
            'HOME_WIN_PCT', 'AWAY_WIN_PCT', 'HOME_RECENT_VALUE', 'AWAY_RECENT_VALUE',
            'HOME_TONIGHT_VALUE', 'AWAY_TONIGHT_VALUE']
    df[keep].to_csv(GAME_PREDICTIONS, index=False)

    players = per_player[per_player['GAME_ID'].isin(df['GAME_ID'])].copy()
    players['RATE_ABOVE'] = np.where(players['EXP_MIN'] > 0, players['VALUE'] / players['EXP_MIN'].replace(0, np.nan), 0.0)
    players = players.merge(_player_names(seasons.player), on='PLAYER_ID', how='left')
    players = players.merge(_reasons(season, statuses, df), on=['GAME_ID', 'TEAM', 'PLAYER_ID'], how='left')
    players = players.sort_values(['GAME_ID', 'TEAM', 'VALUE'], ascending=[True, True, False])
    players.to_csv(GAME_PLAYERS, index=False)

    played_now = df[df['PLAYED']]
    meta = {
        'season': season,
        'as_of': now.isoformat(timespec='minutes'),
        'last_game_date': played_now['GAME_DATE'].max() if len(played_now) else None,
        'injury_report': report_time.isoformat(timespec='minutes') if report_time is not None else None,
        'games_played': len(played_now),
        'correct_so_far': int(((played_now['HOME_WIN_PROB'] >= 0.5) == (played_now['HOME_WIN'] == 1)).sum()),
        'upcoming_games': int((~df['PLAYED']).sum()),
        'fetch_failed': failed,
    }
    LIVE_META.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"{meta['games_played']} games played this season, {meta['correct_so_far']} called correctly; "
          f"{meta['upcoming_games']} upcoming games predicted (injury report {meta['injury_report']})")
    return meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--no-fetch', action='store_true', help="Don't download anything; use the files on disk.")
    build_live(fetch=not parser.parse_args().no_fetch)
