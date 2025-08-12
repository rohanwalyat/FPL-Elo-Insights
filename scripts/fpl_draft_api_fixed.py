#!/usr/bin/env python3
"""
FPL Draft API Integration - Fixed Version
Fetches teams and players from your specific FPL Draft league
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

class FPLDraftAPI:
    def __init__(self):
        self.base_url = "https://draft.premierleague.com/api"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_bootstrap_data(self):
        """Get general bootstrap data (players, teams, positions, etc.)"""
        print("Fetching bootstrap data...")
        
        url = f"{self.base_url}/bootstrap-static"
        response = self.session.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def get_league_details(self, league_id):
        """Get specific league details and teams"""
        print(f"Fetching league details for league {league_id}...")
        
        url = f"{self.base_url}/league/{league_id}/details"
        response = self.session.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def get_league_transactions(self, league_id):
        """Get league transactions (drafts, trades, waivers)"""
        print(f"Fetching league transactions for league {league_id}...")
        
        try:
            url = f"{self.base_url}/draft/league/{league_id}/transactions"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Transactions endpoint not available: {e}")
            return None
    
    def get_league_picks(self, league_id):
        """Get current league picks/squads - try different endpoints"""
        print(f"Fetching league picks for league {league_id}...")
        
        # Try different possible endpoints
        endpoints = [
            f"/draft/league/{league_id}/element-status",
            f"/league/{league_id}/element-status", 
            f"/draft/{league_id}/picks",
            f"/league/{league_id}/picks"
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                print(f"Trying endpoint: {endpoint}")
                response = self.session.get(url)
                response.raise_for_status()
                print(f"✓ Success with endpoint: {endpoint}")
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"✗ Failed endpoint {endpoint}: {e}")
                continue
        
        print("No working picks endpoint found")
        return None

def process_bootstrap_data(bootstrap_data):
    """Process bootstrap data into useful DataFrames"""
    
    # Extract players
    players_df = pd.DataFrame(bootstrap_data['elements'])
    
    # Extract teams
    teams_df = pd.DataFrame(bootstrap_data['teams'])
    
    # Extract positions
    positions_df = pd.DataFrame(bootstrap_data['element_types'])
    
    # Extract gameweek info
    gameweeks_df = pd.DataFrame(bootstrap_data['events'])
    
    return {
        'players': players_df,
        'teams': teams_df,
        'positions': positions_df,
        'gameweeks': gameweeks_df
    }

def process_league_data(league_data):
    """Process league-specific data"""
    
    league_info = {
        'league_id': league_data['league']['id'],
        'league_name': league_data['league']['name'],
        'draft_dt': league_data['league']['draft_dt'],
        'start_event': league_data['league']['start_event'],
        'stop_event': league_data['league']['stop_event'],
        'draft_status': league_data['league']['draft_status'],
        'total_managers': len(league_data['league_entries'])
    }
    
    # Extract manager/team data
    managers_df = pd.DataFrame(league_data['league_entries'])
    
    # Extract matches if available
    matches_df = None
    if 'matches' in league_data and league_data['matches']:
        matches_df = pd.DataFrame(league_data['matches'])
    
    # Extract standings if available
    standings_df = None
    if 'standings' in league_data and league_data['standings']:
        standings_df = pd.DataFrame(league_data['standings'])
    
    return league_info, managers_df, matches_df, standings_df

def save_data_to_csv(data_dict, output_dir):
    """Save processed data to CSV files"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    saved_files = []
    for name, df in data_dict.items():
        if isinstance(df, pd.DataFrame) and not df.empty:
            filename = f"{name}_{timestamp}.csv"
            filepath = output_path / filename
            df.to_csv(filepath, index=False)
            saved_files.append(str(filepath))
            print(f"Saved {name}: {len(df)} rows -> {filepath}")
        elif df is None:
            print(f"Skipped {name}: No data available")
        else:
            print(f"Skipped {name}: Not a valid DataFrame")
    
    return saved_files

def main():
    """Main function to fetch and process FPL Draft data"""
    
    # You need to provide your league ID here
    LEAGUE_ID = input("Enter your FPL Draft League ID: ").strip()
    
    if not LEAGUE_ID:
        print("League ID is required!")
        return
    
    try:
        # Initialize API client
        api = FPLDraftAPI()
        
        # Get bootstrap data (all players, teams, etc.)
        print("\n=== Fetching Bootstrap Data ===")
        bootstrap_data = api.get_bootstrap_data()
        processed_data = process_bootstrap_data(bootstrap_data)
        
        # Get league-specific data
        print(f"\n=== Fetching League Data (ID: {LEAGUE_ID}) ===")
        league_data = api.get_league_details(LEAGUE_ID)
        league_info, managers_df, matches_df, standings_df = process_league_data(league_data)
        
        # Get current picks/squads
        print(f"\n=== Fetching Current Picks ===")
        picks_data = api.get_league_picks(LEAGUE_ID)
        
        # Process picks data if available
        picks_df = None
        if picks_data:
            if 'element_status' in picks_data:
                picks_df = pd.DataFrame(picks_data['element_status'])
            elif isinstance(picks_data, list):
                picks_df = pd.DataFrame(picks_data)
            else:
                print("Picks data structure not recognized")
        
        # Get transactions
        print(f"\n=== Fetching Transactions ===")
        transactions_data = api.get_league_transactions(LEAGUE_ID)
        transactions_df = None
        if transactions_data and 'transactions' in transactions_data:
            transactions_df = pd.DataFrame(transactions_data['transactions'])
        
        # Add processed data
        processed_data['managers'] = managers_df
        processed_data['picks'] = picks_df
        processed_data['matches'] = matches_df
        processed_data['standings'] = standings_df
        processed_data['transactions'] = transactions_df
        
        # Print league info
        print(f"\n=== League Information ===")
        print(f"League: {league_info['league_name']} (ID: {league_info['league_id']})")
        print(f"Managers: {league_info['total_managers']}")
        print(f"Start Event: {league_info['start_event']}")
        print(f"Stop Event: {league_info['stop_event']}")
        print(f"Draft Date: {league_info['draft_dt']}")
        print(f"Draft Status: {league_info['draft_status']}")
        
        # Show manager info
        print(f"\n=== Managers ===")
        for _, manager in managers_df.iterrows():
            print(f"  {manager['entry_name']} ({manager['player_first_name']} {manager['player_last_name']}) - Waiver: {manager['waiver_pick']}")
        
        # Save to CSV files
        print(f"\n=== Saving Data ===")
        output_dir = "../data/draft_league"
        saved_files = save_data_to_csv(processed_data, output_dir)
        
        print(f"\n✅ Successfully saved {len(saved_files)} files:")
        for file in saved_files:
            print(f"  - {file}")
            
        # Save league info as JSON
        info_file = Path(output_dir) / f"league_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(info_file, 'w') as f:
            json.dump(league_info, f, indent=2)
        print(f"  - {info_file}")
        
        print(f"\n🎯 Data successfully fetched for league: {league_info['league_name']}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
    except KeyError as e:
        print(f"❌ Data Processing Error: Missing key {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    main()