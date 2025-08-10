CREATE TABLE players (
    player_code INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    second_name VARCHAR(100) NOT NULL,
    web_name VARCHAR(100) NOT NULL,
    team_code INTEGER NOT NULL,
    position VARCHAR(20) NOT NULL
);

-- Create indexes for common query patterns
CREATE INDEX idx_players_player_id ON players(player_id);
CREATE INDEX idx_players_team_code ON players(team_code);
CREATE INDEX idx_players_position ON players(position);
CREATE INDEX idx_players_web_name ON players(web_name);