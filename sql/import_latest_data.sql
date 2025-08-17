-- Import latest 2025-2026 season data
-- This script imports the current season data from the correct paths

-- Clear existing data (optional - uncomment if you want to refresh all data)
-- TRUNCATE TABLE playermatchstats;
-- TRUNCATE TABLE matches;  
-- TRUNCATE TABLE players;
-- TRUNCATE TABLE teams;

-- Import teams data (base reference data)
\copy teams(code, id, name, short_name, strength, strength_overall_home, strength_overall_away, strength_attack_home, strength_attack_away, strength_defence_home, strength_defence_away, pulse_id, elo) FROM '/Users/rohanwalyat/football-analytics/fpl-elo-insights/data/2025-2026/teams.csv' DELIMITER ',' CSV HEADER;

-- Import players data (base reference data)  
\copy players(player_code, player_id, first_name, second_name, web_name, team_code, position) FROM '/Users/rohanwalyat/football-analytics/fpl-elo-insights/data/2025-2026/players.csv' DELIMITER ',' CSV HEADER;

-- Import GW1 matches data (most recent completed gameweek)
\copy matches(gameweek, kickoff_time, home_team, home_team_elo, home_score, away_score, away_team, away_team_elo, finished, match_id, home_possession, away_possession, home_expected_goals_xg, away_expected_goals_xg, home_total_shots, away_total_shots, home_shots_on_target, away_shots_on_target, home_big_chances, away_big_chances, home_big_chances_missed, away_big_chances_missed, home_accurate_passes, away_accurate_passes, home_accurate_passes_pct, away_accurate_passes_pct, home_fouls_committed, away_fouls_committed, home_corners, away_corners, home_xg_open_play, away_xg_open_play, home_xg_set_play, away_xg_set_play, home_non_penalty_xg, away_non_penalty_xg, home_xg_on_target_xgot, away_xg_on_target_xgot, home_shots_off_target, away_shots_off_target, home_blocked_shots, away_blocked_shots, home_hit_woodwork, away_hit_woodwork, home_shots_inside_box, away_shots_inside_box, home_shots_outside_box, away_shots_outside_box, home_passes, away_passes, home_own_half, away_own_half, home_opposition_half, away_opposition_half, home_accurate_long_balls, away_accurate_long_balls, home_accurate_long_balls_pct, away_accurate_long_balls_pct, home_accurate_crosses, away_accurate_crosses, home_accurate_crosses_pct, away_accurate_crosses_pct, home_throws, away_throws, home_touches_in_opposition_box, away_touches_in_opposition_box, home_offsides, away_offsides, home_yellow_cards, away_yellow_cards, home_red_cards, away_red_cards, home_tackles_won, away_tackles_won, home_tackles_won_pct, away_tackles_won_pct, home_interceptions, away_interceptions, home_blocks, away_blocks, home_clearances, away_clearances, home_keeper_saves, away_keeper_saves, home_duels_won, away_duels_won, home_ground_duels_won, away_ground_duels_won, home_ground_duels_won_pct, away_ground_duels_won_pct, home_aerial_duels_won, away_aerial_duels_won, home_aerial_duels_won_pct, away_aerial_duels_won_pct, home_successful_dribbles, away_successful_dribbles, home_successful_dribbles_pct, away_successful_dribbles_pct, stats_processed, player_stats_processed, home_distance_covered, away_distance_covered, home_walking_distance, away_walking_distance, home_running_distance, away_running_distance, home_sprinting_distance, away_sprinting_distance, home_number_of_sprints, away_number_of_sprints, home_top_speed, away_top_speed) FROM '/Users/rohanwalyat/football-analytics/fpl-elo-insights/data/2025-2026/By Gameweek/GW1/matches.csv' DELIMITER ',' CSV HEADER;

-- Import GW1 playermatchstats data (most recent completed gameweek)
\copy playermatchstats(player_id, match_id, minutes_played, goals, assists, total_shots, xg, xa, xgot, shots_on_target, successful_dribbles, big_chances_missed, touches_opposition_box, touches, accurate_passes, chances_created, final_third_passes, accurate_crosses, accurate_long_balls, tackles_won, interceptions, recoveries, blocks, clearances, headed_clearances, dribbled_past, duels_won, duels_lost, ground_duels_won, aerial_duels_won, was_fouled, fouls_committed, saves, goals_conceded, xgot_faced, goals_prevented, sweeper_actions, gk_accurate_passes, gk_accurate_long_balls, offsides, high_claim, tackles, accurate_passes_percent, accurate_crosses_percent, accurate_long_balls_percent, ground_duels_won_percent, aerial_duels_won_percent, successful_dribbles_percent, tackles_won_percent, start_min, finish_min, team_goals_conceded, penalties_scored, penalties_missed) FROM '/Users/rohanwalyat/football-analytics/fpl-elo-insights/data/2025-2026/By Gameweek/GW1/playermatchstats.csv' DELIMITER ',' CSV HEADER;

-- Display import summary
SELECT 'Teams imported:' as description, COUNT(*) as count FROM teams
UNION ALL
SELECT 'Players imported:', COUNT(*) FROM players  
UNION ALL
SELECT 'Matches imported:', COUNT(*) FROM matches
UNION ALL
SELECT 'Player match stats imported:', COUNT(*) FROM playermatchstats;