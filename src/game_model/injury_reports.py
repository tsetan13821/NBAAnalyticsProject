"""The official NBA injury reports: download, parse, and match players to their NBA.com ids.

    python -m src.game_model.injury_reports            # missing seasons, plus the season in progress
    python -m src.game_model.injury_reports --refresh  # every season again (PDFs come from the local cache)

The league publishes a PDF several times a day listing every player who might miss that day's games,
with a status: Out, Doubtful, Questionable, Probable or Available. They are archived at predictable
URLs back to the 2018-19 season, which lets the model train on what was known *before* each game
(the same information it gets for upcoming games) instead of who turned out to play.

For each game date this uses the 5 PM (Eastern) report, and an earlier one for games that tip off
before about 5:30 PM. One gzipped CSV per season goes to data/raw/injuries/; the PDFs are cached in
data/cache/ (not committed) so a re-parse never downloads them again.
"""
import argparse
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pdfplumber
import requests
from nba_api.stats.static import teams as static_teams

from src.game_model.seasons import configured_seasons
from src.paths import (
    GZIP,
    INJURIES_DIR,
    INJURY_PDF_CACHE,
    injuries_path,
    player_games_path,
    team_games_path,
)

BASE_URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_{stamp}.pdf"
STATUSES = ('Out', 'Doubtful', 'Questionable', 'Probable', 'Available')
EVENING_REPORT = (17, 0)  # 5 PM ET: the last report before most games
# For earlier tip-offs, the latest of these that exists and comes at least half an hour before the game.
EARLY_REPORTS = [(13, 0), (12, 0), (11, 0)]
REQUEST_PAUSE_S = 0.3
EASTERN = ZoneInfo('America/New_York')


# --- downloading ------------------------------------------------------------------------------------

def today_eastern() -> date:
    """The league's date (report and game dates are Eastern), whatever the machine's time zone: a cloud
    runner on UTC is already on tomorrow during the evening games."""
    return datetime.now(EASTERN).date()


def report_stamps(day: date, hour: int, minute: int) -> list[str]:
    """Filename stamps to try: "2025-01-15_05PM" (until 2025-26) and "2026-01-15_05_00PM" (since)."""
    h12 = hour % 12 or 12
    suffix = 'AM' if hour < 12 else 'PM'
    old = f"{day.isoformat()}_{h12:02d}{suffix}"
    new = f"{day.isoformat()}_{h12:02d}_{minute:02d}{suffix}"
    if minute:
        return [new]
    return [new, old] if day >= date(2025, 12, 1) else [old, new]


def download_report(day: date, hour: int, minute: int = 0, session: requests.Session | None = None,
                    offline: bool = False):
    """The cached PDF path for that report, or None if the league never published one (or, offline,
    if it was never downloaded)."""
    INJURY_PDF_CACHE.mkdir(parents=True, exist_ok=True)
    http = session or requests
    for stamp in report_stamps(day, hour, minute):
        path = INJURY_PDF_CACHE / f"{stamp}.pdf"
        missing = path.with_suffix('.missing')
        if path.exists():
            return path
        if missing.exists() or offline:
            continue
        response = http.get(BASE_URL.format(stamp=stamp), timeout=30)
        time.sleep(REQUEST_PAUSE_S)
        if response.status_code == 200 and response.content.startswith(b'%PDF'):
            path.write_bytes(response.content)
            return path
        if response.status_code in (403, 404):
            # Only remember a miss for days that are over: today's report may simply not be out yet.
            if day < today_eastern():
                missing.touch()
            continue
        response.raise_for_status()
    return None


# --- parsing ----------------------------------------------------------------------------------------

@dataclass
class _Columns:
    """Left edges of the report's columns, read from the header row (the layout changed over the years)."""
    starts: dict[str, float]

    def name_of(self, x: float) -> str | None:
        best = None
        for name, start in sorted(self.starts.items(), key=lambda item: item[1]):
            if x >= start - 3:
                best = name
        return best


_HEADER_KEYS = {'Matchup': 'matchup', 'Team': 'team', 'Player': 'player', 'Reason': 'reason',
                'Current': 'status', 'Previous': 'previous'}


