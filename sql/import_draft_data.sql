-- Import FPL Draft Data
-- Run this after creating the draft tables

-- Clear existing data for league 25029
DELETE FROM draft_picks WHERE league_id = 25029;
DELETE FROM draft_managers WHERE league_id = 25029;
DELETE FROM draft_standings WHERE league_id = 25029;
DELETE FROM draft_leagues WHERE league_id = 25029;

-- Import league info
INSERT INTO draft_leagues (league_id, league_name, draft_dt, start_event, stop_event, draft_status, total_managers)
VALUES (25029, 'Sequel ka Sequel', '2025-08-10T16:45:00Z', 1, 38, 'post', 10);

-- Import managers (use the latest CSV file)
\copy draft_managers(entry_id, entry_name, id, joined_time, player_first_name, player_last_name, short_name, waiver_pick) FROM '/Users/rohanwalyat/Library/Mobile Documents/com~apple~CloudDocs/football-analytics/fpl-elo-insights/data/draft_league/managers_20250811_224812.csv' DELIMITER ',' CSV HEADER;

-- Update league_id for managers
UPDATE draft_managers SET league_id = 25029 WHERE league_id IS NULL;

-- Import picks (use the latest CSV file) - map CSV columns to table columns
-- CSV: element,in_accepted_trade,owner,status -> Table: element_id,league_id,owner,status
\copy draft_picks(element_id, owner, status) FROM '/Users/rohanwalyat/Library/Mobile Documents/com~apple~CloudDocs/football-analytics/fpl-elo-insights/data/draft_league/picks_20250811_224812.csv' DELIMITER ',' CSV HEADER;

-- Update league_id for picks
UPDATE draft_picks SET league_id = 25029 WHERE league_id IS NULL;

-- Import standings (use the latest CSV file)
\copy draft_standings(entry_id, entry_name, player_name, rank, last_rank, rank_sort, total, event_total) FROM '/Users/rohanwalyat/Library/Mobile Documents/com~apple~CloudDocs/football-analytics/fpl-elo-insights/data/draft_league/standings_20250811_224812.csv' DELIMITER ',' CSV HEADER;

-- Update league_id for standings
UPDATE draft_standings SET league_id = 25029 WHERE league_id IS NULL;