-- Serving database for the API (backend/data/nba.db), built by src/export_db.py.
-- Read-only at runtime. Every stat column ending in _pg is a per-game average;
-- *_pct columns are fractions (0.512 = 51.2%).

PRAGMA user_version = 3;  -- bump when the schema changes

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE franchises (
    abbr            TEXT PRIMARY KEY,              -- current abbreviation, e.g. 'OKC'
    nba_team_id     INTEGER NOT NULL UNIQUE,       -- NBA.com id (used for logo URLs)
    name            TEXT NOT NULL,                 -- 'Oklahoma City Thunder'
    city            TEXT NOT NULL,
    nickname        TEXT NOT NULL,
    conference      TEXT NOT NULL CHECK (conference IN ('East', 'West')),
    primary_color   TEXT NOT NULL,
    secondary_color TEXT NOT NULL
);

CREATE TABLE players (
    player_id        INTEGER PRIMARY KEY,          -- NBA.com id (used for headshot URLs)
    name             TEXT NOT NULL,
    search_name      TEXT NOT NULL,                -- lowercase, accents removed
    position         TEXT,                         -- NBA.com listed position, e.g. 'G-F' (NULL if unlisted)
    position_group   TEXT NOT NULL CHECK (position_group IN ('G', 'F', 'C')),  -- primary listed position
    height_in        INTEGER,
    weight_lb        INTEGER,
    country          TEXT,
    college          TEXT,
    draft_year       INTEGER,                      -- draft columns are NULL for undrafted players
    draft_round      INTEGER,
    draft_number     INTEGER,
    first_season     TEXT NOT NULL,
    last_season      TEXT NOT NULL,
    seasons_played   INTEGER NOT NULL,
    latest_team_abbr TEXT NOT NULL REFERENCES franchises (abbr),  -- team in the player's last season in this data
    current_team_abbr TEXT REFERENCES franchises (abbr)           -- NBA.com roster today; NULL if not on one
);
CREATE INDEX ix_players_search_name ON players (search_name);

CREATE TABLE seasons (
    season        TEXT PRIMARY KEY,                -- '2023-24'
    start_year    INTEGER NOT NULL UNIQUE,
    champion_abbr TEXT REFERENCES franchises (abbr),   -- NULL when not recorded
    mvp_player_id INTEGER REFERENCES players (player_id),
    in_progress   INTEGER NOT NULL DEFAULT 0 CHECK (in_progress IN (0, 1))  -- 1: the season under way (stats so far)
);

CREATE TABLE team_seasons (
    team_abbr           TEXT NOT NULL REFERENCES franchises (abbr),
    season              TEXT NOT NULL REFERENCES seasons (season),
    team_abbr_then      TEXT NOT NULL,             -- abbreviation used that season, e.g. 'SEA'
    conference          TEXT NOT NULL CHECK (conference IN ('East', 'West')),
    conference_rank     INTEGER NOT NULL,
    wins                INTEGER NOT NULL,
    losses              INTEGER NOT NULL,
    win_pct             REAL NOT NULL,
    point_diff_pg       REAL NOT NULL,
    is_champion         INTEGER NOT NULL CHECK (is_champion IN (0, 1)),
    PRIMARY KEY (team_abbr, season)
);
CREATE INDEX ix_team_seasons_season ON team_seasons (season);

