-- Import FPL Draft Data - Clean Version
-- Run this after creating the draft tables
-- Set the LEAGUE_ID variable before running this script

-- Configuration - Change this to your league ID
\set LEAGUE_ID 25029

-- Clear existing data for the specified league
DELETE FROM draft_picks WHERE league_id = :LEAGUE_ID;
DELETE FROM draft_managers WHERE league_id = :LEAGUE_ID;
DELETE FROM draft_standings WHERE league_id = :LEAGUE_ID;
DELETE FROM draft_leagues WHERE league_id = :LEAGUE_ID;

-- Drop temp tables if they exist
DROP TABLE IF EXISTS temp_managers;
DROP TABLE IF EXISTS temp_picks;

-- Import league info
INSERT INTO draft_leagues (league_id, league_name, draft_dt, start_event, stop_event, draft_status, total_managers)
VALUES (:LEAGUE_ID, 'Sequel ka Sequel', '2025-08-10T16:45:00Z', 1, 38, 'post', 10);

-- Create temporary table for managers import
CREATE TEMP TABLE temp_managers (
    entry_id TEXT,
    entry_name TEXT,
    id INTEGER,
    joined_time TEXT,
    player_first_name TEXT,
    player_last_name TEXT,
    short_name TEXT,
    waiver_pick TEXT
);

-- Import managers CSV into temp table (always uses latest symlink)
\copy temp_managers FROM 'data/draft_league/latest/managers.csv' DELIMITER ',' CSV HEADER;

-- Insert into draft_managers from temp table (skip incomplete records)
INSERT INTO draft_managers (id, league_id, entry_name, player_first_name, player_last_name, short_name, waiver_pick, entry_id, joined_time)
SELECT 
    id,
    :LEAGUE_ID as league_id,
    COALESCE(NULLIF(entry_name, ''), 'Unknown Team') as entry_name,
    NULLIF(player_first_name, ''),
    NULLIF(player_last_name, ''),
    short_name,
    CASE WHEN waiver_pick = '' OR waiver_pick IS NULL THEN NULL ELSE waiver_pick::DECIMAL::INTEGER END,
    CASE WHEN entry_id = '' OR entry_id IS NULL THEN NULL ELSE entry_id::DECIMAL::INTEGER END,
    CASE WHEN joined_time = '' OR joined_time IS NULL THEN NULL ELSE joined_time::TIMESTAMP END
FROM temp_managers
WHERE short_name IS NOT NULL AND short_name != '';

-- Create temporary table for picks import  
CREATE TEMP TABLE temp_picks (
    element TEXT,
    in_accepted_trade TEXT,
    owner TEXT,
    status TEXT
);

-- Import picks CSV into temp table (always uses latest symlink)
\copy temp_picks FROM 'data/draft_league/latest/picks.csv' DELIMITER ',' CSV HEADER;

-- Insert into draft_picks from temp table
INSERT INTO draft_picks (element_id, league_id, owner, status)
SELECT 
    element::INTEGER,
    :LEAGUE_ID as league_id,
    CASE 
        WHEN owner IS NULL OR owner = '' THEN NULL 
        ELSE owner::DECIMAL::INTEGER 
    END,
    status
FROM temp_picks
WHERE element IS NOT NULL AND element != '';

-- Clean up temp tables
DROP TABLE temp_managers;
DROP TABLE temp_picks;

-- Show summary
SELECT 'League Info' as table_name, COUNT(*) as records FROM draft_leagues WHERE league_id = :LEAGUE_ID
UNION ALL
SELECT 'Managers' as table_name, COUNT(*) as records FROM draft_managers WHERE league_id = :LEAGUE_ID
UNION ALL  
SELECT 'Picks' as table_name, COUNT(*) as records FROM draft_picks WHERE league_id = :LEAGUE_ID;