def _find_header(words: list[dict]) -> tuple[_Columns, float] | None:
    for anchor in words:
        if anchor['text'].startswith('Matchup'):
            row = [w for w in words if abs(w['top'] - anchor['top']) < 3]
            starts = {}
            games = sorted((w for w in row if w['text'].startswith('Game')), key=lambda w: w['x0'])
            if len(games) >= 2:
                starts['date'], starts['time'] = games[0]['x0'], games[1]['x0']
            for w in row:
                key = _HEADER_KEYS.get(w['text'].split()[0])
                if key and key not in starts:
                    starts[key] = w['x0']
            if {'matchup', 'team', 'player', 'status'} <= starts.keys():
                return _Columns(starts), anchor['top']
    return None


def _lines(words: list[dict], below: float) -> list[list[dict]]:
    """Words below the header grouped into visual lines (same baseline, within a few points)."""
    lines: list[list[dict]] = []
    for w in sorted((w for w in words if w['top'] > below + 3), key=lambda w: (round(w['top']), w['x0'])):
        if lines and abs(lines[-1][0]['top'] - w['top']) < 3:
            lines[-1].append(w)
        else:
            lines.append([w])
    return lines


# First words of the reason categories ("Injury/Illness - ...", "G League - Two-Way", "Not With Team"...)
REASON_STARTS = ('Injury', 'G', 'Health', 'Not', 'Personal', 'Rest', 'Return', 'League', 'Trade', 'Concussion',
                 "Coach's", 'Ineligible', 'Team', 'Load', 'NBA', '-')


def _split_name(text: str) -> tuple[str, str]:
    """
    "Carter Jr., Wendell Injury/Illness" -> ("Carter Jr., Wendell", "Injury/Illness"): in some
    2019-20 reports the start of the reason is printed left of the Reason column and lands after
    the name. Names are "Last, First", the suffix sometimes after the comma ("Udeh, Jr., Ernest"),
    and a first name can run to two words ("Niederhauser, Yanic Konan"); the name ends where a
    reason category starts.
    """
    match = re.match(r'^([^,]+,(?:\s*(?:Jr|Sr)\.?,|\s*I{2,3},|\s*IV,)?\s*\S+)\s*(.*)$', text)
    if not match:
        return text, ''
    name, words = match.group(1), match.group(2).split()
    while words and not words[0].startswith(REASON_STARTS):
        name += ' ' + words.pop(0)
    return name, ' '.join(words)


WRAP_DISTANCE = 12.0  # points; wrapped lines sit about 7 points above and below their row's baseline


def _attach_wrapped_reasons(rows: list[dict], fragments: list[tuple]) -> None:
    """
    A long reason wraps onto lines of its own, centred on the player's row (half above it, half
    below), so a reason-only line belongs to the player row just beside it. A row at the foot of a
    page can spill its last line onto the top of the next one, above that page's first row.
    """
    pieces: dict[int, list[tuple]] = {}
    for (page, top), text in fragments:
        near = [(abs(row['at'][1] - top), i) for i, row in enumerate(rows)
                if row['at'][0] == page and abs(row['at'][1] - top) <= WRAP_DISTANCE]
        if near:
            pieces.setdefault(min(near)[1], []).append(((page, top), text))
            continue
        on_page = [row['at'][1] for row in rows if row['at'][0] == page]
        earlier = [i for i, row in enumerate(rows) if row['at'][0] < page]
        if earlier and (not on_page or top < min(on_page)):
            pieces.setdefault(earlier[-1], []).append(((page, top), text))
    for i, parts in pieces.items():
        row = rows[i]
        parts.append((row['at'], row['reason']))
        row['reason'] = ' '.join(text for _, text in sorted(parts) if text)


