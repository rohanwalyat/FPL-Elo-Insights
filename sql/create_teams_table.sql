CREATE TABLE teams (
    code INTEGER PRIMARY KEY,
    id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(10) NOT NULL,
    strength INTEGER NOT NULL,
    strength_overall_home INTEGER NOT NULL,
    strength_overall_away INTEGER NOT NULL,
    strength_attack_home INTEGER NOT NULL,
    strength_attack_away INTEGER NOT NULL,
    strength_defence_home INTEGER NOT NULL,
    strength_defence_away INTEGER NOT NULL,
    pulse_id INTEGER NOT NULL,
    elo INTEGER NOT NULL
);

-- Create indexes for common query patterns
CREATE INDEX idx_teams_id ON teams(id);
CREATE INDEX idx_teams_name ON teams(name);
CREATE INDEX idx_teams_short_name ON teams(short_name);
CREATE INDEX idx_teams_elo ON teams(elo);
CREATE INDEX idx_teams_pulse_id ON teams(pulse_id);