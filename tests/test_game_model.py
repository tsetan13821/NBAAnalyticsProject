"""The game predictor's building blocks, on small hand-made inputs (no API calls, no downloads)."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.game_model.arenas import ARENAS, distance_km, tz_shift
from src.game_model.availability import _capped, game_score, team_availability
from src.game_model.features import FEATURES, add_features
from src.game_model.games import ELO_START, add_team_state
from src.game_model.injury_reports import (
    _attach_wrapped_reasons,
    _split_name,
    _tip_minutes,
    normalize_name,
    report_stamps,
    team_abbr,
    team_abbreviations,
)
from src.game_model.live import upcoming_statuses
from src.game_model.predict import predict, win_probability
from src.game_model.seasons import season_from_id, season_label, seasons_between
from src.game_model.train import calibration


def game(gid, day, home, away, margin, season="2024-25", poss=100.0):
    played = margin is not None
    return {
        'GAME_ID': gid, 'SEASON': season, 'GAME_DATE': day, 'HOME': home, 'AWAY': away,
        'HOME_PTS': 100 + margin if played else np.nan, 'AWAY_PTS': 100.0 if played else np.nan,
        'MARGIN': margin if played else np.nan, 'POSS': poss if played else np.nan,
        'HOME_WIN': (int(margin > 0) if played else np.nan),
        'NEUTRAL_SITE': False, 'BUBBLE': False, 'REDUCED_CROWD': False,
    }


# --- seasons and places ---------------------------------------------------------------------------

def test_season_labels():
    assert season_label(2024) == "2024-25"
    assert season_label(1999) == "1999-00"
    assert seasons_between("2023-24", "2025-26") == ["2023-24", "2024-25", "2025-26"]
    assert season_from_id(22024) == "2024-25"


def test_arenas_cover_every_team_and_measure_sensibly():
    assert len(ARENAS) == 30
    assert distance_km('LAL', 'LAC') < 30
    assert 3900 < distance_km('BOS', 'LAL') < 4300
    assert distance_km('NYK', 'MIA') == pytest.approx(distance_km('MIA', 'NYK'))
    assert tz_shift('LAL', 'BOS') == 3  # flying east
    assert tz_shift('BOS', 'LAL') == -3


# --- injury reports ---------------------------------------------------------------------------------

def test_report_stamps_follow_the_filename_eras():
    assert report_stamps(date(2025, 1, 15), 17, 0) == ["2025-01-15_05PM", "2025-01-15_05_00PM"]
    assert report_stamps(date(2026, 1, 15), 17, 0) == ["2026-01-15_05_00PM", "2026-01-15_05PM"]
    assert report_stamps(date(2026, 11, 9), 13, 30) == ["2026-11-09_01_30PM"]
    assert report_stamps(date(2026, 11, 9), 11, 0)[0] == "2026-11-09_11_00AM"


def test_names_from_the_report_match_names_from_the_logs():
    assert normalize_name("Dončić, Luka") == normalize_name("Luka Doncic") == "lukadoncic"
    assert normalize_name("Pippen Jr., Scotty") == normalize_name("Scotty Pippen Jr.")
    assert _split_name("Carter Jr., Wendell Injury/Illness") == ("Carter Jr., Wendell", "Injury/Illness")
    assert _split_name("Gilgeous-Alexander, Shai") == ("Gilgeous-Alexander, Shai", "")
    assert _split_name("Udeh, Jr., Ernest") == ("Udeh, Jr., Ernest", "")
    assert _split_name("Niederhauser, Yanic Konan") == ("Niederhauser, Yanic Konan", "")
    assert _split_name("Butler Jr., John G League") == ("Butler Jr., John", "G League")
    assert normalize_name("Udeh, Jr., Ernest") == normalize_name("Ernest Udeh Jr.")


def test_a_wrapped_reason_joins_the_nearest_player_row():
    # Reasons too long for the column wrap onto lines of their own, centred on the player's row
    rows = [{'player': 'Diop, Khalifa', 'reason': 'G League - On Assignment', 'at': (0, 100.0)},
            {'player': 'Merrill, Sam', 'reason': '', 'at': (0, 120.0)},
            {'player': 'Tomlin, Nae', 'reason': '', 'at': (0, 140.0)},
            {'player': 'Hall, PJ', 'reason': 'G League - Two-Way', 'at': (1, 125.0)}]
    fragments = [((0, 115.0), 'Right Elbow'), ((0, 125.0), 'Management'),
                 ((0, 135.0), 'Low Back Stress'), ((0, 145.0), 'Reaction'),
                 ((1, 90.0), 'Rehab')]  # the top of the next page: the end of the last row's reason
    _attach_wrapped_reasons(rows, fragments)
    assert [r['reason'] for r in rows] == ['G League - On Assignment', 'Right Elbow Management',
                                           'Low Back Stress Reaction Rehab', 'G League - Two-Way']


def test_team_names_from_the_report():
    nicknames = team_abbreviations()
    assert team_abbr("LA Clippers", nicknames) == "LAC"
    assert team_abbr("MemphisGrizzlies", nicknames) == "MEM"
    assert team_abbr("Portland Trail Blazers", nicknames) == "POR"
    assert team_abbr("Injury Report:", nicknames) is None


def test_tip_times_are_read_on_a_12_hour_clock():
    assert _tip_minutes("07:30") == 19 * 60 + 30
    assert _tip_minutes("12:00") == 12 * 60
    assert _tip_minutes("01:00") == 13 * 60


# --- team state ------------------------------------------------------------------------------------

def test_team_state_uses_only_earlier_games():
    games = pd.DataFrame([
        game('1', '2024-11-01', 'BOS', 'NYK', 20),
        game('2', '2024-11-02', 'BOS', 'LAL', -5),
        game('3', '2024-11-03', 'NYK', 'BOS', None),  # not played yet
    ])
    out = add_team_state(games)
    first, second, upcoming = out.iloc[0], out.iloc[1], out.iloc[2]
    # Before its first game nobody has a record or a rating edge
    assert first['HOME_ELO'] == first['AWAY_ELO'] == ELO_START
    assert first['HOME_GP'] == 0 and first['HOME_NET'] == 0
    # The win moved Elo before the second game, and Boston is on a back-to-back
    assert second['HOME_ELO'] > ELO_START
    assert second['HOME_GP'] == 1 and second['HOME_WIN_PCT'] == 1.0
    assert second['HOME_B2B'] == 1 and second['HOME_REST'] == 1
    assert second['HOME_NET'] > 0
    # The upcoming game sees both results; Boston travels from its own arena to New York
    assert upcoming['AWAY_GP'] == 2 and upcoming['AWAY_WIN_PCT'] == 0.5
    assert upcoming['AWAY_B2B'] == 1 and upcoming['AWAY_3IN4'] == 1
    assert upcoming['AWAY_TRAVEL_KM'] == pytest.approx(distance_km('BOS', 'NYK'))


def test_an_unplayed_game_changes_no_ratings():
    played = pd.DataFrame([game('1', '2024-11-01', 'BOS', 'NYK', 20), game('2', '2024-11-05', 'NYK', 'BOS', 3)])
    with_upcoming = pd.DataFrame([game('1', '2024-11-01', 'BOS', 'NYK', 20), game('x', '2024-11-03', 'BOS', 'NYK', None),
                                  game('2', '2024-11-05', 'NYK', 'BOS', 3)])
    a = add_team_state(played).iloc[1]
    b = add_team_state(with_upcoming).iloc[2]
    assert a['HOME_ELO'] == b['HOME_ELO'] and a['HOME_NET'] == b['HOME_NET']


def test_elo_regresses_toward_average_between_seasons():
    games = pd.DataFrame([game(str(i), f'2024-11-{i + 1:02d}', 'BOS', 'NYK', 25) for i in range(5)]
                         + [game('n', '2025-10-25', 'BOS', 'NYK', 1, season='2025-26')])
    out = add_team_state(games)
    end_of_season = out.iloc[4]['HOME_ELO']
    assert ELO_START < out.iloc[5]['HOME_ELO'] < end_of_season
    assert out.iloc[5]['HOME_GP'] == 0  # records start again


# --- player value and availability -------------------------------------------------------------------

def test_game_score():
    line = pd.DataFrame([{'PTS': 30, 'FGM': 11, 'FGA': 20, 'FTM': 6, 'FTA': 7, 'OREB': 1, 'DREB': 7,
                          'AST': 8, 'STL': 2, 'BLK': 1, 'PF': 2, 'TOV': 3}])
    assert game_score(line).iloc[0] == pytest.approx(30 + 4.4 - 14 - 0.4 + 0.7 + 2.1 + 2 + 5.6 + 0.7 - 0.8 - 3)


def test_minutes_go_to_the_best_players_first():
    rates = np.array([0.5, 0.1, 0.0])
    minutes = np.array([200.0, 100.0, 100.0])
    # 240 minutes: 200 of the best player's, 40 of the next
    assert _capped(rates, minutes, np.ones(3)) == pytest.approx(0.5 * 200 + 0.1 * 40)
    # Without the best player, the others fill in
    assert _capped(rates, minutes, np.array([0.0, 1.0, 1.0])) == pytest.approx(0.1 * 100)


def _box(gid, day, team, rows):
    return [{'GAME_ID': gid, 'GAME_DATE': day, 'TEAM_ABBREVIATION': team, 'PLAYER_ID': pid, 'MIN': minutes,
             'GMSC': gmsc, 'SEASON': '2024-25'} for pid, minutes, gmsc in rows]


def test_a_fresh_injury_counts_and_a_long_one_does_not():
    # Team A: star 1 (great), role player 2. Star 3 has been out all along.
    # Team B: two average players. Games 1-3 played, game 4 upcoming.
    games = pd.DataFrame([game(str(i), f'2024-11-0{i}', 'AAA', 'BBB', 5) for i in (1, 2, 3)]
                         + [game('4', '2024-11-04', 'AAA', 'BBB', None)])
    box = []
    for i in (1, 2, 3):
        box += _box(str(i), f'2024-11-0{i}', 'AAA', [(1, 36, 30), (2, 30, 10)] + ([(3, 30, 20)] if i == 1 else []))
        box += _box(str(i), f'2024-11-0{i}', 'BBB', [(10, 34, 12), (11, 34, 12)])
    players = pd.DataFrame(box)
    no_report = pd.DataFrame(columns=['GAME_DATE', 'TEAM_ABBR', 'PLAYER_ID', 'STATUS'])

    healthy, _ = team_availability(games, players, no_report)
    star_out = pd.DataFrame([{'GAME_DATE': '2024-11-04', 'TEAM_ABBR': 'AAA', 'PLAYER_ID': 1, 'STATUS': 'Out'}])
    hurt, per_player = team_availability(games, players, star_out)

    upcoming_healthy, upcoming_hurt = healthy.iloc[3], hurt.iloc[3]
    # Player 3 missed the last games: what the team has fielded lately is below its full strength
    assert upcoming_healthy['HOME_RECENT_VALUE'] < upcoming_healthy['HOME_FULL_VALUE']
    # Tonight with the star listed out: much less available than recently fielded
    assert upcoming_hurt['HOME_TONIGHT_VALUE'] < upcoming_hurt['HOME_RECENT_VALUE'] - 3
    # Nobody listed: tonight's lineup is what the team has been fielding
    assert upcoming_healthy['HOME_TONIGHT_VALUE'] == pytest.approx(upcoming_healthy['HOME_RECENT_VALUE'])
    upcoming = per_player[per_player['GAME_ID'] == '4'].set_index('PLAYER_ID')
    assert upcoming.loc[1, 'STATUS'] == 'Out' and upcoming.loc[1, 'CHANCE'] == 0.0
    assert upcoming.loc[1, 'PARTICIPATION'] == 1.0
    # Player 3 sat out two games without being listed (a coach's decision): he isn't counted on tonight
    assert upcoming.loc[3, 'CHANCE'] == pytest.approx(1 / 3)


def test_a_player_back_from_a_listed_injury_counts_in_full():
    games = pd.DataFrame([game(str(i), f'2024-11-0{i}', 'AAA', 'BBB', 5) for i in (1, 2, 3)]
                         + [game('4', '2024-11-04', 'AAA', 'BBB', None)])
    box = []
    for i in (1, 2, 3):
        box += _box(str(i), f'2024-11-0{i}', 'AAA', [(2, 30, 10)] + ([(1, 36, 30)] if i == 1 else []))
        box += _box(str(i), f'2024-11-0{i}', 'BBB', [(10, 34, 12)])
    listed = pd.DataFrame([{'GAME_DATE': f'2024-11-0{i}', 'TEAM_ABBR': 'AAA', 'PLAYER_ID': 1, 'STATUS': 'Out'} for i in (2, 3)])
    per_game, per_player = team_availability(games, pd.DataFrame(box), listed)
    star = per_player[(per_player['GAME_ID'] == '4') & (per_player['PLAYER_ID'] == 1)].iloc[0]
    assert star['CHANCE'] == 1.0 and star['PARTICIPATION'] == pytest.approx(1 / 3)
    assert per_game.iloc[3]['HOME_TONIGHT_VALUE'] > per_game.iloc[3]['HOME_RECENT_VALUE']  # his return is a boost


# --- features, prediction, evaluation ----------------------------------------------------------------

def test_features_are_home_minus_away():
    row = {
        'HOME_ELO': 1600, 'AWAY_ELO': 1544, 'BUBBLE': False, 'NEUTRAL_SITE': False, 'REDUCED_CROWD': True,
        'HOME_NET': 5.0, 'AWAY_NET': -1.0, 'HOME_FORM': 2.0, 'AWAY_FORM': 3.0, 'HOME_REST': 2, 'AWAY_REST': 1,
        'HOME_B2B': 0, 'AWAY_B2B': 1, 'HOME_3IN4': 0, 'AWAY_3IN4': 0, 'AWAY_TRAVEL_KM': 1500.0, 'AWAY_TZ_SHIFT': -2,
        'HOME_FULL_VALUE': 30.0, 'AWAY_FULL_VALUE': 25.0, 'HOME_TONIGHT_VALUE': 20.0, 'HOME_RECENT_VALUE': 28.0,
        'AWAY_TONIGHT_VALUE': 25.0, 'AWAY_RECENT_VALUE': 25.0, 'HOME_ACTUAL_VALUE': 18.0, 'AWAY_ACTUAL_VALUE': 25.0,
    }
    out = add_features(pd.DataFrame([row])).iloc[0]
    assert out['ELO_DIFF'] == pytest.approx(2.0)
    assert out['REDUCED_CROWD'] == 1 and out['NO_CROWD'] == 0
    assert out['NET_DIFF'] == 6.0 and out['REST_DIFF'] == 1
    assert out['AWAY_TRAVEL'] == 1.5 and out['AWAY_TZ_EAST'] == 0
    assert out['AVAIL_DIFF'] == -8.0 and out['AVAIL_ACTUAL_DIFF'] == -10.0
    assert set(FEATURES) <= set(out.index)


def test_win_probability_follows_the_margin():
    assert win_probability(0.0, 12.0) == pytest.approx(0.5)
    assert win_probability(12.0, 12.0) == pytest.approx(0.8413, abs=1e-4)
    assert win_probability(-12.0, 12.0) == pytest.approx(1 - 0.8413, abs=1e-4)


def test_predict_adds_up_the_coefficients():
    model = {'intercept': 2.0, 'spread': 12.0, 'coefficients': {'ELO_DIFF': 1.0, 'AVAIL_DIFF': 0.5}}
    margin, prob = predict(pd.DataFrame([{'ELO_DIFF': 3.0, 'AVAIL_DIFF': -4.0}]), model)
    assert margin[0] == pytest.approx(3.0)
    assert prob[0] == pytest.approx(win_probability(3.0, 12.0))


def test_calibration_bins_are_from_the_favourites_side():
    y = np.array([1, 0, 1, 1])
    p = np.array([0.9, 0.1, 0.55, 0.45])  # favourites: home, away, home, away
    rows = calibration(y, p, bins=5)
    assert sum(r['games'] for r in rows) == 4
    top = rows[-1]
    assert top['games'] == 2 and top['actual'] == 1.0  # both 90% favourites won


def listing(day, team, player, status):
    return {'GAME_DATE': day, 'TEAM_ABBR': team, 'PLAYER_ID': float(player), 'STATUS': status, 'REASON': 'Injury'}


def test_upcoming_statuses_are_decided_per_team():
    # Tonight's report lists BOS; NYK still says NOT YET SUBMITTED (no rows), so its star, out since
    # its last game, is carried forward. MIA had someone out three days ago but has played since with
    # nobody listed, so nothing is carried. Tomorrow's BOS game carries only tonight's Out player.
    report = pd.DataFrame([listing('2026-11-09', 'BOS', 1, 'Out'), listing('2026-11-09', 'BOS', 2, 'Questionable')])
    archive = pd.DataFrame([
        listing('2026-11-07', 'NYK', 10, 'Out'), listing('2026-11-07', 'NYK', 11, 'Questionable'),
        listing('2026-11-06', 'MIA', 20, 'Out'),
        listing('2026-11-09', 'BOS', 3, 'Out'),  # an earlier report today: replaced by the latest
    ])
    played = pd.DataFrame({'GAME_DATE': ['2026-11-07', '2026-11-08'], 'HOME': ['NYK', 'MIA'], 'AWAY': ['CHI', 'ORL']})
    games = pd.DataFrame({'GAME_DATE': ['2026-11-09', '2026-11-09', '2026-11-10'],
                          'HOME': ['BOS', 'MIA', 'BOS'], 'AWAY': ['NYK', 'ATL', 'DAL']})
    got = upcoming_statuses(report, archive, games, played)
    found = {(r.GAME_DATE, r.TEAM_ABBR, r.PLAYER_ID): (r.STATUS, r.STATUS_SOURCE) for r in got.itertuples()}
    assert found == {
        ('2026-11-09', 'BOS', 1): ('Out', 'report'),
        ('2026-11-09', 'BOS', 2): ('Questionable', 'report'),
        ('2026-11-09', 'NYK', 10): ('Out', 'carried'),
        ('2026-11-10', 'BOS', 1): ('Out', 'carried'),
    }
