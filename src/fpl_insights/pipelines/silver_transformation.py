#!/usr/bin/env python3
"""
Silver Layer Data Transformation

Transforms bronze layer raw data into clean, validated, and normalized data
ready for business logic application in the gold layer.
"""

import json
import pandas as pd
import psycopg2
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from medallion_config import MedallionConfig, DataSource, DataLayer

@dataclass
class TransformationResult:
    """Result of a data transformation"""
    success: bool
    record_count: int
    errors: List[str]
    warnings: List[str]
    output_path: Optional[Path] = None

class DataQualityValidator:
    """Validates data quality according to defined rules"""
    
    def __init__(self):
        self.quality_rules = {
            'completeness': {
                'player_id': {'null_threshold': 0.0},
                'web_name': {'null_threshold': 0.0},
                'team_code': {'null_threshold': 0.05}
            },
            'validity': {
                'total_points': {'min_value': 0, 'max_value': 500},
                'goals_scored': {'min_value': 0, 'max_value': 15},
                'minutes_played': {'min_value': 0, 'max_value': 90}
            }
        }
    
    def validate_completeness(self, df: pd.DataFrame) -> List[str]:
        """Check for missing/null values"""
        errors = []
        
        for column, rule in self.quality_rules['completeness'].items():
            if column in df.columns:
                null_pct = df[column].isnull().sum() / len(df)
                if null_pct > rule['null_threshold']:
                    errors.append(f"{column} has {null_pct:.2%} null values (threshold: {rule['null_threshold']:.2%})")
        
        return errors
    
    def validate_ranges(self, df: pd.DataFrame) -> List[str]:
        """Check for values outside expected ranges"""
        errors = []
        
        for column, rule in self.quality_rules['validity'].items():
            if column in df.columns:
                min_val, max_val = rule['min_value'], rule['max_value']
                out_of_range = df[(df[column] < min_val) | (df[column] > max_val)]
                
                if len(out_of_range) > 0:
                    errors.append(f"{column} has {len(out_of_range)} values outside range [{min_val}, {max_val}]")
        
        return errors
    
    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[List[str], List[str]]:
        """Validate entire dataframe and return errors and warnings"""
        errors = []
        warnings = []
        
        # Basic structure checks - treat empty dataframes as warnings, not errors for optional data
        if df.empty:
            warnings.append("DataFrame is empty")
            return [], warnings
        
        # Completeness checks
        completeness_errors = self.validate_completeness(df)
        errors.extend(completeness_errors)
        
        # Range checks
        range_errors = self.validate_ranges(df)
        warnings.extend(range_errors)  # Treat range issues as warnings initially
        
        return errors, warnings

