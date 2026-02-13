
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from urllib.parse import quote_plus

def get_db_connection():
    """Create database connection using sqlalchemy."""
    user = os.getenv('PGUSER', 'postgres')
    password = os.getenv('PGPASSWORD', 'Simonsays@123')
    host = os.getenv('PGHOST', 'localhost')
    port = os.getenv('PGPORT', '5432')
    db = os.getenv('PGDATABASE', 'fpl_elo')
    
    encoded_password = quote_plus(password)
    conn_str = f'postgresql://{user}:{encoded_password}@{host}:{port}/{db}'
    engine = create_engine(conn_str)
    return engine

def fetch_data(engine):
    """Fetch necessary data from database."""
    print("Fetching data...")
    
    # 1. Matches with Elo ratings and Gameweek info
    matches_query = """
    SELECT 
        m.match_id,
        m.gameweek,
        m.kickoff_time,
        m.home_team as home_team_id,
        m.away_team as away_team_id,
        m.home_team_elo,
        m.away_team_elo
    FROM matches m
    WHERE m.finished = true
    ORDER BY m.kickoff_time
    """
    matches_df = pd.read_sql(matches_query, engine)
    
    # 2. Player Match Stats (Detailed per-match data)
    # Note: cast m.id to varchar to match pms.match_id if needed, or vice-versa. 
    # Checking types: matches.id is integer, pms.match_id is varchar usually.
    pms_query = """
    SELECT 
        pms.player_id,
        pms.match_id,
        pms.minutes_played,
        pms.goals,
        pms.assists,
        pms.xg,
        pms.xa,
        pms.xgot,
        pms.shots_on_target,
        pms.chances_created as key_passes,
        pms.saves,
        pms.goals_conceded
    FROM playermatchstats pms
    """
    pms_df = pd.read_sql(pms_query, engine)

    # 3. Player Gameweek Points (Target variable)
    pgw_query = """
    SELECT 
        player_id,
        gw as gameweek,
        total_points
    FROM player_gameweek_stats
    """
    pgw_df = pd.read_sql(pgw_query, engine)
    
    # 4. Players (Position, Team)
    players_query = """
    SELECT 
        player_id,
        web_name,
        position,
        team_code
    FROM players
    """
    players_df = pd.read_sql(players_query, engine)
    
    return matches_df, pms_df, pgw_df, players_df

def process_data(matches_df, pms_df, pgw_df, players_df):
    """Process and merge data to create a feature set."""
    print("Processing data...")
    
    # Check join keys types
    matches_df['match_id'] = matches_df['match_id'].astype(str)
    pms_df['match_id'] = pms_df['match_id'].astype(str)
    
    # Join PMS with Matches to get context (Gameweek, Elo, Home/Away)
    # We need to know which team the player belongs to to determine Home/Away and Elo
    # Join Players to PMS to get team_code
    pms_full = pms_df.merge(players_df, on='player_id', how='left')
    
    # Join with Matches
    # Note: matches has home_team_id/away_team_id. players has team_code. 
    # We might need a team mapping if team_code != team_id. 
    # Usually team_code is FPL code, team_id is internal ID. 
    # Assuming direct join might fail. Let's infer is_home/elo from match context if possible.
    # Actually, simpler: matches has home_team/away_team columns which usually match team IDs.
    
    joined_df = pms_full.merge(matches_df, on='match_id', how='inner')
    
    # Determine is_home and opponent elo
    # Getting team_id from players table might be tricky if it's FPL code. 
    # Let's assume we can map team_code or ID. 
    # Wait, `players` table has `team_code`. `matches` table uses `home_team` (id) and `away_team` (id).
    # We need a `teams` table to map code to id.
    # Let's fetch teams table.
    
    return joined_df

def create_features(df):
    """Create rolling features and lag targets."""
    # Logic to calculate rolling avgs per player
    # ...
    return df

