"""Build the read-only serving database (backend/data/nba.db) and the portable next-game model.

Everything the API needs is precomputed here, so the API itself only does lookups:
  - per-game player stats, archetypes and tiers
  - percentile ranks per season and peer group (for player comparisons)
  - five most similar players per player-season
  - leave-one-season-out MVP predictions for every season
  - team standings and game-by-game records
  - the season in progress (if fetched): stats so far and standings, marked in_progress and
    left out of everything model-based (MVP tables, archetypes, similar players)
  - the next-game XGBoost model exported to plain JSON trees (no xgboost needed to serve it)

Run from the repository root:
    python -m src.export_db
"""
import contextlib
import io
import json
import sqlite3
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from nba_api.stats.static import teams as nba_teams

from src.features import to_per_game
from src.models.mvp_prediction import run_loocv
from src.nba_reference import CHAMPIONS, CONFERENCES, TEAM_COLORS, franchise_abbreviation, get_conference, normalize_name
from src.paths import (
    CLUSTERED_PLAYERS,
    CURRENT_SEASON_STANDINGS,
    CURRENT_SEASON_STATS,
    DB_SCHEMA,
    GAME_MATCHUPS,
    MVP_DATA,
    NEXT_GAME_METRICS,
    NEXT_GAME_MODEL,
    PLAYER_BIO,
    RAW_PLAYER_STATS,
    SERVING_DB,
    SERVING_DIR,
    SERVING_NEXT_GAME_MODEL,
)

# sqlite3 cannot bind numpy scalars directly
for _np_type in (np.int64, np.int32):
    sqlite3.register_adapter(_np_type, int)
sqlite3.register_adapter(np.bool_, int)


# Raw column -> database column
STAT_COLUMNS = {
    'MIN': 'min_pg', 'PTS': 'pts_pg', 'REB': 'reb_pg', 'AST': 'ast_pg', 'STL': 'stl_pg', 'BLK': 'blk_pg', 'TOV': 'tov_pg',
    'FG_PCT': 'fg_pct', 'FG3_PCT': 'fg3_pct', 'FT_PCT': 'ft_pct', 'TS_PCT': 'ts_pct', 'EFG_PCT': 'efg_pct',
    'USG_PCT': 'usg_pct', 'PIE': 'pie', 'OFF_RATING': 'off_rating', 'DEF_RATING': 'def_rating',
    'NET_RATING': 'net_rating', 'AST_TO': 'ast_to', 'OREB_PCT': 'oreb_pct', 'DREB_PCT': 'dreb_pct',
    'AST_PCT': 'ast_pct', 'REB_PCT': 'reb_pct',
}
LOWER_IS_BETTER = {'tov_pg', 'def_rating'}

ARCHETYPE_SCORE_COLUMNS = {
    'Scorer_Score': 'scorer_score',
    'Playmaker_Score': 'playmaker_score',
    'Rebounder_Score': 'rebounder_score',
    'Defensive Player_Score': 'defender_score',
}
SIMILAR_PLAYERS_PER_SEASON = 5


def season_from_id(season_id):
    """NBA SEASON_ID 22025 -> '2025-26'."""
    start = int(str(season_id)[-4:])
    return f"{start}-{str(start + 1)[-2:]}"


# --- table builders ----------------------------------------------------------------------

def build_franchises():
    conference_of = {abbr: conf for conf, members in CONFERENCES.items() for abbr in members}
    rows = []
    for team in nba_teams.get_teams():
        abbr = team['abbreviation']
        primary, secondary = TEAM_COLORS[abbr]
        rows.append({
            'abbr': abbr, 'nba_team_id': team['id'], 'name': team['full_name'], 'city': team['city'],
            'nickname': team['nickname'], 'conference': conference_of[abbr],
            'primary_color': primary, 'secondary_color': secondary,
        })
    return pd.DataFrame(rows).sort_values('abbr')


def _rank_within_conference(df):
    df['conference'] = [get_conference(t, s) for t, s in zip(df['team_abbr_then'], df['season'])]
    df['conference_rank'] = (
        df.groupby(['season', 'conference'])['win_pct'].rank(ascending=False, method='min').astype(int)
    )
    return df


