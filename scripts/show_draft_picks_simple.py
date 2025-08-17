#!/usr/bin/env python3
"""
FPL Draft League - Show Player Picks by Manager (No pandas dependency)
Displays which players are owned by each manager in the draft league
"""

import csv
import json
import os
from pathlib import Path

def load_csv_data(file_path):
    """Load CSV data into list of dictionaries"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return []

def load_draft_data():
    """Load the latest draft league data"""
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    data_dir = base_dir / "data" / "draft_league" / "latest"
    
    print(f"Loading data from: {data_dir}")
    
    managers = load_csv_data(data_dir / "managers.csv")
    picks = load_csv_data(data_dir / "picks.csv")
    players = load_csv_data(data_dir / "players.csv")
    
    if not managers or not picks or not players:
        print("❌ Error loading data files!")
        print("Make sure to run 'python3 scripts/simple_draft_fetch.py' first!")
        return None, None, None
    
    return managers, picks, players

def get_player_info(player_id, players):
    """Get player information from player ID"""
    for player in players:
        if player['id'] == str(player_id):
            position_map = {"1": "GKP", "2": "DEF", "3": "MID", "4": "FWD"}
            position = position_map.get(player['element_type'], "UNK")
            
            return {
                'name': player['web_name'],
                'full_name': f"{player['first_name']} {player['second_name']}",
                'position': position,
                'team_id': player['team'],
                'total_points': int(player.get('total_points', 0)),
                'draft_rank': int(player.get('draft_rank', 999))
            }
    return None

def get_team_name(team_id):
    """Get team name from team ID"""
    team_map = {
        "1": "ARS", "2": "AVL", "3": "BOU", "4": "BRE", "5": "BRI",
        "6": "CHE", "7": "CRY", "8": "EVE", "9": "FUL", "10": "IPS",
        "11": "LEI", "12": "LIV", "13": "MCI", "14": "MUN", "15": "NEW",
        "16": "NFO", "17": "SOU", "18": "TOT", "19": "WHU", "20": "WOL"
    }
    return team_map.get(str(team_id), f"T{team_id}")

def display_manager_squads(managers, picks, players):
    """Display each manager's squad"""
    print("\n" + "="*80)
    print("🏆 FPL DRAFT LEAGUE - PLAYER PICKS BY MANAGER")
    print("="*80)
    
    # Filter picks to only those with owners
    picked_players = [p for p in picks if p['owner'] and p['owner'].strip()]
    
    for manager in managers:
        manager_id = manager['id']
        team_name = manager['entry_name']
        manager_name = f"{manager['player_first_name']} {manager['player_last_name']}"
        
        print(f"\n🔥 {team_name}")
        print(f"👤 Manager: {manager_name}")
        print("-" * 60)
        
        # Get this manager's picks (picks use entry_id, not id)
        manager_entry_id = manager['entry_id']
        manager_picks = [p for p in picked_players if p['owner'] == str(manager_entry_id)]
        
        if not manager_picks:
            print("   No players picked yet")
            continue
        
        # Group players by position
        squad_by_position = {"GKP": [], "DEF": [], "MID": [], "FWD": []}
        
        for pick in manager_picks:
            player_info = get_player_info(pick['element'], players)
            if player_info:
                squad_by_position[player_info['position']].append(player_info)
        
        # Display squad by position
        total_points = 0
        total_players = 0
        
        for position in ["GKP", "DEF", "MID", "FWD"]:
            if squad_by_position[position]:
                print(f"\n   {position}:")
                position_players = sorted(squad_by_position[position], key=lambda x: x['name'])
                for player in position_players:
                    team_name = get_team_name(player['team_id'])
                    points = player['total_points']
                    total_points += points
                    print(f"      • {player['name']} ({team_name}) - {points} pts")
                total_players += len(position_players)
        
        print(f"\n   📊 Total: {total_players} players, {total_points} points")

def display_summary_stats(managers, picks, players):
    """Display summary statistics"""
    print("\n" + "="*80)
    print("📈 LEAGUE SUMMARY")
    print("="*80)
    
    picked_players = [p for p in picks if p['owner'] and p['owner'].strip()]
    total_picked = len(picked_players)
    total_available = len(picks) - total_picked
    
    print(f"👥 Total Managers: {len(managers)}")
    print(f"⚽ Players Picked: {total_picked}")
    print(f"🆓 Players Available: {total_available}")
    print(f"📦 Total Player Pool: {len(picks)}")
    
    # Players per manager
    print(f"\n🔢 Players per Manager:")
    for manager in managers:
        manager_entry_id = manager['entry_id']
        team_name = manager['entry_name']
        manager_picks = [p for p in picked_players if p['owner'] == str(manager_entry_id)]
        print(f"   {team_name}: {len(manager_picks)} players")

def display_top_available_players(picks, players, limit=10):
    """Display top available players"""
    print(f"\n" + "="*80)
    print(f"🆓 TOP {limit} AVAILABLE PLAYERS")
    print("="*80)
    
    # Get unpicked players
    available_picks = [p for p in picks if not p['owner'] or not p['owner'].strip()]
    
    if not available_picks:
        print("   No players available (all drafted)")
        return
    
    # Get player details and sort by draft rank (lower is better)
    available_with_details = []
    for pick in available_picks:
        player_info = get_player_info(pick['element'], players)
        if player_info:
            available_with_details.append(player_info)
    
    # Sort by draft rank (lower rank = higher pick)
    top_available = sorted(available_with_details, key=lambda x: x['draft_rank'])[:limit]
    
    print(f"{'Player':<20} {'Team':<5} {'Pos':<4} {'Points':<7} {'Rank'}")
    print("-" * 50)
    
    for player in top_available:
        team_name = get_team_name(player['team_id'])
        print(f"{player['name']:<20} {team_name:<5} {player['position']:<4} {player['total_points']:<7} {player['draft_rank']}")

def display_waiver_order(managers):
    """Display waiver order"""
    print(f"\n" + "="*80)
    print("📋 WAIVER ORDER")
    print("="*80)
    
    # Sort managers by waiver pick (handle empty values)
    def get_waiver_pick(manager):
        pick = manager.get('waiver_pick', '')
        return int(pick) if pick and pick.strip() else 999
    
    sorted_managers = sorted(managers, key=get_waiver_pick)
    
    print(f"{'Pick':<5} {'Team':<25} {'Manager'}")
    print("-" * 50)
    
    for manager in sorted_managers:
        pick = manager.get('waiver_pick', 'N/A')
        team_name = manager['entry_name']
        manager_name = f"{manager['player_first_name']} {manager['player_last_name']}"
        print(f"{pick:<5} {team_name:<25} {manager_name}")

def main():
    """Main function"""
    print("Loading FPL Draft League data...")
    
    managers, picks, players = load_draft_data()
    if not managers:
        return
    
    print(f"✅ Loaded: {len(managers)} managers, {len(picks)} picks, {len(players)} players")
    
    # Display manager squads
    display_manager_squads(managers, picks, players)
    
    # Display summary stats
    display_summary_stats(managers, picks, players)
    
    # Display waiver order
    display_waiver_order(managers)
    
    # Display top available players
    display_top_available_players(picks, players)
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()