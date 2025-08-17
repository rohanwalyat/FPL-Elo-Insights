#!/usr/bin/env python3
"""
Import 2025-2026 season data into PostgreSQL database
Handles column mapping and data type conversion
"""

import pandas as pd
import psycopg2
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        database=os.getenv('PGDATABASE', 'fpl_elo'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD')
    )

def import_matches_data():
    """Import GW1 matches data with proper column mapping"""
    print("Importing GW1 matches data...")
    
    # Load matches CSV
    matches_df = pd.read_csv('data/2025-2026/By Gameweek/GW1/matches.csv')
    
    # Map to database columns (excluding new columns that don't exist in DB)
    db_columns = [
        'gameweek', 'kickoff_time', 'home_team', 'home_team_elo', 'home_score', 
        'away_score', 'away_team', 'away_team_elo', 'finished', 'match_id',
        'home_possession', 'away_possession', 'home_expected_goals_xg', 'away_expected_goals_xg',
        'home_total_shots', 'away_total_shots', 'home_shots_on_target', 'away_shots_on_target',
        'home_big_chances', 'away_big_chances', 'home_big_chances_missed', 'away_big_chances_missed',
        'home_accurate_passes', 'away_accurate_passes', 'home_accurate_passes_pct', 'away_accurate_passes_pct',
        'home_fouls_committed', 'away_fouls_committed', 'home_corners', 'away_corners',
        'home_xg_open_play', 'away_xg_open_play', 'home_xg_set_play', 'away_xg_set_play',
        'home_non_penalty_xg', 'away_non_penalty_xg', 'home_xg_on_target_xgot', 'away_xg_on_target_xgot',
        'home_shots_off_target', 'away_shots_off_target', 'home_blocked_shots', 'away_blocked_shots',
        'home_hit_woodwork', 'away_hit_woodwork', 'home_shots_inside_box', 'away_shots_inside_box',
        'home_shots_outside_box', 'away_shots_outside_box', 'home_passes', 'away_passes',
        'home_own_half', 'away_own_half', 'home_opposition_half', 'away_opposition_half',
        'home_accurate_long_balls', 'away_accurate_long_balls', 'home_accurate_long_balls_pct', 'away_accurate_long_balls_pct',
        'home_accurate_crosses', 'away_accurate_crosses', 'home_accurate_crosses_pct', 'away_accurate_crosses_pct',
        'home_throws', 'away_throws', 'home_touches_in_opposition_box', 'away_touches_in_opposition_box',
        'home_offsides', 'away_offsides', 'home_yellow_cards', 'away_yellow_cards',
        'home_red_cards', 'away_red_cards', 'home_tackles_won', 'away_tackles_won',
        'home_tackles_won_pct', 'away_tackles_won_pct', 'home_interceptions', 'away_interceptions',
        'home_blocks', 'away_blocks', 'home_clearances', 'away_clearances',
        'home_keeper_saves', 'away_keeper_saves', 'home_duels_won', 'away_duels_won',
        'home_ground_duels_won', 'away_ground_duels_won', 'home_ground_duels_won_pct', 'away_ground_duels_won_pct',
        'home_aerial_duels_won', 'away_aerial_duels_won', 'home_aerial_duels_won_pct', 'away_aerial_duels_won_pct',
        'home_successful_dribbles', 'away_successful_dribbles', 'home_successful_dribbles_pct', 'away_successful_dribbles_pct',
        'stats_processed', 'player_stats_processed'
    ]
    
    # Filter to only columns that exist in both CSV and database
    available_columns = [col for col in db_columns if col in matches_df.columns]
    filtered_df = matches_df[available_columns].copy()
    
    # Handle data types
    filtered_df['finished'] = filtered_df['finished'].astype(bool)
    
    conn = get_db_connection()
    try:
        # Insert data
        with conn.cursor() as cur:
            # Create column list and placeholders
            cols = ', '.join(available_columns)
            placeholders = ', '.join(['%s'] * len(available_columns))
            
            insert_query = f"INSERT INTO matches ({cols}) VALUES ({placeholders})"
            
            # Insert each row
            for _, row in filtered_df.iterrows():
                cur.execute(insert_query, tuple(row))
            
            conn.commit()
            print(f"✅ Imported {len(filtered_df)} matches")
            
    except Exception as e:
        print(f"❌ Error importing matches: {e}")
        conn.rollback()
    finally:
        conn.close()

