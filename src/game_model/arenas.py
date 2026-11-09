"""Where each team plays: arena coordinates and standard-time UTC offset, for travel and time-zone features.

Current arenas. Moves since 2015 stayed within the same city (the Warriors from Oakland to San
Francisco, the Clippers to Inglewood), a few kilometres that make no difference to travel fatigue.
"""
import math

# abbreviation: (latitude, longitude, UTC offset in standard time)
ARENAS: dict[str, tuple[float, float, int]] = {
    'ATL': (33.757, -84.396, -5), 'BKN': (40.683, -73.975, -5), 'BOS': (42.366, -71.062, -5),
    'CHA': (35.225, -80.839, -5), 'CHI': (41.881, -87.674, -6), 'CLE': (41.496, -81.688, -5),
    'DAL': (32.790, -96.810, -6), 'DEN': (39.749, -105.008, -7), 'DET': (42.341, -83.055, -5),
    'GSW': (37.768, -122.388, -8), 'HOU': (29.751, -95.362, -6), 'IND': (39.764, -86.156, -5),
    'LAC': (33.945, -118.343, -8), 'LAL': (34.043, -118.267, -8), 'MEM': (35.138, -90.051, -6),
    'MIA': (25.781, -80.188, -5), 'MIL': (43.045, -87.917, -6), 'MIN': (44.979, -93.276, -6),
    'NOP': (29.949, -90.082, -6), 'NYK': (40.751, -73.993, -5), 'OKC': (35.463, -97.515, -6),
    'ORL': (28.539, -81.384, -5), 'PHI': (39.901, -75.172, -5), 'PHX': (33.446, -112.071, -7),
    'POR': (45.532, -122.667, -8), 'SAC': (38.580, -121.500, -8), 'SAS': (29.427, -98.438, -6),
    'TOR': (43.643, -79.379, -5), 'UTA': (40.768, -111.901, -7), 'WAS': (38.898, -77.021, -5),
}


def distance_km(a: str, b: str) -> float:
    """Great-circle distance between two teams' arenas."""
    lat1, lon1, _ = ARENAS[a]
    lat2, lon2, _ = ARENAS[b]
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def tz_shift(a: str, b: str) -> int:
    """Hours of clock change travelling from a's arena to b's (positive = eastward, the harder way)."""
    return ARENAS[b][2] - ARENAS[a][2]
