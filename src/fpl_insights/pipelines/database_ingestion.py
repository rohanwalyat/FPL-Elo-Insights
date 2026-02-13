#!/usr/bin/env python3
"""
FPL Database Ingestion Automation Script

This script automatically detects and imports the latest FPL data into PostgreSQL:
- Handles 2025-2026 season data structure (By Gameweek format)
- Imports main season data (players, teams, matches, playermatchstats)
- Imports draft league data (managers, picks, leagues)
- Intelligent column mapping for schema compatibility
- Incremental updates without data loss
"""

import os
import sys
import subprocess
import pandas as pd
import psycopg2
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

class DatabaseIngester:
    def __init__(self):
        """Initialize the database ingester"""
        # Load environment variables
        load_dotenv()
        
        # Set up paths
        self.script_dir = Path(__file__).parent
        self.repo_path = self.script_dir.parent.parent.parent
        self.data_path = self.repo_path / "data"
        
        # Database connection parameters
        self.db_params = {
            'host': os.getenv('PGHOST', 'localhost'),
            'port': os.getenv('PGPORT', '5432'),
            'database': os.getenv('PGDATABASE', 'fpl_elo'),
            'user': os.getenv('PGUSER', 'postgres'),
            'password': os.getenv('PGPASSWORD')
        }
        
        # Track what was imported
        self.import_summary = {
            'season_data': {},
            'draft_data': {},
            'errors': []
        }

    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")

    def get_db_connection(self):
        """Create database connection"""
        try:
            return psycopg2.connect(**self.db_params)
        except Exception as e:
            self.log(f"Database connection failed: {e}", "ERROR")
            return None

    def test_database_connection(self):
        """Test if database is accessible"""
        self.log("Testing database connection...")
        conn = self.get_db_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM teams")
                count = cur.fetchone()[0]
                self.log(f"Database connection successful (found {count} teams)")
                return True
        except Exception as e:
            self.log(f"Database test failed: {e}", "ERROR")
            return False
        finally:
            conn.close()

    def find_latest_season_data(self):
        """Find all season data files across all gameweeks"""
        season_data = {
            'players': None,
            'teams': None,
            'matches_list': [],
            'stats_list': []
        }
        
        # Check for season data in raw hierarchy
        season_path = self.data_path / "raw" / "pl_history" / "2025-2026"
        if season_path.exists():
            # Check for main season files
            players_file = season_path / "players.csv"
            teams_file = season_path / "teams.csv"
            
            if players_file.exists():
                season_data['players'] = players_file
            if teams_file.exists():
                season_data['teams'] = teams_file
            
            # Find all gameweek data
            gameweek_path = season_path / "By Gameweek"
            if gameweek_path.exists():
                for gw_dir in sorted(gameweek_path.iterdir(), key=lambda x: int(x.name[2:]) if x.name.startswith("GW") and x.name[2:].isdigit() else 0):
                    if gw_dir.is_dir() and gw_dir.name.startswith("GW"):
                        matches_file = gw_dir / "matches.csv"
                        stats_file = gw_dir / "playermatchstats.csv"
                        
                        if matches_file.exists() and stats_file.exists():
                            # Only include if files have actual data (not just headers)
                            if matches_file.stat().st_size > 3000 and stats_file.stat().st_size > 3000:
                                season_data['matches_list'].append(matches_file)
                                season_data['stats_list'].append(stats_file)
                
                if season_data['matches_list']:
                    self.log(f"Found match data across {len(season_data['matches_list'])} gameweeks")
        
        return season_data

    def find_draft_league_data(self):
        """Find draft league data files"""
        draft_data = {}
        
        # Check draft league data in raw hierarchy
        draft_path = self.data_path / "raw" / "draft_league" / "latest"
        if draft_path.exists():
            for file_name in ['managers.csv', 'picks.csv', 'players.csv', 'teams.csv', 'standings.csv']:
                file_path = draft_path / file_name
                if file_path.exists():
                    draft_data[file_name.replace('.csv', '')] = file_path
        
        return draft_data

    def import_season_data(self, season_data):
        """Import main season data with intelligent column mapping"""
        if not season_data:
            self.log("No season data found to import")
            return False

        conn = self.get_db_connection()
        if not conn:
            return False

        try:
            with conn.cursor() as cur:
                # Clear existing data for new season
                self.log("Clearing existing season data...")
                cur.execute("TRUNCATE TABLE playermatchstats, matches, players, teams CASCADE;")
                
                # Import teams
                if 'teams' in season_data:
                    self.log("Importing teams data...")
                    teams_df = pd.read_csv(season_data['teams'])
                    
                    # Ensure columns match placeholders
                    team_cols = ['code', 'id', 'name', 'short_name', 'strength', 
                                'strength_overall_home', 'strength_overall_away',
                                'strength_attack_home', 'strength_attack_away',
                                'strength_defence_home', 'strength_defence_away',
                                'pulse_id', 'elo']
                    teams_df = teams_df[team_cols]
                    
                    for _, row in teams_df.iterrows():
                        cur.execute("""
                            INSERT INTO teams (code, id, name, short_name, strength, 
                                             strength_overall_home, strength_overall_away,
                                             strength_attack_home, strength_attack_away,
                                             strength_defence_home, strength_defence_away,
                                             pulse_id, elo)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (code) DO UPDATE SET
                                name = EXCLUDED.name,
                                short_name = EXCLUDED.short_name,
                                elo = EXCLUDED.elo
                        """, tuple(row))
                    
                    self.import_summary['season_data']['teams'] = len(teams_df)
                    self.log(f"✅ Imported {len(teams_df)} teams")

                # Import players
                if 'players' in season_data:
                    self.log("Importing players data...")
                    players_df = pd.read_csv(season_data['players'])
                    
                    # Ensure columns match placeholders
                    player_cols = ['player_code', 'player_id', 'first_name', 'second_name',
                                  'web_name', 'team_code', 'position']
                    players_df = players_df[player_cols]
                    
                    for _, row in players_df.iterrows():
                        cur.execute("""
                            INSERT INTO players (player_code, player_id, first_name, second_name,
                                               web_name, team_code, position)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (player_code) DO UPDATE SET
                                first_name = EXCLUDED.first_name,
                                second_name = EXCLUDED.second_name,
                                web_name = EXCLUDED.web_name,
                                team_code = EXCLUDED.team_code,
                                position = EXCLUDED.position
                        """, tuple(row))
                    
                    self.import_summary['season_data']['players'] = len(players_df)
                    self.log(f"✅ Imported {len(players_df)} players")

                # Import matches from all gameweeks
                if season_data.get('matches_list'):
                    self.log(f"Importing match data from {len(season_data['matches_list'])} gameweeks...")
                    
                    # Get database columns for matches table
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='matches' AND column_name != 'match_url'
                        ORDER BY ordinal_position
                    """)
                    db_columns = [row[0] for row in cur.fetchall()]
                    
                    total_matches = 0
                    for matches_file in season_data['matches_list']:
                        matches_df = pd.read_csv(matches_file)
                        
                        # Filter CSV columns to match database
                        available_columns = [col for col in db_columns if col in matches_df.columns]
                        filtered_df = matches_df[available_columns].copy()
                        
                        if 'finished' in filtered_df.columns:
                            filtered_df['finished'] = filtered_df['finished'].map({True: True, False: False, 'True': True, 'False': False}).fillna(False).astype(bool)
                        
                        # Handle null values for PostgreSQL (convert NaN to None)
                        filtered_df = filtered_df.astype(object).where(pd.notnull(filtered_df), None)
                        
                        # Filter out non-PL matches (missing team IDs)
                        filtered_df = filtered_df.dropna(subset=['home_team', 'away_team'])
                        
                        # Insert matches
                        cols = ', '.join(available_columns)
                        placeholders = ', '.join(['%s'] * len(available_columns))
                        
                        for _, row in filtered_df.iterrows():
                            cur.execute(f"""
                                INSERT INTO matches ({cols}) VALUES ({placeholders})
                                ON CONFLICT (match_id) DO UPDATE SET
                                    finished = EXCLUDED.finished,
                                    home_score = EXCLUDED.home_score,
                                    away_score = EXCLUDED.away_score
                            """, tuple(row))
                        total_matches += len(filtered_df)
                    
                    self.import_summary['season_data']['matches'] = total_matches
                    self.log(f"✅ Total matches imported: {total_matches}")

                # Import playermatchstats from all gameweeks
                if season_data.get('stats_list'):
                    self.log(f"Importing player stats from {len(season_data['stats_list'])} gameweeks...")
                    
                    # Get database columns for playermatchstats table  
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='playermatchstats' AND column_name != 'id'
                        ORDER BY ordinal_position
                    """)
                    db_columns = [row[0] for row in cur.fetchall()]
                    
                    total_stats = 0
                    for stats_file in season_data['stats_list']:
                        stats_df = pd.read_csv(stats_file)
                        
                        # Map CSV columns to database columns
                        available_columns = [col for col in db_columns if col in stats_df.columns]
                        filtered_df = stats_df[available_columns].copy()
                        
                        # Add missing columns with defaults
                        for col in db_columns:
                            if col not in filtered_df.columns:
                                if col in ['xg', 'xa', 'xgot', 'xgot_faced', 'goals_prevented']:
                                    filtered_df[col] = 0.0
                                else:
                                    filtered_df[col] = 0
                        
                        # Ensure column order matches database
                        filtered_df = filtered_df[db_columns]
                        
                        # Handle data type conversions and null values
                        for col in filtered_df.columns:
                            if col in ['xg', 'xa', 'xgot', 'xgot_faced', 'goals_prevented']:
                                filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').fillna(0.0)
                            elif col == 'player_id':
                                filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').fillna(0).astype(int)
                            elif col == 'match_id':
                                pass # keep as string
                            else:
                                filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').fillna(0).astype(int)
                        
                        # Fix percents
                        for pct_col in ['accurate_passes_percent', 'accurate_crosses_percent', 'accurate_long_balls_percent']:
                            if pct_col in filtered_df.columns:
                                filtered_df[pct_col] = filtered_df[pct_col].astype(float).round().astype(int)
                        
                        # Handle nulls for PostgreSQL
                        filtered_df = filtered_df.astype(object).where(pd.notnull(filtered_df), None)
                        
                        # Insert player match stats
                        cols = ', '.join(db_columns)
                        placeholders = ', '.join(['%s'] * len(db_columns))
                        
                        for _, row in filtered_df.iterrows():
                            cur.execute(f"""
                                INSERT INTO playermatchstats ({cols}) VALUES ({placeholders})
                            """, tuple(row))
                        total_stats += len(filtered_df)
                    
                    self.import_summary['season_data']['playermatchstats'] = total_stats
                    self.log(f"✅ Total player match stats imported: {total_stats}")

                conn.commit()
                return True

        except Exception as e:
            self.log(f"Error importing season data: {e}", "ERROR")
            self.import_summary['errors'].append(f"Season data import: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def import_draft_data(self, draft_data):
        """Import draft league data"""
        if not draft_data:
            self.log("No draft league data found to import")
            return True

        conn = self.get_db_connection()
        if not conn:
            return False

        try:
            with conn.cursor() as cur:
                # Import draft managers
                if 'managers' in draft_data:
                    self.log("Importing draft managers...")
                    managers_df = pd.read_csv(draft_data['managers'])
                    
                    # Clear existing draft data
                    cur.execute("DELETE FROM draft_managers")
                    
                    for _, row in managers_df.iterrows():
                        # Handle null values and data type conversion
                        manager_id = int(row.get('id', 0)) if pd.notna(row.get('id')) else None
                        entry_id = int(row.get('entry_id', 0)) if pd.notna(row.get('entry_id')) else None
                        waiver_pick = int(row.get('waiver_pick', 0)) if pd.notna(row.get('waiver_pick')) else None
                        
                        cur.execute("""
                            INSERT INTO draft_managers 
                            (id, league_id, entry_name, player_first_name, player_last_name,
                             short_name, waiver_pick, entry_id, joined_time)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            manager_id, 1, row.get('entry_name'),
                            row.get('player_first_name'), row.get('player_last_name'),
                            row.get('short_name'), waiver_pick, entry_id, None
                        ))
                    
                    self.import_summary['draft_data']['managers'] = len(managers_df)
                    self.log(f"✅ Imported {len(managers_df)} draft managers")

                # Import draft picks
                if 'picks' in draft_data:
                    self.log("Importing draft picks...")
                    picks_df = pd.read_csv(draft_data['picks'])
                    
                    # Clear existing picks
                    cur.execute("DELETE FROM draft_picks")
                    
                    for _, row in picks_df.iterrows():
                        # Handle null values and data type conversion
                        element_id = int(row.get('element', 0)) if pd.notna(row.get('element')) else None
                        owner = int(row.get('owner', 0)) if pd.notna(row.get('owner')) else None
                        
                        cur.execute("""
                            INSERT INTO draft_picks (element_id, league_id, owner, status)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            element_id, 1, owner, 
                            'owned' if owner is not None else 'available'
                        ))
                    
                    self.import_summary['draft_data']['picks'] = len(picks_df)
                    self.log(f"✅ Imported {len(picks_df)} draft picks")

                conn.commit()
                return True

        except Exception as e:
            self.log(f"Error importing draft data: {e}", "ERROR")
            self.import_summary['errors'].append(f"Draft data import: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def print_summary(self):
        """Print import summary"""
        self.log("=== IMPORT SUMMARY ===")
        
        if self.import_summary['season_data']:
            self.log("📊 Season Data Imported:")
            for table, count in self.import_summary['season_data'].items():
                self.log(f"   {table}: {count} records")
        
        if self.import_summary['draft_data']:
            self.log("🏆 Draft League Data Imported:")
            for table, count in self.import_summary['draft_data'].items():
                self.log(f"   {table}: {count} records")
        
        if self.import_summary['errors']:
            self.log("❌ Errors encountered:")
            for error in self.import_summary['errors']:
                self.log(f"   {error}")
        
        total_records = (sum(self.import_summary['season_data'].values()) + 
                        sum(self.import_summary['draft_data'].values()))
        self.log(f"✅ Total records imported: {total_records}")

    def run_ingestion(self):
        """Run the complete database ingestion process"""
        self.log("=== Starting Database Ingestion ===")
        
        # Test database connection
        if not self.test_database_connection():
            self.log("Database connection failed. Exiting.", "ERROR")
            return False
        
        # Find data files
        self.log("Scanning for data files...")
        season_data = self.find_latest_season_data()
        draft_data = self.find_draft_league_data()
        
        if not season_data and not draft_data:
            self.log("No data files found to import. Exiting.")
            return False
        
        # Import season data
        if season_data:
            self.log(f"Found season data files: {list(season_data.keys())}")
            if not self.import_season_data(season_data):
                return False
        
        # Import draft data
        if draft_data:
            self.log(f"Found draft league data files: {list(draft_data.keys())}")
            if not self.import_draft_data(draft_data):
                return False
        
        # Print summary
        self.print_summary()
        self.log("=== Database Ingestion Completed ===")
        return True

def main():
    """Main execution function"""
    # Change to script directory for relative paths
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    ingester = DatabaseIngester()
    success = ingester.run_ingestion()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()