CREATE TABLE player_seasons (
    player_id       INTEGER NOT NULL REFERENCES players (player_id),
    season          TEXT NOT NULL,
    team_abbr       TEXT NOT NULL,                 -- franchise (current abbreviation)
    team_abbr_then  TEXT NOT NULL,
    games           INTEGER NOT NULL,
    min_pg          REAL NOT NULL,
    pts_pg          REAL NOT NULL,
    reb_pg          REAL NOT NULL,
    ast_pg          REAL NOT NULL,
    stl_pg          REAL NOT NULL,
    blk_pg          REAL NOT NULL,
    tov_pg          REAL NOT NULL,
    fg_pct          REAL NOT NULL,
    fg3_pct         REAL NOT NULL,
    ft_pct          REAL NOT NULL,
    ts_pct          REAL NOT NULL,
    efg_pct         REAL NOT NULL,
    usg_pct         REAL NOT NULL,
    pie             REAL NOT NULL,
    off_rating      REAL NOT NULL,
    def_rating      REAL NOT NULL,
    net_rating      REAL NOT NULL,
    ast_to          REAL NOT NULL,
    oreb_pct        REAL NOT NULL,
    dreb_pct        REAL NOT NULL,
    ast_pct         REAL NOT NULL,
    reb_pct         REAL NOT NULL,
    -- Archetype columns are NULL for players below the clustering thresholds
    archetype       TEXT CHECK (archetype IN ('Scorer', 'Playmaker', 'Rebounder', 'Defensive Player')),
    tier            TEXT CHECK (tier IN ('Elite', 'Very Good', 'Average')),
    scorer_score    REAL,
    playmaker_score REAL,
    rebounder_score REAL,
    defender_score  REAL,
    PRIMARY KEY (player_id, season),
    FOREIGN KEY (team_abbr, season) REFERENCES team_seasons (team_abbr, season)
);
CREATE INDEX ix_player_seasons_season ON player_seasons (season);
CREATE INDEX ix_player_seasons_team ON player_seasons (team_abbr, season);

-- Percentile (0-100) of each stat within a peer group for that season. Higher is always better
-- (tov_pg and def_rating are inverted). peer_group is 'ALL' or the player's position group.
CREATE TABLE player_percentiles (
    player_id  INTEGER NOT NULL,
    season     TEXT NOT NULL,
    peer_group TEXT NOT NULL CHECK (peer_group IN ('ALL', 'G', 'F', 'C')),
    min_pg REAL, pts_pg REAL, reb_pg REAL, ast_pg REAL, stl_pg REAL, blk_pg REAL, tov_pg REAL,
    fg_pct REAL, fg3_pct REAL, ft_pct REAL, ts_pct REAL, efg_pct REAL, usg_pct REAL, pie REAL,
    off_rating REAL, def_rating REAL, net_rating REAL, ast_to REAL,
    oreb_pct REAL, dreb_pct REAL, ast_pct REAL, reb_pct REAL,
    PRIMARY KEY (player_id, season, peer_group),
    FOREIGN KEY (player_id, season) REFERENCES player_seasons (player_id, season)
);

-- Five most similar player-seasons (same season) by distance between archetype scores.
CREATE TABLE similar_players (
    player_id         INTEGER NOT NULL,
    season            TEXT NOT NULL,
    rank              INTEGER NOT NULL CHECK (rank BETWEEN 1 AND 5),
    similar_player_id INTEGER NOT NULL,
    distance          REAL NOT NULL,
    PRIMARY KEY (player_id, season, rank),
    FOREIGN KEY (player_id, season) REFERENCES player_seasons (player_id, season),
    FOREIGN KEY (similar_player_id, season) REFERENCES player_seasons (player_id, season)
);

-- Leave-one-season-out MVP predictions, precomputed. model_score is the raw XGBoost output
-- (not a calibrated probability); score_share normalises it to sum to 1 within a season.
CREATE TABLE mvp_candidates (
    season      TEXT NOT NULL REFERENCES seasons (season),
    player_id   INTEGER NOT NULL,
    rank        INTEGER NOT NULL,
    model_score REAL NOT NULL,
    score_share REAL NOT NULL,
    is_mvp      INTEGER NOT NULL CHECK (is_mvp IN (0, 1)),
    PRIMARY KEY (season, player_id),
    UNIQUE (season, rank),
    FOREIGN KEY (player_id, season) REFERENCES player_seasons (player_id, season)
);

CREATE TABLE mvp_seasons (
    season              TEXT PRIMARY KEY REFERENCES seasons (season),
    era                 INTEGER NOT NULL CHECK (era IN (1, 2)),
    candidates          INTEGER NOT NULL,
    predicted_player_id INTEGER NOT NULL REFERENCES players (player_id),
    actual_player_id    INTEGER NOT NULL REFERENCES players (player_id),
    actual_rank         INTEGER NOT NULL,          -- where the real MVP ranked in the model's list
    correct             INTEGER NOT NULL CHECK (correct IN (0, 1))
);