def build_team_seasons(mvp_data):
    df = (
        mvp_data[['FRANCHISE_ABBREVIATION', 'SEASON', 'TEAM_ABBREVIATION', 'WINS', 'LOSSES', 'WinPCT', 'DiffPointsPG']]
        .drop_duplicates(subset=['FRANCHISE_ABBREVIATION', 'SEASON'])
        .rename(columns={
            'FRANCHISE_ABBREVIATION': 'team_abbr', 'SEASON': 'season', 'TEAM_ABBREVIATION': 'team_abbr_then',
            'WINS': 'wins', 'LOSSES': 'losses', 'WinPCT': 'win_pct', 'DiffPointsPG': 'point_diff_pg',
        })
    )
    df = _rank_within_conference(df)
    df['is_champion'] = (df['team_abbr'] == df['season'].map(CHAMPIONS)).astype(int)
    return df.sort_values(['season', 'team_abbr'])


def build_current_team_seasons(standings):
    """Standings so far for the season in progress (every team uses its current abbreviation)."""
    df = standings.rename(columns={
        'FRANCHISE_ABBREVIATION': 'team_abbr', 'SEASON': 'season',
        'WINS': 'wins', 'LOSSES': 'losses', 'WinPCT': 'win_pct', 'DiffPointsPG': 'point_diff_pg',
    })[['team_abbr', 'season', 'wins', 'losses', 'win_pct', 'point_diff_pg']]
    df['team_abbr_then'] = df['team_abbr']
    df = _rank_within_conference(df)
    df['is_champion'] = 0
    return df.sort_values('team_abbr')


def load_current_season(completed_seasons):
    """(stats, standings) for the season in progress, or (None, None) when it hasn't been fetched."""
    if not (CURRENT_SEASON_STATS.exists() and CURRENT_SEASON_STANDINGS.exists()):
        return None, None
    stats, standings = pd.read_csv(CURRENT_SEASON_STATS), pd.read_csv(CURRENT_SEASON_STANDINGS)
    seasons = set(stats['SEASON']) | set(standings['SEASON'])
    if len(seasons) != 1:
        raise ValueError(f"Current-season files mix seasons: {sorted(seasons)}")
    season = seasons.pop()
    if season <= max(completed_seasons):
        # e.g. the season has ended and been added to the completed data, but the old file is still here
        print(f"Ignoring {CURRENT_SEASON_STATS.name}: {season} is not after the last completed season")
        return None, None
    return stats, standings


def build_player_seasons(raw_totals, clustered):
    per_game = to_per_game(raw_totals)
    df = per_game[['PLAYER_ID', 'SEASON', 'TEAM_ABBREVIATION', 'GP', *STAT_COLUMNS]].rename(
        columns={'PLAYER_ID': 'player_id', 'SEASON': 'season', 'TEAM_ABBREVIATION': 'team_abbr_then', 'GP': 'games',
                 **STAT_COLUMNS}
    )
    df['team_abbr'] = df['team_abbr_then'].map(franchise_abbreviation)

    archetypes = clustered[['PLAYER_ID', 'SEASON', 'Cluster', 'Tier', *ARCHETYPE_SCORE_COLUMNS]].rename(
        columns={'PLAYER_ID': 'player_id', 'SEASON': 'season', 'Cluster': 'archetype', 'Tier': 'tier',
                 **ARCHETYPE_SCORE_COLUMNS}
    )
    df = df.merge(archetypes, on=['player_id', 'season'], how='left', validate='one_to_one')
    return df.sort_values(['season', 'player_id'])


def fallback_position_group(career_totals):
    """G/F/C from career per-36-minute rates, for the rare player without a listed position."""
    per36 = career_totals[['REB', 'AST', 'BLK']].div(career_totals['MIN'].clip(lower=1), axis=0) * 36
    groups = pd.Series('G', index=per36.index)
    groups[per36['REB'] >= 6.0] = 'F'
    groups[(per36['REB'] >= 10.5) | ((per36['REB'] >= 9.0) & (per36['BLK'] >= 1.6))] = 'C'
    return groups


