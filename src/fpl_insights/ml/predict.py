
import pandas as pd
import numpy as np
import joblib
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

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

def predict_next_gw():
    # Load separate models per position
    models = {}
    feature_cols = {}
    positions = {'GKP': 1, 'DEF': 2, 'MID': 3, 'FWD': 4}
    
    try:
        for pos_name in positions.keys():
            models[pos_name] = joblib.load(f'data/models/xgb_model_{pos_name}.pkl')
            feature_cols[pos_name] = joblib.load(f'data/models/feature_cols_{pos_name}.pkl')
        print("Loaded 4 position-specific models.")
    except Exception as e:
        print(f"Error loading models: {e}")
        return

    # Load latest rolling stats from training data
    train_df = pd.read_csv('data/models/training_data.csv')
    train_df = train_df.sort_values('kickoff_time')
    
    # helper: EWMA recursive update
    # y_t = alpha * x_t + (1 - alpha) * y_{t-1}
    def update_ewma(prev_ewma, new_val, span):
        if pd.isna(prev_ewma): return new_val # seed
        alpha = 2 / (span + 1)
        return alpha * new_val + (1 - alpha) * prev_ewma

    print("Calculating next match features (EWMA update)...")
    
    roll_cols = ['minutes_played', 'goals', 'assists', 'xg', 'xa', 'xgot', 'shots_on_target', 
                 'key_passes', 'saves', 'goals_conceded']
    
    # Calculate latest features for each player
    # We take the LAST row for each player. 
    # The columns "{col}_roll_{r}" in that row represent the EWMA entering that match.
    # We want the EWMA entering the NEXT match.
    # So we take that value, and update it with the actual stats from that match.
    
    latest_features = {}
    
    # 1. Player Features
    for player_id, group in train_df.groupby('player_id'):
        last_row = group.iloc[-1]
        
        feats = {'player_id': player_id}
        
        # Static
        for c in group.columns:
            if c.startswith('pos_') or c == 'position':
                feats[c] = last_row[c]
        
        # Numeric Rolling
        for col in roll_cols:
            val_now = last_row[col] # Stats from the last match
            
            for r in [3, 5]:
                prev_roll = last_row.get(f'{col}_roll_{r}', np.nan)
                # Update
                new_roll = update_ewma(prev_roll, val_now, r)
                feats[f'{col}_roll_{r}'] = new_roll
        
        # Lagged points form
        # total_points_roll_3 describes form entering last match. Update with last match points.
        val_pts = last_row['total_points']
        prev_pts_roll = last_row.get('total_points_roll_3', np.nan)
        feats['total_points_roll_3'] = update_ewma(prev_pts_roll, val_pts, 3)
        
        feats['total_points_lag1'] = val_pts
        
        latest_features[player_id] = feats

    latest_features_df = pd.DataFrame.from_dict(latest_features, orient='index')

    # 2. Team Defensive Strength (Opponent Strength)
    # We need the latest strength for every team ID.
    # In training data, 'opponent_id' is the team ID of the opponent.
    # 'opponent_def_strength_roll_5' is that team's strength entering the match.
    # We can update it with their xGA from that match.
    # But xGA isn't explicitly in the row... we derived it in feature engineering.
    # Approximation: Just take the last known 'opponent_def_strength_roll_5' for that team.
    
    team_strengths = {}
    # Iterate over all matches to find the last time a team played (as opponent)
    # This is slightly inefficient but robust
    
    # Group by opponent_id, take last row
    # (Assuming opponent_id covers all teams at some point)
    last_ops = train_df.drop_duplicates(subset=['opponent_id'], keep='last')
    for _, row in last_ops.iterrows():
        tid = row['opponent_id']
        strength = row['opponent_def_strength_roll_5']
        team_strengths[tid] = strength
        
    # Also check if any teams appear as 'team_id' but never 'opponent_id' (unlikely)
    
    # Now join with Next Fixtures
    print("Fetching next fixtures...")
    engine = get_db_connection()
    
    next_fixtures_query = """
    SELECT 
        m.match_id,
        m.gameweek,
        m.kickoff_time,
        m.home_team as home_team_id,
        m.away_team as away_team_id,
        m.home_team_elo,
        m.away_team_elo
    FROM matches m
    WHERE m.finished = false
    ORDER BY m.kickoff_time
    """
    next_fixtures = pd.read_sql(next_fixtures_query, engine)
    
    players_query = """
    SELECT player_id, team_code, web_name FROM players
    """
    players_df = pd.read_sql(players_query, engine)
    
    teams_query = "SELECT id as team_id, code as team_code FROM teams"
    teams_df = pd.read_sql(teams_query, engine)
    
    players_full = players_df.merge(teams_df, on='team_code', how='left')
    
    predictions = []
    
    for _, player in players_full.iterrows():
        p_id = player['player_id']
        t_id = player['team_id']
        
        # Find next match for this team
        next_match = next_fixtures[
            (next_fixtures['home_team_id'] == t_id) | 
            (next_fixtures['away_team_id'] == t_id)
        ].head(1)
        
        if next_match.empty:
            continue
            
        next_match = next_match.iloc[0]
        
        # Get features
        if p_id in latest_features:
            feats = latest_features[p_id].copy()
        else:
            continue # New player
            
        # Add context features
        is_home = 1 if next_match['home_team_id'] == t_id else 0
        feats['is_home'] = is_home
        
        opp_id = next_match['away_team_id'] if is_home else next_match['home_team_id']
        feats['opponent_id'] = opp_id
        
        if is_home:
            feats['team_elo'] = next_match['home_team_elo']
            feats['opponent_elo'] = next_match['away_team_elo']
        else:
            feats['team_elo'] = next_match['away_team_elo']
            feats['opponent_elo'] = next_match['home_team_elo']
            
        feats['elo_diff'] = feats['team_elo'] - feats['opponent_elo']
        
        # Add Opponent Strength
        # Default to 1.2 if unknown (league avg)
        feats['opponent_def_strength_roll_5'] = team_strengths.get(opp_id, 1.2)
        
        # Metadata
        feats['player_id'] = p_id
        feats['web_name'] = player['web_name']
        feats['gameweek'] = next_match['gameweek']
        feats['match_id'] = next_match['match_id']
        
        # Determine strict position for model selection
        # feature_engineering might have mapped it to 1,2,3,4 or kept string
        # Let's rely on 'position' column if it exists, or infer?
        # players_full doesn't have position column.
        # But 'feats' has 'position' from training data.
        
        pos_val = feats.get('position')
        
        # Map to GKP/DEF/MID/FWD key
        pos_key = None
        if pos_val in [1, 'Goalkeeper', 'GKP']: pos_key = 'GKP'
        elif pos_val in [2, 'Defender', 'DEF']: pos_key = 'DEF'
        elif pos_val in [3, 'Midfielder', 'MID']: pos_key = 'MID'
        elif pos_val in [4, 'Forward', 'FWD']: pos_key = 'FWD'
        
        if pos_key:
            feats['model_pos'] = pos_key
            predictions.append(feats)
        
    pred_df = pd.DataFrame(predictions)
    
    if pred_df.empty:
        print("No predictions to make.")
        return

    # PREDICT using separate models
    final_preds = []
    
    print("Generating predictions...")
    for pos_key, group_df in pred_df.groupby('model_pos'):
        model = models.get(pos_key)
        f_cols = feature_cols.get(pos_key)
        
        if not model:
            print(f"Model for {pos_key} not found, skipping.")
            continue
            
        # Fill missing cols
        for c in f_cols:
            if c not in group_df.columns:
                group_df[c] = 0
        
        X = group_df[f_cols]
        preds = model.predict(X)
        
        group_df['ml_xp'] = preds
        final_preds.append(group_df)
        
    if not final_preds:
        print("No predictions generated.")
        return
        
    final_df = pd.concat(final_preds)
    
    # Save to Database
    print("Saving to database...")
    output_cols = ['player_id', 'web_name', 'gameweek', 'ml_xp']
    engine = get_db_connection()
    final_df[output_cols].to_sql('ml_projections', engine, if_exists='replace', index=False)
    print(f"Saved {len(final_df)} predictions to table 'ml_projections'")


if __name__ == "__main__":
    predict_next_gw()
