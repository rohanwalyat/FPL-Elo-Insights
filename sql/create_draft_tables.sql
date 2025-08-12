-- Create FPL Draft Tables

-- Draft League Information
CREATE TABLE IF NOT EXISTS draft_leagues (
    league_id INTEGER PRIMARY KEY,
    league_name VARCHAR(100) NOT NULL,
    draft_dt TIMESTAMP,
    start_event INTEGER,
    stop_event INTEGER,
    draft_status VARCHAR(20),
    total_managers INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Draft League Managers/Teams
CREATE TABLE IF NOT EXISTS draft_managers (
    id INTEGER,
    league_id INTEGER,
    entry_name VARCHAR(100) NOT NULL,
    player_first_name VARCHAR(50),
    player_last_name VARCHAR(50),
    short_name VARCHAR(20),
    waiver_pick INTEGER,
    entry_id INTEGER,
    joined_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, league_id)
);

-- Draft Player Ownership
CREATE TABLE IF NOT EXISTS draft_picks (
    element_id INTEGER,
    league_id INTEGER,
    owner INTEGER,
    status VARCHAR(20),
    added_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (element_id, league_id)
);

-- Draft League Standings
CREATE TABLE IF NOT EXISTS draft_standings (
    league_id INTEGER,
    entry_id INTEGER,
    entry_name VARCHAR(100),
    player_name VARCHAR(100),
    rank INTEGER,
    last_rank INTEGER,
    rank_sort INTEGER,
    total INTEGER,
    event_total INTEGER,
    PRIMARY KEY (league_id, entry_id)
);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_draft_managers_league ON draft_managers(league_id);
CREATE INDEX IF NOT EXISTS idx_draft_picks_league ON draft_picks(league_id);
CREATE INDEX IF NOT EXISTS idx_draft_picks_owner ON draft_picks(owner);
CREATE INDEX IF NOT EXISTS idx_draft_standings_league ON draft_standings(league_id);