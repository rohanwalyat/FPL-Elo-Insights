#!/usr/bin/env python3
"""
Medallion Architecture Configuration for FPL Data Pipeline

Defines the structure and configuration for Bronze, Silver, and Gold data layers.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any
from enum import Enum

class DataLayer(Enum):
    BRONZE = "bronze"
    SILVER = "silver" 
    GOLD = "gold"

class DataSource(Enum):
    FPL_API = "fpl_api"
    GITHUB_DATA = "github_data"
    BETTING_ODDS = "betting_odds"
    DRAFT_LEAGUE = "draft_league"

@dataclass
class MedallionConfig:
    """Configuration for medallion architecture layers"""
    
    # Base paths
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent.parent)
    data_root: Path = field(default=None)
    
    # Layer paths
    bronze_path: Path = field(default=None)
    silver_path: Path = field(default=None) 
    gold_path: Path = field(default=None)
    
    # Database configuration
    db_config: Dict[str, str] = field(default_factory=dict)
    
    # Data retention policies (days)
    bronze_retention_days: int = 90
    silver_retention_days: int = 365
    gold_retention_days: int = 1095  # 3 years
    
    def __post_init__(self):
        """Initialize paths after creation"""
        if self.data_root is None:
            self.data_root = self.project_root / "data"
            
        self.bronze_path = self.data_root / "raw"
        self.silver_path = self.data_root / "processed"
        self.gold_path = self.data_root / "analytics"
        
        # Ensure directories exist
        self.bronze_path.mkdir(parents=True, exist_ok=True)
        self.silver_path.mkdir(parents=True, exist_ok=True)
        self.gold_path.mkdir(parents=True, exist_ok=True)
        
        # Default database config
        if not self.db_config:
            self.db_config = {
                'host': 'localhost',
                'database': 'fpl_elo',
                'user': 'postgres',
                'password': os.getenv('POSTGRES_PASSWORD', '')
            }
    
    def get_layer_path(self, layer: DataLayer, source: DataSource = None, date_partition: str = None) -> Path:
        """Get path for specific layer, optionally partitioned by source and date"""
        
        base_path = {
            DataLayer.BRONZE: self.bronze_path,
            DataLayer.SILVER: self.silver_path,
            DataLayer.GOLD: self.gold_path
        }[layer]
        
        path = base_path
        
        if source:
            path = path / source.value
            
        if date_partition:
            path = path / "daily" / date_partition
            
        path.mkdir(parents=True, exist_ok=True)
        return path

# Data source configurations
BRONZE_SOURCES = {
    DataSource.FPL_API: {
        'endpoints': [
            'https://draft.premierleague.com/api/bootstrap-static',
            'https://draft.premierleague.com/api/fixtures',
        ],
        'file_formats': ['json'],
        'update_frequency': 'hourly',
        'validation_rules': {
            'required_keys': ['elements', 'teams', 'events'],
            'max_file_size_mb': 50
        }
    },
    
    DataSource.GITHUB_DATA: {
        'source_patterns': [
            'data/raw/pl_history/2025-2026/By Gameweek/GW*/players.csv',
            'data/raw/pl_history/2025-2026/By Gameweek/GW*/matches.csv',
            'data/raw/pl_history/2025-2026/By Gameweek/GW*/teams.csv',
            'data/raw/pl_history/2025-2026/By Gameweek/GW*/playermatchstats.csv'
        ],
        'file_formats': ['csv'],
        'update_frequency': 'daily',
        'validation_rules': {
            'min_rows': 1,
            'required_columns': ['id', 'web_name']  # Varies by file type
        }
    },
    
    DataSource.BETTING_ODDS: {
        'endpoints': [],  # Add your betting odds endpoints
        'file_formats': ['json', 'csv'],
        'update_frequency': 'hourly',
        'validation_rules': {
            'required_keys': ['match_id', 'odds'],
            'max_file_age_hours': 24
        }
    },
    
    DataSource.DRAFT_LEAGUE: {
        'endpoints': [
            'https://draft.premierleague.com/api/league/{league_id}/details',
            'https://draft.premierleague.com/api/league/{league_id}/element-status'
        ],
        'file_formats': ['json'],
        'update_frequency': 'daily',
        'validation_rules': {
            'required_keys': ['league', 'league_entries'],
            'max_file_size_mb': 10
        }
    }
}

# Silver layer transformations
SILVER_TRANSFORMATIONS = {
    'players': {
        'source': [DataSource.FPL_API, DataSource.GITHUB_DATA],
        'primary_key': 'player_id',
        'deduplication_strategy': 'latest_timestamp',
        'data_quality_checks': [
            'no_null_player_id',
            'valid_team_mapping',
            'reasonable_stats_ranges'
        ]
    },
    
    'matches': {
        'source': [DataSource.GITHUB_DATA],
        'primary_key': 'match_id', 
        'deduplication_strategy': 'latest_timestamp',
        'data_quality_checks': [
            'no_null_match_id',
            'valid_date_format',
            'home_away_teams_different'
        ]
    },
    
    'betting_odds': {
        'source': [DataSource.BETTING_ODDS],
        'primary_key': ['match_id', 'bookmaker', 'timestamp'],
        'deduplication_strategy': 'keep_all',
        'data_quality_checks': [
            'odds_within_reasonable_range',
            'match_exists_in_fixtures'
        ]
    }
}

# Gold layer aggregations
GOLD_AGGREGATIONS = {
    'expected_points': {
        'sources': ['players', 'matches', 'betting_odds'],
        'refresh_strategy': 'full_refresh',
        'dependencies': ['fixture_difficulty', 'player_performance']
    },
    
    'player_performance': {
        'sources': ['players', 'matches'],
        'refresh_strategy': 'incremental',
        'partition_column': 'gameweek'
    },
    
    'team_analytics': {
        'sources': ['matches', 'players'],
        'refresh_strategy': 'incremental',
        'aggregation_level': 'team_gameweek'
    }
}

# Data quality rules
DATA_QUALITY_RULES = {
    'completeness': {
        'player_id': {'null_threshold': 0.0},
        'web_name': {'null_threshold': 0.0},
        'total_points': {'null_threshold': 0.05}
    },
    
    'validity': {
        'total_points': {'min_value': 0, 'max_value': 500},
        'goals_scored': {'min_value': 0, 'max_value': 10},
        'minutes_played': {'min_value': 0, 'max_value': 90}
    },
    
    'consistency': {
        'team_mapping': 'team_id_exists_in_teams_table',
        'match_dates': 'match_date_within_season_bounds'
    }
}