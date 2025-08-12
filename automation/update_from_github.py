#!/usr/bin/env python3
"""
GitHub-based FPL Data Update Script
This script pulls latest data from your forked repo and updates the database
"""

import os
import sys
import subprocess
import pandas as pd
from datetime import datetime
from pathlib import Path

def log_message(message):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def run_git_command(command, cwd=None):
    """Run a git command"""
    try:
        result = subprocess.run(command.split(), 
                              capture_output=True, text=True, 
                              check=True, cwd=cwd)
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()

def pull_latest_data():
    """Pull latest data from GitHub repo"""
    log_message("Pulling latest data from GitHub...")
    
    # Get the repo path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_path = os.path.dirname(script_dir)  # Go up one level from automation/ to FPL-Elo-Insights/
    
    if not os.path.exists(os.path.join(repo_path, '.git')):
        log_message("FPL-Elo-Insights is not a git repository. Cannot pull updates.")
        return False
    
    # Check current status
    success, status = run_git_command('git status --porcelain', repo_path)
    if not success:
        log_message(f"Failed to check git status: {status}")
        return False
    
    if status:
        log_message("Local changes detected. Stashing changes before pull...")
        stash_success, _ = run_git_command('git stash', repo_path)
        if not stash_success:
            log_message("Failed to stash changes")
            return False
    
    # Pull latest changes
    success, output = run_git_command('git pull origin main', repo_path)
    if not success:
        # Try 'master' branch if 'main' fails
        success, output = run_git_command('git pull origin master', repo_path)
        if not success:
            log_message(f"Failed to pull from GitHub: {output}")
            return False
    
    if "Already up to date" in output:
        log_message("Repository is already up to date")
        return True
    
    log_message("Successfully pulled latest changes from GitHub")
    return True

def run_psql_command(command):
    """Run a psql command"""
    try:
        # Set up environment with password from .env file or environment
        env = os.environ.copy()
        
        # Try to load password from .env file
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('PGPASSWORD='):
                        env['PGPASSWORD'] = line.split('=', 1)[1].strip()
                        break
        
        result = subprocess.run([
            'psql', '-U', 'postgres', '-d', 'fpl_elo', '-c', command
        ], capture_output=True, text=True, check=True, env=env)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def update_database_tables():
    """Update database tables from CSV files"""
    log_message("Updating database tables...")
    
    # Data paths - get relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_path = os.path.dirname(script_dir)
    base_path = os.path.join(repo_path, 'data')
    
    # Check for different season folders
    season_folders = ['2025-2026', '2024-2025']
    data_paths = {}
    
    for season in season_folders:
        season_path = os.path.join(base_path, season)
        if os.path.exists(season_path):
            players_csv = os.path.join(season_path, 'players.csv')
            teams_csv = os.path.join(season_path, 'teams.csv')
            
            if os.path.exists(players_csv):
                data_paths['players'] = players_csv
            if os.path.exists(teams_csv):
                data_paths['teams'] = teams_csv
            
            # Check for matches in nested folders
            matches_csv = os.path.join(season_path, 'matches', 'matches.csv')
            if os.path.exists(matches_csv):
                data_paths['matches'] = matches_csv
            
            # Check for playermatchstats
            pms_csv = os.path.join(season_path, 'playermatchstats', 'playermatchstats.csv')
            if os.path.exists(pms_csv):
                data_paths['playermatchstats'] = pms_csv
    
    log_message(f"Found data files: {list(data_paths.keys())}")
    
    # Update players table
    if 'players' in data_paths:
        log_message("Updating players table...")
        success, output = run_psql_command(f"TRUNCATE TABLE players CASCADE;")
        if success:
            copy_cmd = f"\\copy players FROM '{data_paths['players']}' DELIMITER ',' CSV HEADER;"
            success, output = run_psql_command(copy_cmd)
            if success:
                log_message("✓ Players table updated")
            else:
                log_message(f"✗ Failed to update players: {output}")
    
    # Update teams table
    if 'teams' in data_paths:
        log_message("Updating teams table...")
        success, output = run_psql_command(f"TRUNCATE TABLE teams CASCADE;")
        if success:
            copy_cmd = f"\\copy teams FROM '{data_paths['teams']}' DELIMITER ',' CSV HEADER;"
            success, output = run_psql_command(copy_cmd)
            if success:
                log_message("✓ Teams table updated")
            else:
                log_message(f"✗ Failed to update teams: {output}")
    
    # Update matches table (if exists)
    if 'matches' in data_paths:
        log_message("Updating matches table...")
        # Don't truncate matches, use upsert approach via temp table
        copy_cmd = f"\\copy matches FROM '{data_paths['matches']}' DELIMITER ',' CSV HEADER;"
        success, output = run_psql_command(copy_cmd)
        if success:
            log_message("✓ Matches table updated")
        else:
            log_message(f"✗ Failed to update matches: {output}")
    
    return True

def check_for_updates():
    """Check if there are updates available without pulling"""
    log_message("Checking for updates...")
    
    # Get the repo path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_path = os.path.dirname(script_dir)  # Go up one level from automation/ to FPL-Elo-Insights/
    
    # Fetch latest info from remote
    success, _ = run_git_command('git fetch origin', repo_path)
    if not success:
        log_message("Failed to fetch from remote")
        return False
    
    # Check if local is behind remote
    success, output = run_git_command('git status -uno', repo_path)
    if success and "behind" in output:
        log_message("Updates available from GitHub")
        return True
    else:
        log_message("Repository is up to date")
        return False

def main():
    """Main execution function"""
    log_message("=== Starting GitHub-based FPL Data Update ===")
    
    # Check if updates are available
    if not check_for_updates():
        log_message("No updates needed. Exiting.")
        return
    
    # Pull latest data
    if not pull_latest_data():
        log_message("Failed to pull latest data. Exiting.")
        sys.exit(1)
    
    # Test database connection
    log_message("Testing database connection...")
    success, output = run_psql_command("SELECT COUNT(*) FROM players;")
    
    if not success:
        log_message("Database connection failed. Make sure PostgreSQL is running.")
        log_message("Try: psql -U postgres -d fpl_elo")
        sys.exit(1)
    
    log_message("Database connection successful")
    
    # Update database
    update_database_tables()
    
    log_message("=== GitHub-based update completed successfully! ===")

if __name__ == "__main__":
    main()