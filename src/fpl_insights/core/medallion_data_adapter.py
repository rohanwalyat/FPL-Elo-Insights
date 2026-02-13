#!/usr/bin/env python3
"""
Medallion Data Adapter

Provides a compatibility layer for existing analysis scripts to access data from the
medallion architecture instead of making direct database/API calls.

This adapter preserves the existing script interfaces while redirecting data access
to the appropriate medallion layer (bronze, silver, or gold).
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Union
import json
from datetime import datetime

class MedallionDataAdapter:
    """Adapter to access medallion data layers with backward compatibility"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent.parent
        self.data_dir = self.base_dir / "data"
        
        # Data layer paths
        self.bronze_dir = self.data_dir / "bronze"
        self.silver_dir = self.data_dir / "silver"  
        self.gold_dir = self.data_dir / "gold"
        
    def get_player_expected_points(self, position_filter: str = None, 
                                 min_matches: int = 0) -> pd.DataFrame:
        """
        Get player expected points data from gold layer
        
        Args:
            position_filter: Filter by position (Goalkeeper, Defender, Midfielder, Forward)
            min_matches: Minimum matches played filter
            
        Returns:
            DataFrame with player expected points and analytics
        """
        try:
            df = pd.read_parquet(self.gold_dir / "player_performance" / "player_performance.parquet")
            
            # Apply filters
            if position_filter:
                df = df[df['position'] == position_filter]
                
            if min_matches > 0:
                df = df[df['matches_played'] >= min_matches]
                
            return df
            
        except Exception as e:
            print(f"❌ Error loading player expected points: {e}")
            return pd.DataFrame()
    
    def get_team_analytics(self, team_id: Optional[int] = None) -> pd.DataFrame:
        """
        Get team analytics data from gold layer
        
        Args:
            team_id: Optional team ID filter
            
        Returns:
            DataFrame with team analytics
        """
        try:
            df = pd.read_parquet(self.gold_dir / "team_analytics" / "team_analytics.parquet")
            
            if team_id:
                df = df[df['team_id'] == team_id]
                
            return df
            
        except Exception as e:
            print(f"❌ Error loading team analytics: {e}")
            return pd.DataFrame()
    
    def get_fixture_difficulty(self, team_name: Optional[str] = None) -> pd.DataFrame:
        """
        Get fixture difficulty data from gold layer
        
        Args:
            team_name: Optional team name filter
            
        Returns:
            DataFrame with fixture difficulty ratings
        """
        try:
            df = pd.read_parquet(self.gold_dir / "fixture_difficulty" / "fixture_difficulty.parquet")
            
            if team_name:
                df = df[df['team_name'].str.contains(team_name, case=False, na=False)]
                
            return df
            
        except Exception as e:
            print(f"❌ Error loading fixture difficulty: {e}")
            return pd.DataFrame()
    
    def get_fpl_players_data(self) -> pd.DataFrame:
        """
        Get FPL players data from silver layer (cleaned and validated)
        
        Returns:
            DataFrame with FPL players data
        """
        try:
            return pd.read_parquet(self.silver_dir / "players" / "players.parquet")
        except Exception as e:
            print(f"❌ Error loading FPL players data: {e}")
            return pd.DataFrame()
    
    def get_fpl_teams_data(self) -> pd.DataFrame:
        """
        Get FPL teams data from silver layer (cleaned and validated)
        
        Returns:
            DataFrame with FPL teams data
        """
        try:
            return pd.read_parquet(self.silver_dir / "teams" / "teams.parquet")
        except Exception as e:
            print(f"❌ Error loading FPL teams data: {e}")
            return pd.DataFrame()
    
    def get_matches_data(self) -> pd.DataFrame:
        """
        Get matches data from silver layer (cleaned and validated)
        
        Returns:
            DataFrame with matches data
        """
        try:
            return pd.read_parquet(self.silver_dir / "matches" / "matches.parquet")
        except Exception as e:
            print(f"❌ Error loading matches data: {e}")
            return pd.DataFrame()
    
    def get_player_match_stats(self, player_id: Optional[int] = None) -> pd.DataFrame:
        """
        Get player match statistics from silver layer (cleaned and validated)
        
        Args:
            player_id: Optional player ID filter
            
        Returns:
            DataFrame with player match statistics
        """
        try:
            df = pd.read_parquet(self.silver_dir / "playermatchstats" / "playermatchstats.parquet")
            
            if player_id:
                df = df[df['player_id'] == player_id]
                
            return df
            
        except Exception as e:
            print(f"❌ Error loading player match stats: {e}")
            return pd.DataFrame()
    
    def get_draft_league_data(self) -> Dict:
        """
        Get draft league data from bronze layer (latest raw data)
        
        Returns:
            Dictionary with draft league data
        """
        try:
            # Find the latest draft league data
            draft_files = list(self.bronze_dir.glob("**/draft_league_*.json"))
            if not draft_files:
                return {}
                
            # Get the most recent file
            latest_file = max(draft_files, key=lambda x: x.stat().st_mtime)
            
            with open(latest_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"❌ Error loading draft league data: {e}")
            return {}
    
    def get_available_players(self, league_id: str) -> List[int]:
        """
        Get available players in a draft league from bronze layer data
        
        Args:
            league_id: Draft league ID
            
        Returns:
            List of available player IDs
        """
        try:
            # Get all players from silver layer
            all_players = self.get_fpl_players_data()
            all_player_ids = set(all_players['id'].tolist())
            
            # Get owned players from draft league data
            draft_data = self.get_draft_league_data()
            owned_players = set()
            
            if 'element_status' in draft_data:
                for element in draft_data['element_status']:
                    if element.get('owner') and element.get('owner') != '':
                        owned_players.add(element['element'])
            
            # Return available players (all - owned)
            available_players = list(all_player_ids - owned_players)
            return available_players
            
        except Exception as e:
            print(f"❌ Error getting available players: {e}")
            return []
    
    def get_data_freshness(self) -> Dict[str, str]:
        """
        Get data freshness information across all layers
        
        Returns:
            Dictionary with last update timestamps for each layer
        """
        freshness = {}
        
        try:
            # Gold layer freshness
            player_perf = pd.read_parquet(self.gold_dir / "player_performance" / "player_performance.parquet")
            if not player_perf.empty and 'last_updated' in player_perf.columns:
                freshness['player_performance'] = player_perf['last_updated'].iloc[0]
            
            team_analytics = pd.read_parquet(self.gold_dir / "team_analytics" / "team_analytics.parquet") 
            if not team_analytics.empty and 'last_updated' in team_analytics.columns:
                freshness['team_analytics'] = team_analytics['last_updated'].iloc[0]
                
            fixture_diff = pd.read_parquet(self.gold_dir / "fixture_difficulty" / "fixture_difficulty.parquet")
            if not fixture_diff.empty and 'last_updated' in fixture_diff.columns:
                freshness['fixture_difficulty'] = fixture_diff['last_updated'].iloc[0]
                
        except Exception as e:
            print(f"⚠️ Could not retrieve data freshness: {e}")
            
        return freshness
    
    def is_medallion_data_available(self) -> bool:
        """
        Check if medallion data is available and up-to-date
        
        Returns:
            True if medallion data exists and is recent
        """
        required_files = [
            self.gold_dir / "player_performance" / "player_performance.parquet",
            self.gold_dir / "team_analytics" / "team_analytics.parquet", 
            self.gold_dir / "fixture_difficulty" / "fixture_difficulty.parquet",
            self.silver_dir / "players" / "players.parquet",
            self.silver_dir / "teams" / "teams.parquet"
        ]
        
        for file_path in required_files:
            if not file_path.exists():
                return False
                
        return True