def import_playermatchstats_data():
    """Import GW1 player match stats with proper column mapping"""
    print("Importing GW1 player match stats...")
    
    # Load player match stats CSV
    stats_df = pd.read_csv('data/2025-2026/By Gameweek/GW1/playermatchstats.csv')
    
    # Map to database columns (excluding new columns)
    db_columns = [
        'player_id', 'match_id', 'minutes_played', 'goals', 'assists', 'total_shots',
        'xg', 'xa', 'shots_on_target', 'successful_dribbles', 'big_chances_missed',
        'touches_opposition_box', 'touches', 'accurate_passes', 'accurate_passes_percent',
        'chances_created', 'final_third_passes', 'accurate_crosses', 'accurate_crosses_percent',
        'accurate_long_balls', 'accurate_long_balls_percent', 'tackles_won', 'interceptions',
        'recoveries', 'blocks', 'clearances', 'headed_clearances', 'dribbled_past',
        'duels_won', 'duels_lost', 'ground_duels_won', 'ground_duels_won_percent',
        'aerial_duels_won', 'aerial_duels_won_percent', 'was_fouled', 'fouls_committed',
        'saves', 'goals_conceded', 'xgot_faced', 'goals_prevented', 'sweeper_actions',
        'gk_accurate_passes', 'gk_accurate_long_balls', 'offsides', 'high_claim',
        'tackles', 'successful_dribbles_percent', 'tackles_won_percent', 'xgot',
        'start_min', 'finish_min', 'team_goals_conceded', 'penalties_scored', 'penalties_missed'
    ]
    
    # Filter to only columns that exist in both CSV and database
    available_columns = [col for col in db_columns if col in stats_df.columns]
    filtered_df = stats_df[available_columns].copy()
    
    # Handle missing columns - set defaults
    for col in db_columns:
        if col not in filtered_df.columns:
            if col in ['xg', 'xa', 'xgot', 'xgot_faced', 'goals_prevented']:
                filtered_df[col] = 0.0
            else:
                filtered_df[col] = 0
    
    # Reorder columns to match database expectation
    filtered_df = filtered_df[db_columns]
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Create column list and placeholders
            cols = ', '.join(db_columns)
            placeholders = ', '.join(['%s'] * len(db_columns))
            
            insert_query = f"INSERT INTO playermatchstats ({cols}) VALUES ({placeholders})"
            
            # Insert each row
            for _, row in filtered_df.iterrows():
                cur.execute(insert_query, tuple(row))
            
            conn.commit()
            print(f"✅ Imported {len(filtered_df)} player match stats")
            
    except Exception as e:
        print(f"❌ Error importing player match stats: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """Main import function"""
    print("🔄 Starting database import for 2025-2026 season data...")
    
    # Import matches and player stats (teams and players already imported)
    import_matches_data()
    import_playermatchstats_data()
    
    # Show final counts
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM teams")
            team_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM players") 
            player_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM matches")
            match_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM playermatchstats")
            stats_count = cur.fetchone()[0]
            
            print(f"\n📊 Final database counts:")
            print(f"   Teams: {team_count}")
            print(f"   Players: {player_count}")
            print(f"   Matches: {match_count}")
            print(f"   Player Match Stats: {stats_count}")
            
    finally:
        conn.close()
    
    print("\n✅ Database import completed!")

if __name__ == "__main__":
    main()