-- Import FPL Draft Data - Fixed Version
-- Run this after creating the draft tables

-- Clear existing data for league 25029
DELETE FROM draft_picks WHERE league_id = 25029;
DELETE FROM draft_managers WHERE league_id = 25029;
DELETE FROM draft_standings WHERE league_id = 25029;
DELETE FROM draft_leagues WHERE league_id = 25029;

-- Import league info
INSERT INTO draft_leagues (league_id, league_name, draft_dt, start_event, stop_event, draft_status, total_managers)
VALUES (25029, 'Sequel ka Sequel', '2025-08-10T16:45:00Z', 1, 38, 'post', 10);

-- Create temporary table for managers import
CREATE TEMP TABLE temp_managers (
    entry_id DECIMAL,
    entry_name TEXT,
    id INTEGER,
    joined_time TEXT,
    player_first_name TEXT,
    player_last_name TEXT,
    short_name TEXT,
    waiver_pick DECIMAL
);

-- Import managers CSV into temp table
\copy temp_managers FROM '/Users/rohanwalyat/Library/Mobile Documents/com~apple~CloudDocs/football-analytics/fpl-elo-insights/data/draft_league/managers_20250811_224812.csv' DELIMITER ',' CSV HEADER;

-- Insert into draft_managers from temp table (skip incomplete records)
INSERT INTO draft_managers (id, league_id, entry_name, player_first_name, player_last_name, short_name, waiver_pick, entry_id, joined_time)
SELECT 
    id,
    25029 as league_id,
    COALESCE(entry_name, 'Unknown Team') as entry_name,
    player_first_name,
    player_last_name,
    short_name,
    waiver_pick::INTEGER,
    entry_id::INTEGER,
    joined_time::TIMESTAMP
FROM temp_managers
WHERE entry_name IS NOT NULL OR short_name IS NOT NULL;

-- Create temporary table for picks import  
CREATE TEMP TABLE temp_picks (
    element INTEGER,
    in_accepted_trade BOOLEAN,
    owner TEXT,  -- Use TEXT to handle decimal values
    status TEXT
);

-- Import picks CSV into temp table
\copy temp_picks FROM '/Users/rohanwalyat/Library/Mobile Documents/com~apple~CloudDocs/football-analytics/fpl-elo-insights/data/draft_league/picks_20250811_224812.csv' DELIMITER ',' CSV HEADER;

-- Insert into draft_picks from temp table
INSERT INTO draft_picks (element_id, league_id, owner, status)
SELECT 
    element,
    25029 as league_id,
    CASE 
        WHEN owner IS NULL OR owner = '' THEN NULL 
        ELSE owner::DECIMAL::INTEGER 
    END,
    status
FROM temp_picks;

-- Show summary
SELECT 'League Info' as table_name, COUNT(*) as records FROM draft_leagues WHERE league_id = 25029
UNION ALL
SELECT 'Managers' as table_name, COUNT(*) as records FROM draft_managers WHERE league_id = 25029
UNION ALL  
SELECT 'Picks' as table_name, COUNT(*) as records FROM draft_picks WHERE league_id = 25029;