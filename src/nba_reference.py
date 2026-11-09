"""Static NBA reference data shared by the pipelines, models and dashboard."""
import unicodedata

# Regular-season MVP by season. 1999-00 is included so the "won last year"
# feature works for the first season in the dataset.
MVP_WINNERS = {
    '1999-00': "Shaquille O'Neal",
    '2000-01': 'Allen Iverson',
    '2001-02': 'Tim Duncan',
    '2002-03': 'Tim Duncan',
    '2003-04': 'Kevin Garnett',
    '2004-05': 'Steve Nash',
    '2005-06': 'Steve Nash',
    '2006-07': 'Dirk Nowitzki',
    '2007-08': 'Kobe Bryant',
    '2008-09': 'LeBron James',
    '2009-10': 'LeBron James',
    '2010-11': 'Derrick Rose',
    '2011-12': 'LeBron James',
    '2012-13': 'LeBron James',
    '2013-14': 'Kevin Durant',
    '2014-15': 'Stephen Curry',
    '2015-16': 'Stephen Curry',
    '2016-17': 'Russell Westbrook',
    '2017-18': 'James Harden',
    '2018-19': 'Giannis Antetokounmpo',
    '2019-20': 'Giannis Antetokounmpo',
    '2020-21': 'Nikola Jokić',
    '2021-22': 'Nikola Jokić',
    '2022-23': 'Joel Embiid',
    '2023-24': 'Nikola Jokić',
    '2024-25': 'Shai Gilgeous-Alexander',
    '2025-26': 'Shai Gilgeous-Alexander',
}

# NBA champion by season, keyed by current franchise abbreviation.
CHAMPIONS = {
    '2000-01': 'LAL', '2001-02': 'LAL', '2002-03': 'SAS', '2003-04': 'DET',
    '2004-05': 'SAS', '2005-06': 'MIA', '2006-07': 'SAS', '2007-08': 'BOS',
    '2008-09': 'LAL', '2009-10': 'LAL', '2010-11': 'DAL', '2011-12': 'MIA',
    '2012-13': 'MIA', '2013-14': 'SAS', '2014-15': 'GSW', '2015-16': 'CLE',
    '2016-17': 'GSW', '2017-18': 'GSW', '2018-19': 'TOR', '2019-20': 'LAL',
    '2020-21': 'MIL', '2021-22': 'GSW', '2022-23': 'DEN', '2023-24': 'BOS',
    '2024-25': 'OKC', '2025-26': 'NYK',
}

# Historical team abbreviations used in player stats -> current franchise abbreviation
# (the abbreviation nba_api's static team list and the standings endpoint use).
FRANCHISE_ABBREVIATIONS = {
    'SEA': 'OKC',  # Seattle SuperSonics -> Oklahoma City Thunder (2008)
    'NJN': 'BKN',  # New Jersey Nets -> Brooklyn Nets (2012)
    'NOH': 'NOP',  # New Orleans Hornets -> Pelicans (2013)
    'NOK': 'NOP',  # New Orleans/Oklahoma City Hornets (2005-07)
    'VAN': 'MEM',  # Vancouver Grizzlies -> Memphis (2001)
    'CHH': 'CHA',  # Charlotte Hornets 1988-2002 history belongs to today's Charlotte franchise
}

# Primary / secondary brand colors per current franchise (approximate hex values for UI accents).
TEAM_COLORS = {
    'ATL': ('#E03A3E', '#C1D32F'), 'BOS': ('#007A33', '#BA9653'), 'BKN': ('#000000', '#FFFFFF'),
    'CHA': ('#1D1160', '#00788C'), 'CHI': ('#CE1141', '#000000'), 'CLE': ('#860038', '#FDBB30'),
    'DAL': ('#00538C', '#002B5E'), 'DEN': ('#0E2240', '#FEC524'), 'DET': ('#C8102E', '#1D42BA'),
    'GSW': ('#1D428A', '#FFC72C'), 'HOU': ('#CE1141', '#000000'), 'IND': ('#002D62', '#FDBB30'),
    'LAC': ('#C8102E', '#1D428A'), 'LAL': ('#552583', '#FDB927'), 'MEM': ('#5D76A9', '#12173F'),
    'MIA': ('#98002E', '#F9A01B'), 'MIL': ('#00471B', '#EEE1C6'), 'MIN': ('#0C2340', '#236192'),
    'NOP': ('#0C2340', '#C8102E'), 'NYK': ('#006BB6', '#F58426'), 'OKC': ('#007AC1', '#EF3B24'),
    'ORL': ('#0077C0', '#C4CED4'), 'PHI': ('#006BB6', '#ED174C'), 'PHX': ('#1D1160', '#E56020'),
    'POR': ('#E03A3E', '#000000'), 'SAC': ('#5A2D81', '#63727A'), 'SAS': ('#C4CED4', '#000000'),
    'TOR': ('#CE1141', '#000000'), 'UTA': ('#002B5C', '#F9A01B'), 'WAS': ('#002B5C', '#E31837'),
}

CONFERENCES = {
    'East': {'ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE', 'DET', 'IND', 'MIA', 'MIL', 'NYK', 'ORL', 'PHI', 'TOR', 'WAS'},
    'West': {'DAL', 'DEN', 'GSW', 'HOU', 'LAC', 'LAL', 'MEM', 'MIN', 'NOP', 'OKC', 'PHX', 'POR', 'SAC', 'SAS', 'UTA'},
}


def franchise_abbreviation(team_abbr):
    """Map a historical team abbreviation to its current franchise abbreviation."""
    return FRANCHISE_ABBREVIATIONS.get(team_abbr, team_abbr)


# The New Orleans Hornets played in the East for their first two seasons.
_CONFERENCE_EXCEPTIONS = {
    ('NOH', '2002-03'): 'East',
    ('NOH', '2003-04'): 'East',
}


def get_conference(team_abbr, season=None):
    """Return 'East', 'West' or 'Unknown' for a current or historical abbreviation."""
    if (team_abbr, season) in _CONFERENCE_EXCEPTIONS:
        return _CONFERENCE_EXCEPTIONS[(team_abbr, season)]
    franchise = franchise_abbreviation(team_abbr)
    for conference, members in CONFERENCES.items():
        if franchise in members:
            return conference
    return 'Unknown'


def normalize_name(name):
    """Strip accents and surrounding whitespace so 'Nikola Jokić' == 'Nikola Jokic'."""
    decomposed = unicodedata.normalize('NFKD', str(name).strip())
    return ''.join(ch for ch in decomposed if not unicodedata.combining(ch))


def previous_season(season):
    """'2010-11' -> '2009-10'."""
    start_year = int(season.split('-')[0]) - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"