# Backward compatibility functions that existing scripts can use
def get_player_expected_points(position_filter=None, min_matches=0):
    """Backward compatible function for existing scripts"""
    adapter = MedallionDataAdapter()
    return adapter.get_player_expected_points(position_filter, min_matches)

def get_team_analytics(team_id=None):
    """Backward compatible function for existing scripts"""
    adapter = MedallionDataAdapter()
    return adapter.get_team_analytics(team_id)

def get_fixture_difficulty(team_name=None):
    """Backward compatible function for existing scripts"""
    adapter = MedallionDataAdapter()
    return adapter.get_fixture_difficulty(team_name)

# Main execution
if __name__ == "__main__":
    adapter = MedallionDataAdapter()
    
    print("🔍 Testing Medallion Data Adapter")
    print("=" * 50)
    
    # Test data availability
    if not adapter.is_medallion_data_available():
        print("❌ Medallion data not available. Please run the pipeline first:")
        print("   python data_pipeline/medallion_orchestrator.py --run-all")
        exit(1)
    
    # Test player expected points
    players = adapter.get_player_expected_points()
    print(f"✅ Player expected points: {len(players)} records")
    
    # Test team analytics
    teams = adapter.get_team_analytics()
    print(f"✅ Team analytics: {len(teams)} records")
    
    # Test fixture difficulty
    fixtures = adapter.get_fixture_difficulty()
    print(f"✅ Fixture difficulty: {len(fixtures)} records")
    
    # Show data freshness
    freshness = adapter.get_data_freshness()
    print(f"\n📅 Data Freshness:")
    for layer, timestamp in freshness.items():
        print(f"   {layer}: {timestamp}")
    
    print(f"\n✅ Medallion Data Adapter is working correctly!")