def parse_report(path) -> pd.DataFrame:
    """One row per listed player: game date, tip-off (ET), matchup, team name, player, status, reason."""
    rows, fragments = [], []
    context = {'date': None, 'time': None, 'matchup': None, 'team': None}
    columns = None
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages):
            # Split on every gap (no blank-merging): neighbouring columns can be one space apart,
            # and merged words would carry a reason into the player's name.
            words = page.extract_words(x_tolerance=1.5)
            header = _find_header(words)
            top = 0.0
            if header:
                columns, top = header
            if columns is None:
                continue
            for line in _lines(words, top):
                text = ' '.join(w['text'] for w in line)
                # The page title and "Page 2 of 9" footer sit in the same columns as the data.
                if 'Injury Report:' in text or re.search(r'Page\s*\d+\s*of\s*\d+', text):
                    continue
                cells: dict[str, str] = {}
                for w in line:
                    name = columns.name_of(w['x0'])
                    if name:
                        cells[name] = f"{cells.get(name, '')} {w['text']}".strip()
                if cells.get('date') and re.match(r'\d\d/\d\d/\d{4}', cells['date']):
                    context['date'] = cells['date'][:10]
                if cells.get('time') and re.match(r'\d\d:\d\d', cells['time']):
                    context['time'] = cells['time'][:5]
                if cells.get('matchup') and '@' in cells['matchup']:
                    context['matchup'] = cells['matchup'].replace(' ', '')
                if cells.get('team'):
                    context['team'] = cells['team']
                status = cells.get('status', '').split(' ')[0]
                at = (page_no, line[0]['top'])
                if cells.get('player') and status in STATUSES:
                    player, spill = _split_name(cells['player'])
                    reason = f"{spill} {cells.get('reason', '')}".strip()
                    rows.append({**context, 'player': player, 'status': status, 'reason': reason, 'at': at})
                elif set(cells) == {'reason'} and 'NOT YET SUBMITTED' not in cells['reason'].upper():
                    fragments.append((at, cells['reason']))
    _attach_wrapped_reasons(rows, fragments)
    df = pd.DataFrame(rows, columns=['date', 'time', 'matchup', 'team', 'player', 'status', 'reason'])
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y').dt.strftime('%Y-%m-%d')
    return df


# --- names --------------------------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """"Dončić, Luka" and "Luka Doncic" -> "lukadoncic"; "Pippen Jr., Scotty" -> "scottypippenjr" """
    parts = [part.strip() for part in name.split(',')]
    if len(parts) == 2:
        name = f"{parts[1]} {parts[0]}"
    elif len(parts) == 3:  # "Udeh, Jr., Ernest"
        name = f"{parts[2]} {parts[0]} {parts[1]}"
    ascii_name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z]', '', ascii_name.lower())


def team_abbreviations() -> dict[str, str]:
    """Report team names ("LA Clippers", "MemphisGrizzlies") matched on the nickname -> abbreviation."""
    return {re.sub(r'\s', '', t['nickname']).lower(): t['abbreviation'] for t in static_teams.get_teams()}


def team_abbr(name: str, nicknames: dict[str, str]) -> str | None:
    squashed = re.sub(r'\s', '', name).lower()
    for nickname, abbr in nicknames.items():
        if squashed.endswith(nickname):
            return abbr
    return None


# --- one season ----------------------------------------------------------------------------------------

def _tip_minutes(tip: str | None) -> int:
    """"07:30" (ET, 12-hour clock without AM/PM) -> minutes after midnight; games are never before 11 AM."""
    if not tip:
        return 19 * 60
    hour, minute = map(int, tip.split(':'))
    if hour < 11:
        hour += 12
    return hour * 60 + minute


def season_reports(season: str, session: requests.Session) -> pd.DataFrame:
    """Every pre-game status in a season, each from the latest report published before that game."""
    games = pd.read_csv(team_games_path(season), dtype={'GAME_ID': str})
    days = sorted(games['GAME_DATE'].unique())
    if season == configured_seasons().current:
        days = [d for d in days if d <= today_eastern().isoformat()]
    frames = []
    for i, day_text in enumerate(days, 1):
        day = date.fromisoformat(day_text)
        evening = download_report(day, *EVENING_REPORT, session=session)
        if evening is None:
            continue
        report = parse_report(evening).assign(report='17:00')
        report = report[report['date'] == day_text]
        early_games = report[report['time'].map(_tip_minutes) < 17 * 60 + 30]
        if not early_games.empty:
            report = report[~report['matchup'].isin(early_games['matchup'])]
            first_tip = early_games['time'].map(_tip_minutes).min()
            for hour, minute in EARLY_REPORTS:
                if hour * 60 + minute > first_tip - 30:
                    continue
                path = download_report(day, hour, minute, session=session)
                if path:
                    early = parse_report(path)
                    early = early[(early['date'] == day_text) & early['matchup'].isin(early_games['matchup'])]
                    report = pd.concat([report, early.assign(report=f"{hour:02d}:{minute:02d}")])
                    break
        frames.append(report)
        if i % 25 == 0:
            print(f"  {season}: {i}/{len(days)} game days")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _unique_ids(logs: pd.DataFrame) -> pd.Series:
    """Normalized name -> player id, for names that belong to exactly one player."""
    ids = logs.drop_duplicates(['key', 'PLAYER_ID']).groupby('key')['PLAYER_ID']
    return ids.first()[ids.size() == 1]


