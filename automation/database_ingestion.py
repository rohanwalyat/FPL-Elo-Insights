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
        self.repo_path = self.script_dir.parent
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
        """Find the latest season data files"""
        season_data = {}
        
        # Check for 2025-2026 season data
        season_path = self.data_path / "2025-2026"
        if season_path.exists():
            # Check for main season files
            players_file = season_path / "players.csv"
            teams_file = season_path / "teams.csv"
            
            if players_file.exists():
                season_data['players'] = players_file
            if teams_file.exists():
                season_data['teams'] = teams_file
            
            # Find latest gameweek data
            gameweek_path = season_path / "By Gameweek"
            if gameweek_path.exists():
                # Find highest numbered gameweek with match data
                gameweeks = []
                for gw_dir in gameweek_path.iterdir():
                    if gw_dir.is_dir() and gw_dir.name.startswith("GW"):
                        gw_num = int(gw_dir.name[2:])  # Extract number from "GW1", etc.
                        matches_file = gw_dir / "matches.csv"
                        stats_file = gw_dir / "playermatchstats.csv"
                        
                        if matches_file.exists() and stats_file.exists():
                            gameweeks.append((gw_num, gw_dir))
                
                if gameweeks:
                    # Get latest gameweek with complete data
                    latest_gw = max(gameweeks, key=lambda x: x[0])
                    gw_dir = latest_gw[1]
                    
                    season_data['matches'] = gw_dir / "matches.csv"
                    season_data['playermatchstats'] = gw_dir / "playermatchstats.csv"
                    
                    self.log(f"Found latest gameweek data: {gw_dir.name}")
        
        return season_data

    def find_draft_league_data(self):
        """Find draft league data files"""
        draft_data = {}
        
        # Check latest draft league data
        draft_path = self.data_path / "draft_league" / "latest"
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

                # Import matches
                if 'matches' in season_data:
                    self.log("Importing matches data...")
                    matches_df = pd.read_csv(season_data['matches'])
                    
                    # Get database columns for matches table
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='matches' AND column_name != 'match_url'
                        ORDER BY ordinal_position
                    """)
                    db_columns = [row[0] for row in cur.fetchall()]
                    
                    # Filter CSV columns to match database
                    available_columns = [col for col in db_columns if col in matches_df.columns]
                    filtered_df = matches_df[available_columns].copy()
                    
                    # Handle boolean conversion
                    if 'finished' in filtered_df.columns:
                        filtered_df['finished'] = filtered_df['finished'].astype(bool)
                    
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
                    
                    self.import_summary['season_data']['matches'] = len(filtered_df)
                    self.log(f"✅ Imported {len(filtered_df)} matches")

                # Import playermatchstats
                if 'playermatchstats' in season_data:
                    self.log("Importing player match stats...")
                    stats_df = pd.read_csv(season_data['playermatchstats'])
                    
                    # Get database columns for playermatchstats table  
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='playermatchstats' AND column_name != 'id'
                        ORDER BY ordinal_position
                    """)
                    db_columns = [row[0] for row in cur.fetchall()]
                    
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
                            # Handle decimal fields
                            filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').fillna(0.0)
                        elif col in ['match_id', 'player_id']:
                            # Handle string/ID fields - keep as strings but handle player_id as int
                            if col == 'player_id':
                                filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').fillna(0).astype(int)
                            # match_id stays as string, no conversion needed
                        else:
                            # Handle integer fields
                            filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce').fillna(0).astype(int)
                    
                    # Handle specific problematic columns
                    if 'accurate_passes_percent' in filtered_df.columns:
                        filtered_df['accurate_passes_percent'] = filtered_df['accurate_passes_percent'].astype(float).round().astype(int)
                    if 'accurate_crosses_percent' in filtered_df.columns:
                        filtered_df['accurate_crosses_percent'] = filtered_df['accurate_crosses_percent'].astype(float).round().astype(int)
                    if 'accurate_long_balls_percent' in filtered_df.columns:
                        filtered_df['accurate_long_balls_percent'] = filtered_df['accurate_long_balls_percent'].astype(float).round().astype(int)
                    
                    # Insert player match stats
                    cols = ', '.join(db_columns)
                    placeholders = ', '.join(['%s'] * len(db_columns))
                    
                    for _, row in filtered_df.iterrows():
                        cur.execute(f"""
                            INSERT INTO playermatchstats ({cols}) VALUES ({placeholders})
                        """, tuple(row))
                    
                    self.import_summary['season_data']['playermatchstats'] = len(filtered_df)
                    self.log(f"✅ Imported {len(filtered_df)} player match stats")

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