class SilverTransformationManager:
    """Manages transformation from bronze to silver layer"""
    
    def __init__(self, config: MedallionConfig):
        self.config = config
        self.validator = DataQualityValidator()
    
    def get_latest_bronze_data(self, source: DataSource, file_pattern: str) -> Optional[Path]:
        """Get the most recent bronze data file for a source"""
        bronze_source_path = self.config.get_layer_path(DataLayer.BRONZE, source)
        
        # Look for files in daily partitions (most recent first)
        daily_dirs = sorted(
            [d for d in bronze_source_path.glob("daily/*") if d.is_dir()],
            reverse=True
        )
        
        for daily_dir in daily_dirs:
            matching_files = list(daily_dir.glob(file_pattern))
            if matching_files:
                return matching_files[0]  # Return most recent
        
        return None
    
    def normalize_player_data(self, bronze_data: Dict) -> pd.DataFrame:
        """Normalize player data from FPL API format"""
        if 'elements' not in bronze_data:
            raise ValueError("No 'elements' found in bronze data")
        
        players = []
        for element in bronze_data['elements']:
            player = {
                'player_id': element['id'],
                'web_name': element['web_name'],
                'first_name': element['first_name'],
                'second_name': element['second_name'],
                'full_name': f"{element['first_name']} {element['second_name']}",
                'position': self.map_position(element['element_type']),
                'team_code': element['team'],
                'total_points': element['total_points'],
                'points_per_game': element['points_per_game'],
                'form': element['form'],
                'goals_scored': element['goals_scored'],
                'assists': element['assists'],
                'minutes_played': element['minutes'],
                'now_cost': element.get('now_cost', 0) / 10.0 if element.get('now_cost') else 0.0,  # Convert to pounds, default 0 for draft
                'selected_by_percent': element.get('selected_by_percent', 0.0),
                'status': element['status'],
                'ingestion_timestamp': datetime.now(timezone.utc).isoformat()
            }
            players.append(player)
        
        return pd.DataFrame(players)
    
    def map_position(self, element_type: int) -> str:
        """Map FPL element_type to position name"""
        position_map = {1: 'Goalkeeper', 2: 'Defender', 3: 'Midfielder', 4: 'Forward'}
        return position_map.get(element_type, 'Unknown')
    
    def normalize_team_data(self, bronze_data: Dict) -> pd.DataFrame:
        """Normalize team data from FPL API format"""
        if 'teams' not in bronze_data:
            raise ValueError("No 'teams' found in bronze data")
        
        teams = []
        for team in bronze_data['teams']:
            team_record = {
                'team_id': team['id'],
                'team_code': team['code'],
                'name': team['name'],
                'short_name': team['short_name'],
                'pulse_id': team.get('pulse_id', 0),
                'strength': team.get('strength', 0),
                'strength_overall_home': team.get('strength_overall_home', 0),
                'strength_overall_away': team.get('strength_overall_away', 0),
                'strength_attack_home': team.get('strength_attack_home', 0),
                'strength_attack_away': team.get('strength_attack_away', 0),
                'strength_defence_home': team.get('strength_defence_home', 0),
                'strength_defence_away': team.get('strength_defence_away', 0),
                'ingestion_timestamp': datetime.now(timezone.utc).isoformat()
            }
            teams.append(team_record)
        
        return pd.DataFrame(teams)
    
    def normalize_match_data(self, match_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize match data from CSV format"""
        # Standardize column names
        column_mapping = {
            'id': 'match_id',
            'match_id': 'match_id',
            'gameweek': 'gameweek',
            'kickoff_time': 'kickoff_time',
            'team_h': 'home_team',
            'team_a': 'away_team',
            'team_h_score': 'home_score',
            'team_a_score': 'away_score',
            'finished': 'finished'
        }
        
        df = match_df.copy()
        
        # Rename columns if they exist
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
        
        # Add metadata
        df['ingestion_timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Convert data types
        if 'finished' in df.columns:
            df['finished'] = df['finished'].astype(bool)
        
        return df
    
    def transform_fpl_api_to_silver(self) -> Dict[str, TransformationResult]:
        """Transform FPL API bronze data to silver layer"""
        results = {}
        
        # Get latest bootstrap-static data
        bronze_file = self.get_latest_bronze_data(DataSource.FPL_API, "bootstrap-static.json")
        
        if not bronze_file:
            return {'error': TransformationResult(
                success=False, 
                record_count=0, 
                errors=["No bronze FPL API data found"],
                warnings=[]
            )}
        
        try:
            # Load bronze data
            with open(bronze_file, 'r') as f:
                bronze_data = json.load(f)
            
            silver_path = self.config.get_layer_path(DataLayer.SILVER)
            
            # Transform players
            players_df = self.normalize_player_data(bronze_data)
            errors, warnings = self.validator.validate_dataframe(players_df)
            
            if not errors:  # Only save if no critical errors
                players_output = silver_path / "players" / "players.parquet"
                players_output.parent.mkdir(parents=True, exist_ok=True)
                players_df.to_parquet(players_output, index=False)
                
                results['players'] = TransformationResult(
                    success=True,
                    record_count=len(players_df),
                    errors=[],
                    warnings=warnings,
                    output_path=players_output
                )
            else:
                results['players'] = TransformationResult(
                    success=False,
                    record_count=len(players_df),
                    errors=errors,
                    warnings=warnings
                )
            
            # Transform teams
            teams_df = self.normalize_team_data(bronze_data)
            teams_errors, teams_warnings = self.validator.validate_dataframe(teams_df)
            
            if not teams_errors:
                teams_output = silver_path / "teams" / "teams.parquet"
                teams_output.parent.mkdir(parents=True, exist_ok=True)
                teams_df.to_parquet(teams_output, index=False)
                
                results['teams'] = TransformationResult(
                    success=True,
                    record_count=len(teams_df),
                    errors=[],
                    warnings=teams_warnings,
                    output_path=teams_output
                )
            else:
                results['teams'] = TransformationResult(
                    success=False,
                    record_count=len(teams_df),
                    errors=teams_errors,
                    warnings=teams_warnings
                )
            
        except Exception as e:
            results['fpl_api_error'] = TransformationResult(
                success=False,
                record_count=0,
                errors=[str(e)],
                warnings=[]
            )
        
        return results
    
    def transform_github_data_to_silver(self) -> Dict[str, TransformationResult]:
        """Transform GitHub CSV bronze data to silver layer"""
        results = {}
        silver_path = self.config.get_layer_path(DataLayer.SILVER)
        
        csv_files = ['matches.csv', 'playermatchstats.csv']
        
        for csv_file in csv_files:
            bronze_file = self.get_latest_bronze_data(DataSource.GITHUB_DATA, csv_file)
            
            if not bronze_file:
                results[csv_file] = TransformationResult(
                    success=False,
                    record_count=0,
                    errors=[f"No bronze {csv_file} data found"],
                    warnings=[]
                )
                continue
            
            try:
                # Load and transform
                df = pd.read_csv(bronze_file)
                
                if csv_file == 'matches.csv':
                    df = self.normalize_match_data(df)
                    output_dir = "matches"
                else:
                    # Basic normalization for playermatchstats
                    df['ingestion_timestamp'] = datetime.now(timezone.utc).isoformat()
                    output_dir = "playermatchstats"
                
                # Validate
                errors, warnings = self.validator.validate_dataframe(df)
                
                if not errors:
                    output_path = silver_path / output_dir / f"{csv_file.replace('.csv', '.parquet')}"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    df.to_parquet(output_path, index=False)
                    
                    results[csv_file] = TransformationResult(
                        success=True,
                        record_count=len(df),
                        errors=[],
                        warnings=warnings,
                        output_path=output_path
                    )
                else:
                    results[csv_file] = TransformationResult(
                        success=False,
                        record_count=len(df),
                        errors=errors,
                        warnings=warnings
                    )
                
            except Exception as e:
                results[csv_file] = TransformationResult(
                    success=False,
                    record_count=0,
                    errors=[str(e)],
                    warnings=[]
                )
        
        return results
    
    def run_full_silver_transformation(self) -> Dict[str, Dict[str, TransformationResult]]:
        """Run complete silver layer transformation"""
        print("🥈 SILVER LAYER TRANSFORMATION STARTED")
        print("=" * 50)
        
        results = {}
        
        # Transform FPL API data
        print("📊 Transforming FPL API data...")
        results['fpl_api'] = self.transform_fpl_api_to_silver()
        
        # Transform GitHub data
        print("📊 Transforming GitHub CSV data...")
        results['github_data'] = self.transform_github_data_to_silver()
        
        # Print summary
        print(f"\n✅ Silver transformation complete!")
        total_success = sum(1 for source_results in results.values() 
                          for result in source_results.values() 
                          if result.success)
        total_attempted = sum(len(source_results) for source_results in results.values())
        
        print(f"Successful transformations: {total_success}/{total_attempted}")
        
        return results

def main():
    """Main execution for silver layer transformation"""
    config = MedallionConfig()
    transformer = SilverTransformationManager(config)
    
    results = transformer.run_full_silver_transformation()
    
    # Print detailed results
    print(f"\n📊 TRANSFORMATION SUMMARY:")
    for source, source_results in results.items():
        print(f"\n{source.upper()}:")
        for data_type, result in source_results.items():
            status = "✅" if result.success else "❌"
            print(f"  {status} {data_type}: {result.record_count} records")
            if result.errors:
                for error in result.errors:
                    print(f"    ❌ {error}")
            if result.warnings:
                for warning in result.warnings[:3]:  # Show first 3 warnings
                    print(f"    ⚠️  {warning}")

if __name__ == "__main__":
    main()