
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_squared_error, mean_absolute_error
import joblib
import os

def load_data(path):
    return pd.read_csv(path)

def train_model():
    data_path = 'data/models/training_data.csv'
    if not os.path.exists(data_path):
        print("Training data not found. Run feature_engineering.py first.")
        return

    df = load_data(data_path)
    
    # Feature Selection Configuration
    # Base excluded columns
    exclude_cols = ['player_id', 'match_id', 'gameweek', 'kickoff_time', 
                    'home_team_id', 'away_team_id', 'team_id', 'web_name', 
                    'home_team_elo', 'away_team_elo', 'team_elo', 'opponent_elo',
                    'target_points_next', 'total_points_lag1', 'opponent_id', 'position', 'pos_1', 'pos_2', 'pos_3', 'pos_4'] 
    
    # Feature sets per position (can be customized)
    # For now, we'll start with all available rolling features but could be refined
    # GKP: Saves, Conceded, Minutes
    # DEF: Clean Sheets (if avail), Conceded, Minutes, xA
    # MID/FWD: xG, xA, Shots, Key Passes
    
    # Let's define the loop
    positions = {
        1: 'GKP',
        2: 'DEF',
        3: 'MID',
        4: 'FWD'
    }
    
    # Map string positions to IDs if needed
    if df['position'].dtype == 'O':
        pos_map_str = {
            'Goalkeeper': 1,
            'Defender': 2,
            'Midfielder': 3,
            'Forward': 4,
            'GKP': 1, 'DEF': 2, 'MID': 3, 'FWD': 4
        }
        df['position'] = df['position'].map(pos_map_str)
        print("Mapped string positions to IDs.")
    
    target_col = 'target_points_next'
    
    # Initialize importance dataframe
    all_importances = pd.DataFrame()

    for pos_id, pos_name in positions.items():
        print(f"\nTraining model for {pos_name}...")
        
        # Filter data for this position
        pos_df = df[df['position'] == pos_id].copy()
        
        if pos_df.empty:
            print(f"No data for {pos_name}, skipping.")
            continue
            
        # Select Features (Automated based on exclusion)
        feature_cols = [c for c in pos_df.columns if c not in exclude_cols]
        
        # You could customize feature_cols here based on pos_name if desired
        
        # Split Train/Test Chronologically
        max_gw = pos_df['gameweek'].max()
        test_gw_start = max_gw - 3
        
        train_df = pos_df[pos_df['gameweek'] < test_gw_start]
        test_df = pos_df[pos_df['gameweek'] >= test_gw_start]
        
        X_train = train_df[feature_cols]
        y_train = train_df[target_col]
        X_test = test_df[feature_cols]
        y_test = test_df[target_col]
        
        print(f"  Train stats: {len(X_train)} rows. Test stats: {len(X_test)} rows (GW {test_gw_start}+)")
        
        # Train HistGradientBoostingRegressor
        model = HistGradientBoostingRegressor(
            max_iter=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        
        # Evaluation
        preds = model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        mae = mean_absolute_error(y_test, preds)
        
        print(f"  {pos_name} Test RMSE: {rmse:.4f}")
        print(f"  {pos_name} Test MAE: {mae:.4f}")
        
        # Save Model
        model_filename = f'data/models/xgb_model_{pos_name}.pkl'
        cols_filename = f'data/models/feature_cols_{pos_name}.pkl'
        
        joblib.dump(model, model_filename)
        joblib.dump(feature_cols, cols_filename)
        print(f"  Saved model to {model_filename}")
        
        # Feature Importance (Permutation)
        result = permutation_importance(model, X_test, y_test, n_repeats=5, random_state=42, n_jobs=2)
        
        importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': result.importances_mean,
            'position': pos_name
        }).sort_values('importance', ascending=False)
        
        print(f"  Top 3 Features: {importance['feature'].head(3).tolist()}")
        all_importances = pd.concat([all_importances, importance])

    # Save aggregated importance
    all_importances.to_csv('data/models/feature_importance.csv', index=False)
    print("\nFeature importance saved to data/models/feature_importance.csv")

if __name__ == "__main__":
    train_model()
