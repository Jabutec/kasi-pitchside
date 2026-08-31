-- Kasi Pitchside — warehouse schema (PostgreSQL)

-- UTILITY FUNCTIONS & TRIGGERS
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- DIMENSION TABLES
CREATE TABLE IF NOT EXISTS season (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS venue (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    city VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS team (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    short_code VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS player (
    id SERIAL PRIMARY KEY,
    team_id INT NOT NULL REFERENCES team(id) ON DELETE RESTRICT,
    name VARCHAR(100) NOT NULL,
    position VARCHAR(10) CHECK (position IN ('GK', 'DEF', 'MID', 'FWD')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_player_team UNIQUE (name, team_id)
);

-- FACT TABLES
CREATE TABLE IF NOT EXISTS match (
    id SERIAL PRIMARY KEY,
    season_id INT NOT NULL REFERENCES season(id) ON DELETE CASCADE,
    home_team_id INT NOT NULL REFERENCES team(id) ON DELETE RESTRICT,
    away_team_id INT NOT NULL REFERENCES team(id) ON DELETE RESTRICT,
    venue_id INT REFERENCES venue(id) ON DELETE SET NULL,
    matchday INT NOT NULL,
    match_date DATE NOT NULL,
    kickoff_time TIME,
    home_score INT,                        
    away_score INT,                        
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'live', 'full-time', 'postponed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_match_fixture UNIQUE (season_id, home_team_id, away_team_id, matchday),
    CONSTRAINT ck_match_teams_differ CHECK (home_team_id != away_team_id)
);

CREATE TABLE IF NOT EXISTS player_match_stat (
    id SERIAL PRIMARY KEY,
    match_id INT NOT NULL REFERENCES match(id) ON DELETE CASCADE,
    player_id INT NOT NULL REFERENCES player(id) ON DELETE CASCADE,
    team_id INT NOT NULL REFERENCES team(id) ON DELETE RESTRICT,   -- freezes player's team for this match
    goals INT DEFAULT 0,
    assists INT DEFAULT 0,
    shots INT DEFAULT 0,
    minutes_played INT DEFAULT 0,
    motm BOOLEAN DEFAULT FALSE,
    saves INT DEFAULT 0,
    goals_conceded INT DEFAULT 0,
    clean_sheet BOOLEAN DEFAULT FALSE,
    yellow_cards INT DEFAULT 0,
    red_cards INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_match_player_stat UNIQUE (match_id, player_id)
);

CREATE TABLE IF NOT EXISTS standing_snapshot (
    id SERIAL PRIMARY KEY,
    season_id INT NOT NULL REFERENCES season(id) ON DELETE CASCADE,
    team_id INT NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    matchday INT NOT NULL,
    position INT NOT NULL,
    played INT DEFAULT 0,
    wins INT DEFAULT 0,
    draws INT DEFAULT 0,
    losses INT DEFAULT 0,
    goals_for INT DEFAULT 0,
    goals_against INT DEFAULT 0,
    goal_difference INT DEFAULT 0,
    points INT DEFAULT 0,
    recorded_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_standing_snapshot UNIQUE (season_id, team_id, matchday)
    -- insert-only table: no updated_at, no update trigger — rows are never modified after insert
);

-- PERFORMANCE INDEXES
CREATE INDEX IF NOT EXISTS idx_match_season_status ON match(season_id, status);
CREATE INDEX IF NOT EXISTS idx_match_date ON match(match_date);
CREATE INDEX IF NOT EXISTS idx_match_home_team ON match(home_team_id);
CREATE INDEX IF NOT EXISTS idx_match_away_team ON match(away_team_id);
CREATE INDEX IF NOT EXISTS idx_player_match_stat_match ON player_match_stat(match_id);
CREATE INDEX IF NOT EXISTS idx_player_match_stat_player ON player_match_stat(player_id);
CREATE INDEX IF NOT EXISTS idx_standing_snapshot_season_matchday ON standing_snapshot(season_id, matchday);

-- ATTACH TRIGGERS
DROP TRIGGER IF EXISTS set_match_updated_at ON match;
CREATE TRIGGER set_match_updated_at
BEFORE UPDATE ON match
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS set_player_match_stat_updated_at ON player_match_stat;
CREATE TRIGGER set_player_match_stat_updated_at
BEFORE UPDATE ON player_match_stat
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