def build_players(raw_totals, player_seasons, bio):
    ordered = player_seasons.sort_values(['player_id', 'season'])
    grouped = ordered.groupby('player_id')
    names = raw_totals.drop_duplicates('PLAYER_ID').set_index('PLAYER_ID')['PLAYER_NAME']

    players = pd.DataFrame({
        'first_season': grouped['season'].first(),
        'last_season': grouped['season'].last(),
        'seasons_played': grouped.size(),
        'latest_team_abbr': grouped['team_abbr'].last(),
    })
    players['name'] = names.reindex(players.index)
    players['search_name'] = players['name'].map(lambda n: normalize_name(n).lower())

    bio = bio.set_index('PLAYER_ID').reindex(players.index)
    players['position'] = bio['POSITION']
    fallback = fallback_position_group(raw_totals.groupby('PLAYER_ID')[['MIN', 'REB', 'AST', 'BLK']].sum())
    players['position_group'] = bio['POSITION'].str[0].fillna(fallback.reindex(players.index))
    players['height_in'] = bio['HEIGHT_IN'].astype('Int64')
    players['weight_lb'] = bio['WEIGHT_LB'].astype('Int64')
    players['country'] = bio['COUNTRY']
    players['college'] = bio['COLLEGE'].replace({'None': None, '': None})
    for col in ('DRAFT_YEAR', 'DRAFT_ROUND', 'DRAFT_NUMBER'):
        players[col.lower()] = bio[col].astype('Int64')
    players['current_team_abbr'] = bio['CURRENT_TEAM']
    return players.rename_axis('player_id').reset_index()


def build_seasons(mvp_data, current_season=None):
    seasons = sorted(mvp_data['SEASON'].unique())
    mvp_ids = mvp_data.loc[mvp_data['IS_MVP'] == 1].set_index('SEASON')['PLAYER_ID']
    df = pd.DataFrame({
        'season': seasons,
        'start_year': [int(s[:4]) for s in seasons],
        'champion_abbr': [CHAMPIONS.get(s) for s in seasons],
        'mvp_player_id': [mvp_ids.get(s) for s in seasons],
        'in_progress': 0,
    })
    if current_season:
        current = {'season': current_season, 'start_year': int(current_season[:4]), 'in_progress': 1}
        df = pd.concat([df, pd.DataFrame([current])], ignore_index=True)
    return df


def build_percentiles(player_seasons, players):
    df = player_seasons.merge(players[['player_id', 'position_group']], on='player_id')
    metrics = list(STAT_COLUMNS.values())
    frames = []
    for peer_group, keys in (('ALL', ['season']), ('POSITION', ['season', 'position_group'])):
        grouped = df.groupby(keys)
        out = df[['player_id', 'season']].copy()
        out['peer_group'] = 'ALL' if peer_group == 'ALL' else df['position_group']
        for metric in metrics:
            ascending = metric not in LOWER_IS_BETTER
            out[metric] = (grouped[metric].rank(pct=True, ascending=ascending) * 100).round(1)
        frames.append(out)
    return pd.concat(frames, ignore_index=True)


def build_similar_players(player_seasons):
    scored = player_seasons.dropna(subset=list(ARCHETYPE_SCORE_COLUMNS.values()))
    rows = []
    for season, group in scored.groupby('season'):
        ids = group['player_id'].to_numpy()
        vectors = group[list(ARCHETYPE_SCORE_COLUMNS.values())].to_numpy()
        distances = np.sqrt(((vectors[:, None, :] - vectors[None, :, :]) ** 2).sum(axis=2))
        np.fill_diagonal(distances, np.inf)  # never match a player with themselves
        k = min(SIMILAR_PLAYERS_PER_SEASON, len(ids) - 1)
        for i, player_id in enumerate(ids):
            # stable sort on (distance, player_id) keeps the output deterministic
            order = np.lexsort((ids, distances[i]))[:k]
            for rank, j in enumerate(order, 1):
                rows.append({'player_id': player_id, 'season': season, 'rank': rank,
                             'similar_player_id': ids[j], 'distance': round(float(distances[i, j]), 4)})
    return pd.DataFrame(rows)


