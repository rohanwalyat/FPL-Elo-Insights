#!/usr/bin/env python3
"""
FPL Draft League - Show Player Picks by Manager
Displays which players are owned by each manager in the draft league
"""

import pandas as pd
import os
from pathlib import Path

def load_draft_data():
    """Load the latest draft league data"""
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    data_dir = base_dir / "data" / "draft_league" / "latest"
    
    try:
        # Load all data files
        managers_df = pd.read_csv(data_dir / "managers.csv")
        picks_df = pd.read_csv(data_dir / "picks.csv")
        players_df = pd.read_csv(data_dir / "players.csv")
        
        return managers_df, picks_df, players_df
    except FileNotFoundError as e:
        print(f"❌ Error loading data: {e}")
        print("Make sure to run 'python3 scripts/simple_draft_fetch.py' first!")
        return None, None, None

def get_player_info(player_id, players_df):
    """Get player information from player ID"""
    player = players_df[players_df['id'] == player_id]
    if player.empty:
        return f"Unknown Player (ID: {player_id})"
    
    player = player.iloc[0]
    position_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
    position = position_map.get(player['element_type'], "UNK")
    
    return {
        'name': player['web_name'],
        'full_name': f"{player['first_name']} {player['second_name']}",
        'position': position,
        'team': player['team'],
        'total_points': player.get('total_points', 0),
        'price': player.get('draft_rank', 0)
    }

def get_team_name(team_id, teams_data=None):
    """Get team name from team ID (simplified for now)"""
    # Common team mapping - could be enhanced with teams.csv
    team_map = {
        1: "ARS", 2: "AVL", 3: "BOU", 4: "BRE", 5: "BRI",
        6: "CHE", 7: "CRY", 8: "EVE", 9: "FUL", 10: "IPS",
        11: "LEI", 12: "LIV", 13: "MCI", 14: "MUN", 15: "NEW",
        16: "NFO", 17: "SOU", 18: "TOT", 19: "WHU", 20: "WOL"
    }
    return team_map.get(team_id, f"Team {team_id}")

def display_manager_squads(managers_df, picks_df, players_df):
    """Display each manager's squad"""
    print("\n" + "="*80)
    print("🏆 FPL DRAFT LEAGUE - PLAYER PICKS BY MANAGER")
    print("="*80)
    
    # Get only picked players (those with an owner)
    picked_players = picks_df[picks_df['owner'].notna()].copy()
    # Convert owner to int for proper matching
    picked_players['owner'] = picked_players['owner'].astype(int)
    
    for _, manager in managers_df.iterrows():
        manager_id = manager['id']
        team_name = manager['entry_name']
        manager_name = f"{manager['player_first_name']} {manager['player_last_name']}"
        
        print(f"\n🔥 {team_name}")
        print(f"👤 Manager: {manager_name}")
        print("-" * 60)
        
        # Get this manager's picks (picks use entry_id, not id)
        if pd.isna(manager['entry_id']) or manager['entry_id'] == '':
            manager_picks = pd.DataFrame()  # Empty dataframe for managers without entry_id
        else:
            manager_entry_id = int(manager['entry_id'])
            manager_picks = picked_players[picked_players['owner'] == manager_entry_id]
        
        if manager_picks.empty:
            print("   No players picked yet")
            continue
        
        # Group players by position
        squad_by_position = {"GKP": [], "DEF": [], "MID": [], "FWD": []}
        
        for _, pick in manager_picks.iterrows():
            player_info = get_player_info(pick['element'], players_df)
            if isinstance(player_info, dict):
                squad_by_position[player_info['position']].append(player_info)
        
        # Display squad by position
        for position in ["GKP", "DEF", "MID", "FWD"]:
            if squad_by_position[position]:
                print(f"\n   {position}:")
                for player in sorted(squad_by_position[position], key=lambda x: x['name']):
                    team_name = get_team_name(player['team'])
                    points = player['total_points']
                    print(f"      • {player['name']} ({team_name}) - {points} pts")
        
        total_players = sum(len(squad_by_position[pos]) for pos in squad_by_position)
        print(f"\n   📊 Total Players: {total_players}")

def display_summary_stats(managers_df, picks_df, players_df):
    """Display summary statistics"""
    print("\n" + "="*80)
    print("📈 LEAGUE SUMMARY")
    print("="*80)
    
    picked_players = picks_df[picks_df['owner'].notna()].copy()
    total_picked = len(picked_players)
    total_available = len(picks_df) - total_picked
    
    print(f"👥 Total Managers: {len(managers_df)}")
    print(f"⚽ Players Picked: {total_picked}")
    print(f"🆓 Players Available: {total_available}")
    print(f"📦 Total Player Pool: {len(picks_df)}")
    
    # Players per manager
    print(f"\n🔢 Players per Manager:")
    for _, manager in managers_df.iterrows():
        if pd.isna(manager['entry_id']) or manager['entry_id'] == '':
            manager_picks = pd.DataFrame()
        else:
            manager_entry_id = int(manager['entry_id'])
            manager_picks = picked_players[picked_players['owner'] == manager_entry_id]
        team_name = manager['entry_name']
        print(f"   {team_name}: {len(manager_picks)} players")

def display_top_available_players(picks_df, players_df, limit=10):
    """Display top available players"""
    print(f"\n" + "="*80)
    print(f"🆓 TOP {limit} AVAILABLE PLAYERS")
    print("="*80)
    
    # Get unpicked players
    available_players = picks_df[picks_df['owner'].isna()].copy()
    
    if available_players.empty:
        print("   No players available (all drafted)")
        return
    
    # Get player details and sort by draft rank (lower is better)
    available_with_details = []
    for _, pick in available_players.iterrows():
        player_info = get_player_info(pick['element'], players_df)
        if isinstance(player_info, dict):
            available_with_details.append(player_info)
    
    # Sort by draft rank (lower rank = higher pick)
    top_available = sorted(available_with_details, key=lambda x: x['price'])[:limit]
    
    print(f"{'Player':<20} {'Team':<5} {'Pos':<4} {'Points':<7} {'Rank'}")
    print("-" * 50)
    
    for player in top_available:
        team_name = get_team_name(player['team'])
        print(f"{player['name']:<20} {team_name:<5} {player['position']:<4} {player['total_points']:<7} {player['price']}")

def main():
    """Main function"""
    print("Loading FPL Draft League data...")
    
    managers_df, picks_df, players_df = load_draft_data()
    if managers_df is None:
        return
    
    print(f"✅ Loaded data: {len(managers_df)} managers, {len(picks_df)} picks, {len(players_df)} players")
    
    # Display manager squads
    display_manager_squads(managers_df, picks_df, players_df)
    
    # Display summary stats
    display_summary_stats(managers_df, picks_df, players_df)
    
    # Display top available players
    display_top_available_players(picks_df, players_df)
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()