CREATE TABLE playermatchstats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    match_id VARCHAR(100) NOT NULL,
    minutes_played INTEGER NOT NULL,
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    total_shots INTEGER DEFAULT 0,
    xg DECIMAL(5,2) DEFAULT 0,
    xa DECIMAL(5,2) DEFAULT 0,
    xgot DECIMAL(5,2) DEFAULT 0,
    shots_on_target INTEGER DEFAULT 0,
    successful_dribbles INTEGER DEFAULT 0,
    big_chances_missed INTEGER DEFAULT 0,
    touches_opposition_box INTEGER DEFAULT 0,
    touches INTEGER DEFAULT 0,
    accurate_passes INTEGER DEFAULT 0,
    chances_created INTEGER DEFAULT 0,
    final_third_passes INTEGER DEFAULT 0,
    accurate_crosses INTEGER DEFAULT 0,
    accurate_long_balls INTEGER DEFAULT 0,
    tackles_won INTEGER DEFAULT 0,
    interceptions INTEGER DEFAULT 0,
    recoveries INTEGER DEFAULT 0,
    blocks INTEGER DEFAULT 0,
    clearances INTEGER DEFAULT 0,
    headed_clearances INTEGER DEFAULT 0,
    dribbled_past INTEGER DEFAULT 0,
    duels_won INTEGER DEFAULT 0,
    duels_lost INTEGER DEFAULT 0,
    ground_duels_won INTEGER DEFAULT 0,
    aerial_duels_won INTEGER DEFAULT 0,
    was_fouled INTEGER DEFAULT 0,
    fouls_committed INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    goals_conceded INTEGER DEFAULT 0,
    xgot_faced DECIMAL(5,2) DEFAULT 0,
    goals_prevented DECIMAL(5,2) DEFAULT 0,
    sweeper_actions INTEGER DEFAULT 0,
    gk_accurate_passes INTEGER DEFAULT 0,
    gk_accurate_long_balls INTEGER DEFAULT 0,
    offsides INTEGER DEFAULT 0,
    high_claim INTEGER DEFAULT 0,
    tackles INTEGER DEFAULT 0,
    accurate_passes_percent INTEGER DEFAULT 0,
    accurate_crosses_percent INTEGER DEFAULT 0,
    accurate_long_balls_percent INTEGER DEFAULT 0,
    ground_duels_won_percent INTEGER DEFAULT 0,
    aerial_duels_won_percent INTEGER DEFAULT 0,
    successful_dribbles_percent INTEGER DEFAULT 0,
    tackles_won_percent INTEGER DEFAULT 0,
    start_min INTEGER DEFAULT 0,
    finish_min INTEGER DEFAULT 0,
    team_goals_conceded INTEGER DEFAULT 0,
    penalties_scored INTEGER DEFAULT 0,
    penalties_missed INTEGER DEFAULT 0
);

-- Create indexes for common query patterns
CREATE INDEX idx_playermatchstats_player_id ON playermatchstats(player_id);
CREATE INDEX idx_playermatchstats_match_id ON playermatchstats(match_id);
CREATE INDEX idx_playermatchstats_player_match ON playermatchstats(player_id, match_id);
CREATE INDEX idx_playermatchstats_minutes_played ON playermatchstats(minutes_played);
CREATE INDEX idx_playermatchstats_goals ON playermatchstats(goals);
CREATE INDEX idx_playermatchstats_assists ON playermatchstats(assists);

-- Add foreign key constraints (commented out for initial load)
-- ALTER TABLE playermatchstats ADD CONSTRAINT fk_playermatchstats_match 
--     FOREIGN KEY (match_id) REFERENCES matches(match_id);