def build_mvp_tables():
    with contextlib.redirect_stdout(io.StringIO()):  # run_loocv prints progress
        results = run_loocv()['results']

    candidate_rows, season_rows = [], []
    for res in results:
        cands = pd.DataFrame(res['ALL_CANDIDATES']).sort_values(['MVP_PROB_SCORE', 'PLAYER_ID'], ascending=[False, True])
        cands['rank'] = range(1, len(cands) + 1)
        total = cands['MVP_PROB_SCORE'].sum()
        for row in cands.itertuples(index=False):
            candidate_rows.append({
                'season': res['SEASON'], 'player_id': row.PLAYER_ID, 'rank': row.rank,
                'model_score': round(float(row.MVP_PROB_SCORE), 6),
                'score_share': round(float(row.MVP_PROB_SCORE / total), 6) if total > 0 else 0.0,
                'is_mvp': int(row.IS_MVP),
            })
        actual = cands[cands['IS_MVP'] == 1].iloc[0]
        predicted = cands.iloc[0]
        season_rows.append({
            'season': res['SEASON'], 'era': res['ERA'], 'candidates': len(cands),
            'predicted_player_id': predicted['PLAYER_ID'], 'actual_player_id': actual['PLAYER_ID'],
            'actual_rank': int(actual['rank']), 'correct': int(predicted['PLAYER_ID'] == actual['PLAYER_ID']),
        })
    return pd.DataFrame(candidate_rows), pd.DataFrame(season_rows)


def build_team_game_log(games):
    games = games.sort_values(['GAME_DATE', 'GAME_ID'])
    home = pd.DataFrame({
        'team_abbr': games['HOME_TEAM_ABBREVIATION'], 'opponent_abbr': games['AWAY_TEAM_ABBREVIATION'],
        'is_home': 1, 'won': games['HOME_WIN'],
    })
    away = pd.DataFrame({
        'team_abbr': games['AWAY_TEAM_ABBREVIATION'], 'opponent_abbr': games['HOME_TEAM_ABBREVIATION'],
        'is_home': 0, 'won': 1 - games['HOME_WIN'],
    })
    for side in (home, away):
        side['game_id'] = games['GAME_ID'].astype(str).str.zfill(10)
        side['game_date'] = pd.to_datetime(games['GAME_DATE']).dt.strftime('%Y-%m-%d')
        side['season'] = games['SEASON_ID'].map(season_from_id)
    log = pd.concat([home, away], ignore_index=True).sort_values(['team_abbr', 'game_date', 'game_id'])

    by_team_season = log.groupby(['team_abbr', 'season'])
    log['wins'] = by_team_season['won'].cumsum()
    log['losses'] = by_team_season.cumcount() + 1 - log['wins']
    log['win_pct'] = (log['wins'] / (log['wins'] + log['losses'])).round(4)

    for flag, column in ((1, 'home_win_pct'), (0, 'road_win_pct')):
        venue = log['is_home'] == flag
        venue_wins = (log['won'] * venue).groupby([log['team_abbr'], log['season']]).cumsum()
        venue_games = venue.astype(int).groupby([log['team_abbr'], log['season']]).cumsum()
        log[column] = (venue_wins / venue_games.replace(0, np.nan)).round(4)

    return log


def export_next_game_model(path):
    """Export the XGBoost model as plain JSON trees that can be evaluated without xgboost."""
    booster = joblib.load(NEXT_GAME_MODEL).get_booster()
    config = json.loads(booster.save_config())
    base_score = float(str(config['learner']['learner_model_param']['base_score']).strip('[]'))
    model = {
        'format': 'xgboost-json-dump',
        'objective': config['learner']['objective']['name'],
        'base_score': base_score,
        'features': booster.feature_names,
        'trees': [json.loads(tree) for tree in booster.get_dump(dump_format='json')],
    }
    path.write_text(json.dumps(model, separators=(',', ':')))
    return len(model['trees'])