if __name__ == "__main__":
    engine = get_db_connection()
    try:
        # Fetch data
        matches_df, pms_df, pgw_df, players_df = fetch_data(engine)
        
        # We need teams table to map team_code to team_id for correct Home/Away identification
        teams_df = pd.read_sql("SELECT id, code FROM teams", engine)
        
        # Merge logic
        # Map player team_code -> team_id
        players_df = players_df.merge(teams_df, left_on='team_code', right_on='code', how='left').rename(columns={'id': 'team_id'})
        
        # Merge back
        pms_full = pms_df.merge(players_df[['player_id', 'web_name', 'position', 'team_id']], on='player_id', how='left')
        
        # Convert match_id to string for merging
        matches_df['match_id'] = matches_df['match_id'].astype(str)
        pms_full['match_id'] = pms_full['match_id'].astype(str)
        
        # Merge with matches
        data = pms_full.merge(matches_df, on='match_id', how='inner')
        
        # Calculate context features
        data['is_home'] = (data['team_id'] == data['home_team_id']).astype(int)
        
        conditions = [
            (data['team_id'] == data['home_team_id']),
            (data['team_id'] == data['away_team_id'])
        ]
        choices_elo = [data['home_team_elo'], data['away_team_elo']]
        choices_opp_elo = [data['away_team_elo'], data['home_team_elo']]
        choices_opp_id = [data['away_team_id'], data['home_team_id']]
        
        data['team_elo'] = np.select(conditions, choices_elo, default=np.nan)
        data['opponent_elo'] = np.select(conditions, choices_opp_elo, default=np.nan)
        data['opponent_id'] = np.select(conditions, choices_opp_id, default=np.nan)
        data['elo_diff'] = data['team_elo'] - data['opponent_elo']

        # ---------------------------------------------------------
        # NEW: Opponent Defensive Strength (xGA)
        # ---------------------------------------------------------
        print("Calculating Opponent Defensive Strength...")
        # 1. Calculate Team xG per match
        team_stats = data.groupby(['match_id', 'team_id', 'kickoff_time'])['xg'].sum().reset_index().rename(columns={'xg': 'team_xg'})
        
        # 2. Get Matches to link Opponents
        # match_id is string in data/team_stats
        matches_link = matches_df[['match_id', 'home_team_id', 'away_team_id']].copy()
        
        # Merge to get Home/Away info
        team_stats = team_stats.merge(matches_link, on='match_id', how='left')
        
        # Identify Opponent ID
        team_stats['opponent_id'] = np.where(
            team_stats['team_id'] == team_stats['home_team_id'], 
            team_stats['away_team_id'], 
            team_stats['home_team_id']
        )
        
        # Self-join to get Opponent's xG (which is My xGA)
        # We need (match_id, team_id_of_opponent) -> xg
        opponent_xg = team_stats[['match_id', 'team_id', 'team_xg']].rename(columns={'team_id': 'opponent_id', 'team_xg': 'team_xga'})
        
        # Join back to team_stats
        team_def_stats = team_stats.merge(opponent_xg, on=['match_id', 'opponent_id'], how='left')
        
        # Sort for rolling
        team_def_stats = team_def_stats.sort_values(by=['team_id', 'kickoff_time'])
        
        # Calculate Rolling xGA for the team (Defensive Weakness)
        # EWMA Span 5 (~3 game rolling average with recency bias)
        team_def_stats['team_xga_ewm_5'] = team_def_stats.groupby('team_id')['team_xga'].transform(
            lambda x: x.shift().ewm(span=5, adjust=False).mean()
        )
        
        # Now we have 'team_xga_ewm_5' for every team.
        # We want to join this to the player data as 'opponent_def_strength'
        # So for a player, we match on [match_id, opponent_id] == [match_id, team_id] in team_def_stats
        # Or simpler: merge on opponent_id + match_id
        
        opp_strength_map = team_def_stats[['match_id', 'team_id', 'team_xga_ewm_5']].rename(
            columns={'team_id': 'opponent_id', 'team_xga_ewm_5': 'opponent_def_strength_roll_5'}
        )
        
        # Merge into main data
        # Ensure ID types match (opponent_id in data is float from np.select, convert to match)
        data['opponent_id'] = data['opponent_id'].astype(float)
        opp_strength_map['opponent_id'] = opp_strength_map['opponent_id'].astype(float)
        
        data = data.merge(opp_strength_map, on=['match_id', 'opponent_id'], how='left')
        
        # Fill NaN for early weeks with average? Or just 0
        data['opponent_def_strength_roll_5'] = data['opponent_def_strength_roll_5'].fillna(1.2) # League avg approx

        # Prepare for rolling calculations
        # Sort by player and kickoff time
        data = data.sort_values(by=['player_id', 'kickoff_time'])
        
        # Numeric columns to roll
        roll_cols = ['minutes_played', 'goals', 'assists', 'xg', 'xa', 'xgot', 'shots_on_target', 
                     'key_passes', 'saves', 'goals_conceded']
        
        # Rolling averages (switch to EWMA)
        # Span 3 = Fast reaction, Span 5 = Balanced
        for r in [3, 5]:
            grouped = data.groupby('player_id')[roll_cols].transform(
                lambda x: x.shift().ewm(span=r, adjust=False).mean()
            )
            grouped.columns = [f'{col}_roll_{r}' for col in grouped.columns]
            data = pd.concat([data, grouped], axis=1)
        
        # Lag features (last match performance)
        lag_cols = roll_cols + ['total_points'] 
        
        data = data.merge(pgw_df, on=['player_id', 'gameweek'], how='left')
        
        # Add rolling points (form)
        data['total_points_roll_3'] = data.groupby('player_id')['total_points'].transform(
            lambda x: x.shift().ewm(span=3, adjust=False).mean()
        )
        
        # Create target
        data = data.sort_values(by=['player_id', 'kickoff_time'])
        data['target_points_next'] = data.groupby('player_id')['total_points'].shift(-1)
        
        # Drop rows where target is NaN (last game has no next game)
        # Also drop rows where next game is too far away? (optional)
        
        train_data = data.dropna(subset=['target_points_next'])
        
        print(f"Prepared training data: {train_data.shape}")
        
        # Save to CSV for training
        output_path = 'data/models/training_data.csv'
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        train_data.to_csv(output_path, index=False)
        print(f"Saved to {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