def match_players(reports: pd.DataFrame, season: str) -> pd.DataFrame:
    """
    Add TEAM_ABBR and PLAYER_ID from the game logs: the name on that team that season, else a name
    unique in that season, else a name unique in any season (players who missed the whole season,
    like a star rehabbing a torn Achilles, appear in no log that year). Names that never played an
    NBA game (two-way and G League players) stay unmatched; they have no value to lose anyway.
    """
    nicknames = team_abbreviations()
    reports = reports.copy()
    reports['TEAM_ABBR'] = reports['team'].map(lambda name: team_abbr(name, nicknames))
    reports['key'] = reports['player'].map(normalize_name)

    columns = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION']
    every = pd.concat([pd.read_csv(path, usecols=columns).assign(SEASON=path.name[13:20])
                       for path in sorted(player_games_path(season).parent.glob('player_games_*.csv.gz'))])
    every['key'] = every['PLAYER_NAME'].map(normalize_name)
    this = every[every['SEASON'] == season]
    by_team = this.drop_duplicates(['key', 'TEAM_ABBREVIATION']).set_index(['key', 'TEAM_ABBREVIATION'])['PLAYER_ID']
    in_season, anywhere = _unique_ids(this), _unique_ids(every)

    def lookup(row):
        for hit in (by_team.get((row['key'], row['TEAM_ABBR'])), in_season.get(row['key']), anywhere.get(row['key'])):
            if hit is not None:
                return hit
        return None

    reports['PLAYER_ID'] = reports.apply(lookup, axis=1).astype('Int64')
    return reports.drop(columns='key')


def build_season(season: str, session: requests.Session) -> pd.DataFrame | None:
    reports = season_reports(season, session)
    if reports.empty:
        return None
    reports = match_players(reports, season)
    reports = reports.rename(columns={'date': 'GAME_DATE', 'time': 'TIP_ET', 'matchup': 'MATCHUP',
                                      'player': 'REPORT_NAME', 'status': 'STATUS', 'reason': 'REASON',
                                      'report': 'REPORT_ET'})
    columns = ['GAME_DATE', 'TIP_ET', 'MATCHUP', 'TEAM_ABBR', 'PLAYER_ID', 'REPORT_NAME', 'STATUS', 'REASON', 'REPORT_ET']
    return reports[columns].sort_values(['GAME_DATE', 'MATCHUP', 'TEAM_ABBR', 'REPORT_NAME']).reset_index(drop=True)


def fetch_injury_reports(refresh: bool = False) -> None:
    seasons = configured_seasons()
    INJURIES_DIR.mkdir(parents=True, exist_ok=True)
    with requests.Session() as session:
        for season in seasons.injury:
            path = injuries_path(season)
            if path.exists() and not refresh and season != seasons.current:
                continue
            started = datetime.now()
            df = build_season(season, session)
            if df is None:
                print(f"  {path.name}: no reports")
                continue
            df.to_csv(path, index=False, compression=GZIP)
            unmatched = df['PLAYER_ID'].isna().mean()
            print(f"  {path.name}: {len(df):,} statuses on {df['GAME_DATE'].nunique()} days, "
                  f"{unmatched:.1%} unmatched names ({(datetime.now() - started).seconds}s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--refresh', action='store_true', help="Rebuild completed seasons too.")
    fetch_injury_reports(refresh=parser.parse_args().refresh)
