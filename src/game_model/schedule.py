"""The season's schedule, for upcoming games (tip-off times, home and away, neutral sites).

    python -m src.game_model.schedule

Writes data/raw/games/schedule_<season>.csv for the season in progress: regular-season games only
(NBA Cup knockout games whose teams are not known yet, and the play-in, are left out).
"""
import pandas as pd
from nba_api.stats.endpoints import scheduleleaguev2

from src.game_model.seasons import configured_seasons
from src.paths import schedule_path

STATUS = {1: 'scheduled', 2: 'live', 3: 'final'}


def fetch_schedule(season: str) -> pd.DataFrame:
    raw = scheduleleaguev2.ScheduleLeagueV2(season=season, league_id='00', timeout=90).get_data_frames()[0]
    raw = raw[raw['gameId'].astype(str).str.startswith('002')]
    # NBA Cup knockout games are listed before their teams are known
    raw = raw[raw['homeTeam_teamTricode'].fillna('').str.len().eq(3) & raw['awayTeam_teamTricode'].fillna('').str.len().eq(3)]
    tip = pd.to_datetime(raw['gameDateTimeEst'].str.replace('Z', '', regex=False))  # labelled Z but in ET
    df = pd.DataFrame({
        'GAME_ID': raw['gameId'].astype(str),
        'GAME_DATE': tip.dt.strftime('%Y-%m-%d'),
        'TIP_ET': tip.dt.strftime('%H:%M'),
        'HOME': raw['homeTeam_teamTricode'],
        'AWAY': raw['awayTeam_teamTricode'],
        'NEUTRAL_SITE': raw['isNeutral'].astype(bool),
        'STATUS': raw['gameStatus'].map(STATUS),
    })
    return df.sort_values(['GAME_DATE', 'TIP_ET', 'GAME_ID']).reset_index(drop=True)


def main():
    season = configured_seasons().current
    if not season:
        print("No season in progress; no schedule to fetch.")
        return
    df = fetch_schedule(season)
    df.to_csv(schedule_path(season), index=False)
    print(f"Saved {len(df):,} games ({(df['STATUS'] != 'final').sum()} still to play) to {schedule_path(season)}")


if __name__ == "__main__":
    main()