# --- writing ----------------------------------------------------------------------------

def _insert(conn, table, df):
    columns = list(df.columns)
    placeholders = ', '.join('?' for _ in columns)
    rows = df.astype(object).where(df.notna(), None).itertuples(index=False, name=None)
    conn.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows)


def build_database(db_path=SERVING_DB, model_path=SERVING_NEXT_GAME_MODEL):
    raw_totals = pd.read_csv(RAW_PLAYER_STATS)
    mvp_data = pd.read_csv(MVP_DATA)
    clustered = pd.read_csv(CLUSTERED_PLAYERS)
    games = pd.read_csv(GAME_MATCHUPS)
    bio = pd.read_csv(PLAYER_BIO)
    current_stats, current_standings = load_current_season(set(mvp_data['SEASON']))
    current_season = current_stats['SEASON'].iloc[0] if current_stats is not None else None

    # Player tables cover the season in progress too; the model inputs above (mvp_data, clustered) don't.
    all_totals = raw_totals if current_stats is None else pd.concat([raw_totals, current_stats], ignore_index=True)
    player_seasons = build_player_seasons(all_totals, clustered)
    players = build_players(all_totals, player_seasons, bio)
    team_seasons = build_team_seasons(mvp_data)
    if current_standings is not None:
        team_seasons = pd.concat([team_seasons, build_current_team_seasons(current_standings)], ignore_index=True)
    mvp_candidates, mvp_seasons = build_mvp_tables()
    next_game_metrics = json.loads(NEXT_GAME_METRICS.read_text())
    # The model trains on every season of game data before the held-out test season.
    next_game_metrics['train_first_season_id'] = int(games['SEASON_ID'].min())

    tables = {  # insertion order respects foreign keys
        'franchises': build_franchises(),
        'players': players,
        'seasons': build_seasons(mvp_data, current_season),
        'team_seasons': team_seasons,
        'player_seasons': player_seasons,
        'player_percentiles': build_percentiles(player_seasons, players),
        'similar_players': build_similar_players(player_seasons),
        'mvp_candidates': mvp_candidates,
        'mvp_seasons': mvp_seasons,
        'team_game_log': build_team_game_log(games),
    }
    meta = {
        'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'first_season': tables['seasons']['season'].min(),
        'last_season': mvp_data['SEASON'].max(),  # last completed season
        'current_season': current_season or '',
        'current_season_as_of': str(current_standings['AS_OF'].iloc[0]) if current_standings is not None else '',
        'mvp_correct': str(int(mvp_seasons['correct'].sum())),
        'mvp_seasons': str(len(mvp_seasons)),
        'next_game_metrics': json.dumps(next_game_metrics),
        'rosters_as_of': str(bio['ROSTERS_AS_OF'].max()),
    }
    tables['meta'] = pd.DataFrame({'key': list(meta), 'value': list(meta.values())})

    # Build into a temporary file and swap it in, so a failed build never leaves a half-written DB.
    SERVING_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_suffix('.tmp')
    tmp_path.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp_path)
    try:
        conn.execute('PRAGMA foreign_keys = ON')
        conn.executescript(DB_SCHEMA.read_text())
        with conn:
            for table, df in tables.items():
                _insert(conn, table, df)
        violations = conn.execute('PRAGMA foreign_key_check').fetchall()
        if violations:
            raise RuntimeError(f"Foreign key violations: {violations[:5]}")
        conn.execute('ANALYZE')
        conn.execute('VACUUM')
    finally:
        conn.close()
    tmp_path.replace(db_path)

    trees = export_next_game_model(model_path)
    counts = {table: len(df) for table, df in tables.items()}
    return counts, trees


def main():
    counts, trees = build_database()
    size_mb = SERVING_DB.stat().st_size / 1e6
    print(f"Built {SERVING_DB} ({size_mb:.1f} MB)")
    for table, n in counts.items():
        print(f"  {table:<20} {n:>7,} rows")
    print(f"Exported next-game model ({trees} trees) to {SERVING_NEXT_GAME_MODEL}")


if __name__ == "__main__":
    main()