-- One row per team per game, with the team's record AFTER the game.
CREATE TABLE team_game_log (
    team_abbr        TEXT NOT NULL REFERENCES franchises (abbr),
    game_id          TEXT NOT NULL,
    game_date        TEXT NOT NULL,                -- ISO date
    season           TEXT NOT NULL REFERENCES seasons (season),
    opponent_abbr    TEXT NOT NULL REFERENCES franchises (abbr),
    is_home          INTEGER NOT NULL CHECK (is_home IN (0, 1)),
    won              INTEGER NOT NULL CHECK (won IN (0, 1)),
    wins             INTEGER NOT NULL,
    losses           INTEGER NOT NULL,
    win_pct          REAL NOT NULL,
    home_win_pct     REAL,                         -- NULL until the team has played at home
    road_win_pct     REAL,                         -- NULL until the team has played on the road
    PRIMARY KEY (team_abbr, game_id)
);
CREATE INDEX ix_team_game_log_team_date ON team_game_log (team_abbr, game_date);

-- The game model (src/game_model) on the season in progress: every game played so far, as predicted
-- before it, and the coming week. Built by `python -m src.game_model.live`; the model itself and its
-- evaluation are JSON in meta (game_model, game_model_metrics, game_live).
CREATE TABLE game_predictions (
    game_id            TEXT PRIMARY KEY,
    season             TEXT NOT NULL,
    game_date          TEXT NOT NULL,              -- ISO date (US Eastern)
    tip_et             TEXT,                       -- 'HH:MM' Eastern, upcoming games only
    home_abbr          TEXT NOT NULL REFERENCES franchises (abbr),
    away_abbr          TEXT NOT NULL REFERENCES franchises (abbr),
    played             INTEGER NOT NULL CHECK (played IN (0, 1)),
    home_pts           INTEGER,                    -- NULL until played
    away_pts           INTEGER,
    pred_margin        REAL NOT NULL,              -- predicted home margin, points
    home_win_prob      REAL NOT NULL,
    home_wins          INTEGER NOT NULL,           -- records BEFORE the game
    home_losses        INTEGER NOT NULL,
    away_wins          INTEGER NOT NULL,
    away_losses        INTEGER NOT NULL,
    home_elo           REAL NOT NULL,
    away_elo           REAL NOT NULL,
    home_recent_value  REAL NOT NULL,              -- player value each team has fielded lately ...
    away_recent_value  REAL NOT NULL,
    home_tonight_value REAL NOT NULL,              -- ... and expects to have tonight
    away_tonight_value REAL NOT NULL,
    features           TEXT NOT NULL               -- JSON {feature: value}, the model's inputs
);
CREATE INDEX ix_game_predictions_date ON game_predictions (game_date);

-- Every rostered player in those games, for the injury list and what-if changes.
CREATE TABLE game_players (
    game_id          TEXT NOT NULL REFERENCES game_predictions (game_id),
    team_abbr        TEXT NOT NULL REFERENCES franchises (abbr),
    player_id        INTEGER NOT NULL,             -- NBA.com id; not every player is in `players`
    name             TEXT NOT NULL,
    value            REAL NOT NULL,                -- Game Score above replacement at his usual minutes
    rate_above       REAL NOT NULL,                -- the same per minute
    expected_minutes REAL NOT NULL,
    participation    REAL NOT NULL,                -- share of the team's last 10 games he played
    status           TEXT CHECK (status IN ('Out', 'Doubtful', 'Questionable', 'Probable', 'Available')),
    chance           REAL NOT NULL,                -- chance of playing the model used
    reason           TEXT,
    status_source    TEXT CHECK (status_source IN ('report', 'carried')),
    played           INTEGER CHECK (played IN (0, 1)),  -- NULL until the game is played
    PRIMARY KEY (game_id, player_id)
);
