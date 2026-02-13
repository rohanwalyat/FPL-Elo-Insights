#!/usr/bin/env python3
"""
Compatibility Wrapper for Medallion Architecture

This module provides backward-compatible functions that existing analysis scripts
can use without modification while leveraging the medallion architecture under the hood.

Usage:
    Instead of direct database/API calls, existing scripts can import this module
    to get the same data from the optimized medallion layers.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import json
import warnings
from medallion_data_adapter import MedallionDataAdapter

# Global adapter instance
_adapter = None

def get_adapter():
    """Get or create the medallion data adapter instance"""
    global _adapter
    if _adapter is None:
        _adapter = MedallionDataAdapter()
    return _adapter

# === Expected Points Calculator Compatible Functions ===

def get_player_expected_points_data() -> pd.DataFrame:
    """
    Get player expected points data - compatible with ExpectedPointsCalculator
    
    Returns:
        DataFrame with columns: player_id, web_name, full_name, position, 
        expected_points, fpl_total_points, fpl_points_per_game, etc.
    """
    adapter = get_adapter()
    
    # Check if medallion data is available
    if not adapter.is_medallion_data_available():
        warnings.warn("Medallion data not available. Run: python data_pipeline/medallion_orchestrator.py --layer all")
        return pd.DataFrame()
    
    return adapter.get_player_expected_points()

def get_fixture_difficulty_multipliers() -> Dict[str, float]:
    """
    Get fixture difficulty multipliers for teams - compatible with FixtureDifficultyAnalyzer
    
    Returns:
        Dictionary mapping team names to difficulty ratings
    """
    adapter = get_adapter()
    fixture_df = adapter.get_fixture_difficulty()
    
    if fixture_df.empty:
        return {}
    
    # Convert to dictionary format expected by existing scripts
    multipliers = {}
    for _, row in fixture_df.iterrows():
        multipliers[row['team_name']] = row['overall_difficulty_rating']
    
    return multipliers

# === Draft League Compatible Functions ===

def get_fpl_api_data() -> Dict:
    """
    Get FPL API data - compatible with draft league analyzers
    
    Returns:
        Dictionary with 'elements', 'teams', and 'element_types' keys
    """
    adapter = get_adapter()
    
    players_df = adapter.get_fpl_players_data()
    teams_df = adapter.get_fpl_teams_data()
    
    if players_df.empty or teams_df.empty:
        return {}
    
    # Convert to FPL API format
    elements = players_df.to_dict('records')
    teams = teams_df.to_dict('records')
    
    # Add element_types (positions)
    element_types = [
        {'id': 1, 'plural_name': 'Goalkeepers', 'singular_name': 'Goalkeeper'},
        {'id': 2, 'plural_name': 'Defenders', 'singular_name': 'Defender'},
        {'id': 3, 'plural_name': 'Midfielders', 'singular_name': 'Midfielder'},
        {'id': 4, 'plural_name': 'Forwards', 'singular_name': 'Forward'}
    ]
    
    return {
        'elements': elements,
        'teams': teams,
        'element_types': element_types
    }

def get_owned_players_from_draft(league_id: str) -> List[int]:
    """
    Get owned player IDs from draft league - compatible with draft analyzers
    
    Args:
        league_id: Draft league ID
        
    Returns:
        List of owned player IDs
    """
    adapter = get_adapter()
    available_players = adapter.get_available_players(league_id)
    
    # Get all players
    players_df = adapter.get_fpl_players_data()
    if players_df.empty:
        return []
    
    all_player_ids = set(players_df['id'].tolist())
    available_set = set(available_players)
    
    # Return owned players (all - available)
    return list(all_player_ids - available_set)

# === Team Analytics Compatible Functions ===

def get_team_strength_data() -> pd.DataFrame:
    """
    Get team strength data - compatible with fixture difficulty analyzers
    
    Returns:
        DataFrame with team strength metrics
    """
    adapter = get_adapter()
    return adapter.get_team_analytics()

# === Database Compatible Functions ===

def get_players_from_database() -> pd.DataFrame:
    """
    Get player data that would normally come from database queries
    
    Returns:
        DataFrame with player information
    """
    adapter = get_adapter()
    return adapter.get_fpl_players_data()

def get_player_match_stats_from_database(player_id: Optional[int] = None) -> pd.DataFrame:
    """
    Get player match statistics that would normally come from database queries
    
    Args:
        player_id: Optional player ID filter
        
    Returns:
        DataFrame with player match statistics
    """
    adapter = get_adapter()
    return adapter.get_player_match_stats(player_id)

def get_matches_from_database() -> pd.DataFrame:
    """
    Get match data that would normally come from database queries
    
    Returns:
        DataFrame with match information
    """
    adapter = get_adapter()
    return adapter.get_matches_data()

# === Backward Compatibility Check ===

def check_medallion_compatibility() -> Dict[str, bool]:
    """
    Check if medallion architecture is ready to support existing scripts
    
    Returns:
        Dictionary with compatibility status for different script types
    """
    adapter = get_adapter()
    
    # Test core functions
    compatibility = {
        'medallion_data_available': adapter.is_medallion_data_available(),
        'player_expected_points': False,
        'team_analytics': False,
        'fixture_difficulty': False,
        'fpl_api_data': False
    }
    
    try:
        # Test player expected points
        players = adapter.get_player_expected_points()
        compatibility['player_expected_points'] = not players.empty and 'expected_points' in players.columns
        
        # Test team analytics
        teams = adapter.get_team_analytics()
        compatibility['team_analytics'] = not teams.empty
        
        # Test fixture difficulty
        fixtures = adapter.get_fixture_difficulty()
        compatibility['fixture_difficulty'] = not fixtures.empty
        
        # Test FPL API data format
        fpl_data = get_fpl_api_data()
        compatibility['fpl_api_data'] = bool(fpl_data.get('elements')) and bool(fpl_data.get('teams'))
        
    except Exception as e:
        warnings.warn(f"Compatibility check failed: {e}")
    
    return compatibility

# === Usage Examples ===

if __name__ == "__main__":
    print("🔧 Medallion Compatibility Wrapper")
    print("=" * 50)
    
    # Run compatibility check
    compatibility = check_medallion_compatibility()
    
    print("📋 Compatibility Status:")
    for component, status in compatibility.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {component}")
    
    if all(compatibility.values()):
        print("\n✅ All existing analysis scripts should work with medallion architecture!")
        
        # Show sample data
        print(f"\n📊 Sample Data Available:")
        
        # Expected points data
        players = get_player_expected_points_data()
        print(f"  - Player Expected Points: {len(players)} records")
        
        # Team analytics
        teams = get_team_strength_data()
        print(f"  - Team Analytics: {len(teams)} records")
        
        # Fixture difficulty
        difficulty = get_fixture_difficulty_multipliers()
        print(f"  - Fixture Difficulty: {len(difficulty)} teams")
        
        # FPL API format data
        fpl_data = get_fpl_api_data()
        print(f"  - FPL API Format: {len(fpl_data.get('elements', []))} players, {len(fpl_data.get('teams', []))} teams")
        
    else:
        print(f"\n❌ Some components are not ready. Please run:")
        print(f"   python data_pipeline/medallion_orchestrator.py --layer all")
        
    print(f"\n🔍 Data Freshness:")
    adapter = get_adapter()
    freshness = adapter.get_data_freshness()
    for layer, timestamp in freshness.items():
        print(f"  {layer}: {timestamp}")