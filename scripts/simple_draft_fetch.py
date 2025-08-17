#!/usr/bin/env python3
"""
Simple FPL Draft API fetcher - no pandas dependency
"""

import requests
import json
import csv
import os
from datetime import datetime

def fetch_league_data(league_id):
    """Fetch draft league data"""
    base_url = "https://draft.premierleague.com/api"
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    try:
        # Get league details
        print(f"Fetching league details for league {league_id}...")
        url = f"{base_url}/league/{league_id}/details"
        response = session.get(url)
        response.raise_for_status()
        league_data = response.json()
        
        # Get bootstrap data
        print("Fetching bootstrap data...")
        url = f"{base_url}/bootstrap-static"
        response = session.get(url)
        response.raise_for_status()
        bootstrap_data = response.json()
        
        # Try to get league picks (multiple endpoints)
        picks_data = None
        pick_endpoints = [
            f"/draft/league/{league_id}/element-status",
            f"/league/{league_id}/element-status", 
            f"/draft/{league_id}/picks",
            f"/league/{league_id}/picks"
        ]
        
        for endpoint in pick_endpoints:
            try:
                print(f"Trying picks endpoint: {endpoint}")
                url = f"{base_url}{endpoint}"
                response = session.get(url)
                response.raise_for_status()
                picks_data = response.json()
                print(f"✓ Success with endpoint: {endpoint}")
                break
            except requests.exceptions.RequestException:
                print(f"✗ Failed endpoint: {endpoint}")
                continue
        
        if not picks_data:
            print("⚠️ Could not fetch picks data, continuing with other data...")
        
        return league_data, bootstrap_data, picks_data
        
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return None, None, None

def save_csv_data(data, filename, fieldnames):
    """Save data to CSV file"""
    if not data:
        print(f"No data to save for {filename}")
        return
        
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    print(f"Saved {len(data)} rows to {filename}")

def update_latest_symlinks(archive_dir, timestamp):
    """Update symlinks in latest/ directory to point to newest files"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    latest_dir = os.path.join(base_dir, "data", "draft_league", "latest")
    os.makedirs(latest_dir, exist_ok=True)
    
    files_to_link = [
        ('league_info', 'json'),
        ('managers', 'csv'),
        ('picks', 'csv'),
        ('players', 'csv'),
        ('teams', 'csv'),
        ('standings', 'csv')
    ]
    
    for file_base, ext in files_to_link:
        archive_file = os.path.join(archive_dir, f"{file_base}_{timestamp}.{ext}")
        latest_file = os.path.join(latest_dir, f"{file_base}.{ext}")
        
        # Only create symlink if the archive file exists
        if os.path.exists(archive_file):
            # Remove existing symlink if it exists
            if os.path.islink(latest_file):
                os.unlink(latest_file)
            elif os.path.exists(latest_file):
                os.remove(latest_file)
            
            # Create new symlink with relative path
            relative_path = f"../archive/{datetime.now().strftime('%Y-%m-%d')}/{file_base}_{timestamp}.{ext}"
            os.symlink(relative_path, latest_file)
            print(f"Updated symlink: {file_base}.{ext} -> {relative_path}")
        else:
            print(f"Skipped {file_base}.{ext}: archive file not found")

def main():
    league_id = input("Enter your FPL Draft League ID: ").strip()
    if not league_id:
        print("League ID is required!")
        return
    
    league_data, bootstrap_data, picks_data = fetch_league_data(league_id)
    
    if not league_data:
        print("Failed to fetch data")
        return
    
    # Create organized output directories
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    # Get the correct path relative to where script is run from
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)  # Go up one level from scripts/
    archive_dir = os.path.join(base_dir, "data", "draft_league", "archive", date_str)
    os.makedirs(archive_dir, exist_ok=True)
    
    # Save league info as JSON
    league_info = {
        'league_id': league_data['league']['id'],
        'league_name': league_data['league']['name'],
        'draft_dt': league_data['league']['draft_dt'],
        'start_event': league_data['league']['start_event'],
        'stop_event': league_data['league']['stop_event'],
        'draft_status': league_data['league']['draft_status'],
        'total_managers': len(league_data['league_entries'])
    }
    
    with open(f"{archive_dir}/league_info_{timestamp}.json", 'w') as f:
        json.dump(league_info, f, indent=2)
    
    # Save managers
    managers = league_data['league_entries']
    if managers:
        manager_fields = ['entry_id', 'entry_name', 'id', 'joined_time', 'player_first_name', 'player_last_name', 'short_name', 'waiver_pick']
        save_csv_data(managers, f"{archive_dir}/managers_{timestamp}.csv", manager_fields)
    
    # Save picks
    if picks_data and 'element_status' in picks_data:
        picks = picks_data['element_status']
        if picks:
            pick_fields = list(picks[0].keys())  # Use dynamic fieldnames
            save_csv_data(picks, f"{archive_dir}/picks_{timestamp}.csv", pick_fields)
    
    # Save players from bootstrap
    if bootstrap_data and 'elements' in bootstrap_data:
        players = bootstrap_data['elements']
        # Get first player's keys as fieldnames
        if players:
            player_fields = list(players[0].keys())
            save_csv_data(players, f"{archive_dir}/players_{timestamp}.csv", player_fields)
    
    # Save teams from bootstrap
    if bootstrap_data and 'teams' in bootstrap_data:
        teams = bootstrap_data['teams']
        if teams:
            team_fields = list(teams[0].keys())
            save_csv_data(teams, f"{archive_dir}/teams_{timestamp}.csv", team_fields)
    
    # Save standings if available
    if 'standings' in league_data and league_data['standings']:
        standings = league_data['standings']
        if standings:
            standing_fields = list(standings[0].keys())  # Use dynamic fieldnames
            save_csv_data(standings, f"{archive_dir}/standings_{timestamp}.csv", standing_fields)
    
    # Update symlinks to latest files
    update_latest_symlinks(archive_dir, timestamp)
    
    latest_dir = os.path.join(base_dir, "data", "draft_league", "latest")
    print(f"\n✅ Successfully updated draft league data for: {league_info['league_name']}")
    print(f"📁 Archive saved: {archive_dir}")
    print(f"🔗 Latest symlinks updated in: {latest_dir}")
    print(f"⏰ Timestamp: {timestamp}")

if __name__ == "__main__":
    main()