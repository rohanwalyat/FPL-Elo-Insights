#!/usr/bin/env python3
"""
Gold Layer Data Aggregation

Transforms silver layer clean data into business-ready analytics tables
with calculated metrics, aggregations, and machine learning features.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys
import os

# Add scripts directory for imports
script_dir = Path(__file__).parent.parent / "analysis" / "scripts"
sys.path.append(str(script_dir))

from medallion_config import MedallionConfig, DataLayer
# Removed external dependencies that make API calls
# All calculations will be done using bronze layer data only

class GoldAggregationManager:
    """Manages aggregation and feature engineering for gold layer"""
    
    def __init__(self, config: MedallionConfig):
        self.config = config
        # FPL scoring rules for expected points calculation
        self.SCORING_RULES = {
            'goals': {'Goalkeeper': 6, 'Defender': 6, 'Midfielder': 5, 'Forward': 4},
            'assists': 3,
            'clean_sheets': {'Goalkeeper': 4, 'Defender': 4, 'Midfielder': 1, 'Forward': 0},
            'saves': 1/3,  # 1 point per 3 saves
            'appearance': 1,  # Starting a match
            'minutes_60_plus': 1  # Playing 60+ minutes
        }
    
    def calculate_expected_points_bronze_only(self, position: str, matches_played: int, 
                                            avg_minutes: float, avg_goals: float, avg_assists: float,
                                            avg_xg: float, avg_xa: float) -> float:
        """Calculate expected points using only bronze layer data without API calls"""
        if matches_played == 0 or avg_minutes == 0:
            return 0.0
        
        # Enhanced model: blend actual and expected stats based on sample size
        if matches_played <= 3:
            # Small sample: 20% actual, 80% expected
            goal_metric = 0.2 * avg_goals + 0.8 * avg_xg
            assist_metric = 0.2 * avg_assists + 0.8 * avg_xa
        elif matches_played <= 6:
            # Medium sample: 50% actual, 50% expected
            goal_metric = 0.5 * avg_goals + 0.5 * avg_xg
            assist_metric = 0.5 * avg_assists + 0.5 * avg_xa
        else:
            # Large sample: 70% actual, 30% expected
            goal_metric = 0.7 * avg_goals + 0.3 * avg_xg
            assist_metric = 0.7 * avg_assists + 0.3 * avg_xa
        
        # Calculate points based on FPL scoring rules
        goal_points = goal_metric * self.SCORING_RULES['goals'][position]
        assist_points = assist_metric * self.SCORING_RULES['assists']
        
        # Playing time points
        appearance_points = self.SCORING_RULES['appearance'] if avg_minutes > 0 else 0
        minutes_bonus = self.SCORING_RULES['minutes_60_plus'] if avg_minutes >= 60 else 0
        
        total_expected = goal_points + assist_points + appearance_points + minutes_bonus
        return round(total_expected, 2)
    
    def load_silver_data(self, data_type: str) -> Optional[pd.DataFrame]:
        """Load data from silver layer"""
        silver_path = self.config.get_layer_path(DataLayer.SILVER)
        file_path = silver_path / data_type / f"{data_type}.parquet"
        
        if file_path.exists():
            return pd.read_parquet(file_path)
        return None
    
    def save_gold_data(self, df: pd.DataFrame, data_type: str, partition_col: str = None) -> Path:
        """Save data to gold layer with optional partitioning"""
        gold_path = self.config.get_layer_path(DataLayer.GOLD)
        output_dir = gold_path / data_type
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if partition_col and partition_col in df.columns:
            # Save partitioned data
            for partition_value in df[partition_col].unique():
                partition_df = df[df[partition_col] == partition_value]
                partition_path = output_dir / f"{partition_col}={partition_value}"
                partition_path.mkdir(exist_ok=True)
                partition_df.to_parquet(partition_path / "data.parquet", index=False)
            output_path = output_dir
        else:
            # Save as single file
            output_path = output_dir / f"{data_type}.parquet"
            df.to_parquet(output_path, index=False)
        
        return output_path
    
    def calculate_player_performance_metrics(self) -> pd.DataFrame:
        """Calculate comprehensive player performance metrics"""
        print("📊 Calculating player performance metrics...")
        
        # Load required data
        players_df = self.load_silver_data('players')
        playermatchstats_df = self.load_silver_data('playermatchstats')
        matches_df = self.load_silver_data('matches')
        
        if players_df is None:
            raise ValueError("Players data not found in silver layer")
        
        performance_metrics = []
        
        for _, player in players_df.iterrows():
            player_id = player['player_id']
            
            # Get player match stats if available
            if playermatchstats_df is not None:
                player_matches = playermatchstats_df[
                    playermatchstats_df['player_id'] == player_id
                ]
                
                # Calculate current season metrics from match data
                matches_played = len(player_matches)
                total_minutes = player_matches['minutes_played'].sum()
                total_goals = player_matches['goals'].sum()
                total_assists = player_matches['assists'].sum()
                total_xg = player_matches['xg'].sum() if 'xg' in player_matches.columns else 0
                total_xa = player_matches['xa'].sum() if 'xa' in player_matches.columns else 0
                
                # Per 90 calculations
                minutes_per_90 = max(total_minutes, 1) / 90
                goals_per_90 = total_goals / minutes_per_90 if minutes_per_90 > 0 else 0
                assists_per_90 = total_assists / minutes_per_90 if minutes_per_90 > 0 else 0
                xg_per_90 = total_xg / minutes_per_90 if minutes_per_90 > 0 else 0
                xa_per_90 = total_xa / minutes_per_90 if minutes_per_90 > 0 else 0
                
                avg_minutes_per_match = total_minutes / matches_played if matches_played > 0 else 0
            else:
                # Fall back to FPL API data only
                matches_played = 0
                total_minutes = pd.to_numeric(player.get('minutes_played', 0), errors='coerce') or 0
                total_goals = pd.to_numeric(player.get('goals_scored', 0), errors='coerce') or 0
                total_assists = pd.to_numeric(player.get('assists', 0), errors='coerce') or 0
                goals_per_90 = 0
                assists_per_90 = 0
                xg_per_90 = 0
                xa_per_90 = 0
                avg_minutes_per_match = 0
            
            # Calculate expected points using bronze layer data only
            try:
                expected_points = self.calculate_expected_points_bronze_only(
                    position=player['position'],
                    matches_played=matches_played,
                    avg_minutes=avg_minutes_per_match,
                    avg_goals=total_goals / max(matches_played, 1),
                    avg_assists=total_assists / max(matches_played, 1),
                    avg_xg=total_xg / max(matches_played, 1),
                    avg_xa=total_xa / max(matches_played, 1)
                )
            except Exception as e:
                print(f"⚠️  Error calculating expected points for player {player_id}: {e}")
                expected_points = 0
            
            # Compile metrics
            metrics = {
                'player_id': player_id,
                'web_name': player['web_name'],
                'full_name': player['full_name'],
                'position': player['position'],
                'team_code': player['team_code'],
                
                # Current season stats
                'matches_played': matches_played,
                'total_minutes': total_minutes,
                'avg_minutes_per_match': avg_minutes_per_match,
                'total_goals': total_goals,
                'total_assists': total_assists,
                'total_xg': total_xg,
                'total_xa': total_xa,
                
                # Per 90 metrics
                'goals_per_90': round(goals_per_90, 3),
                'assists_per_90': round(assists_per_90, 3),
                'xg_per_90': round(xg_per_90, 3),
                'xa_per_90': round(xa_per_90, 3),
                
                # FPL metrics
                'fpl_total_points': player.get('total_points', 0),
                'fpl_points_per_game': player.get('points_per_game', 0),
                'fpl_form': player.get('form', 0),
                'fpl_cost': player.get('now_cost', 0),
                'selected_by_percent': player.get('selected_by_percent', 0),
                
                # Advanced metrics
                'expected_points': round(expected_points, 2),
                'points_over_expected': round(pd.to_numeric(player.get('total_points', 0), errors='coerce') - expected_points, 2),
                'value_rating': round(pd.to_numeric(player.get('points_per_game', 0), errors='coerce') / max(pd.to_numeric(player.get('now_cost', 1), errors='coerce'), 0.1), 2),
                
                # Metadata
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            performance_metrics.append(metrics)
        
        df = pd.DataFrame(performance_metrics)
        print(f"✅ Calculated performance metrics for {len(df)} players")
        return df
    
    def calculate_team_analytics(self) -> pd.DataFrame:
        """Calculate team-level analytics and performance metrics"""
        print("📊 Calculating team analytics...")
        
        # Load required data
        teams_df = self.load_silver_data('teams')
        matches_df = self.load_silver_data('matches')
        
        if teams_df is None:
            raise ValueError("Teams data not found in silver layer")
        
        team_analytics = []
        
        for _, team in teams_df.iterrows():
            team_id = team['team_id']
            
            # Calculate team stats from matches if available
            if matches_df is not None:
                finished_matches = matches_df[matches_df['finished'] == True]
                
                # Home matches
                home_matches = finished_matches[finished_matches['home_team'] == team_id]
                home_goals_for = home_matches['home_score'].sum()
                home_goals_against = home_matches['away_score'].sum()
                home_wins = len(home_matches[home_matches['home_score'] > home_matches['away_score']])
                home_draws = len(home_matches[home_matches['home_score'] == home_matches['away_score']])
                home_losses = len(home_matches[home_matches['home_score'] < home_matches['away_score']])
                
                # Away matches  
                away_matches = finished_matches[finished_matches['away_team'] == team_id]
                away_goals_for = away_matches['away_score'].sum()
                away_goals_against = away_matches['home_score'].sum()
                away_wins = len(away_matches[away_matches['away_score'] > away_matches['home_score']])
                away_draws = len(away_matches[away_matches['away_score'] == away_matches['home_score']])
                away_losses = len(away_matches[away_matches['away_score'] < away_matches['home_score']])
                
                # Combined stats
                total_matches = len(home_matches) + len(away_matches)
                total_goals_for = home_goals_for + away_goals_for
                total_goals_against = home_goals_against + away_goals_against
                total_wins = home_wins + away_wins
                total_draws = home_draws + away_draws
                total_losses = home_losses + away_losses
                total_points = (total_wins * 3) + total_draws
                
                # Performance metrics
                goals_per_game = total_goals_for / max(total_matches, 1)
                goals_conceded_per_game = total_goals_against / max(total_matches, 1)
                points_per_game = total_points / max(total_matches, 1)
                win_percentage = total_wins / max(total_matches, 1) * 100
                clean_sheet_percentage = 0  # Would need more detailed match data
                
            else:
                # No match data available
                total_matches = 0
                total_goals_for = 0
                total_goals_against = 0
                goals_per_game = 0
                goals_conceded_per_game = 0
                points_per_game = 0
                win_percentage = 0
                clean_sheet_percentage = 0
                home_goals_for = away_goals_for = 0
                home_goals_against = away_goals_against = 0
            
            analytics = {
                'team_id': team_id,
                'team_code': team['team_code'],
                'name': team['name'],
                'short_name': team['short_name'],
                
                # Match statistics
                'matches_played': total_matches,
                'goals_for': total_goals_for,
                'goals_against': total_goals_against,
                'goal_difference': total_goals_for - total_goals_against,
                
                # Home/Away split
                'home_goals_for': home_goals_for,
                'home_goals_against': home_goals_against,
                'away_goals_for': away_goals_for,
                'away_goals_against': away_goals_against,
                
                # Performance metrics
                'goals_per_game': round(goals_per_game, 2),
                'goals_conceded_per_game': round(goals_conceded_per_game, 2),
                'points_per_game': round(points_per_game, 2),
                'win_percentage': round(win_percentage, 1),
                'clean_sheet_percentage': round(clean_sheet_percentage, 1),
                
                # FPL strength ratings
                'strength_overall_home': team.get('strength_overall_home', 0),
                'strength_overall_away': team.get('strength_overall_away', 0),
                'strength_attack_home': team.get('strength_attack_home', 0),
                'strength_attack_away': team.get('strength_attack_away', 0),
                'strength_defence_home': team.get('strength_defence_home', 0),
                'strength_defence_away': team.get('strength_defence_away', 0),
                
                # Metadata
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            team_analytics.append(analytics)
        
        df = pd.DataFrame(team_analytics)
        print(f"✅ Calculated analytics for {len(df)} teams")
        return df
    
    def calculate_fixture_difficulty_scores(self) -> pd.DataFrame:
        """Calculate fixture difficulty scores using bronze layer data only"""
        print("📊 Calculating fixture difficulty scores...")
        
        # Load teams and matches from silver layer (cleaned bronze data)
        teams_df = self.load_silver_data('teams')
        matches_df = self.load_silver_data('matches')
        
        if teams_df is None:
            print("⚠️  No teams data available")
            return pd.DataFrame()
        
        fixture_scores = []
        for _, team in teams_df.iterrows():
            team_id = team['team_id']
            
            # Simple difficulty rating based on FPL strength ratings from bronze data
            home_attack_rating = team.get('strength_attack_home', 50) / 100
            away_attack_rating = team.get('strength_attack_away', 50) / 100  
            home_defence_rating = team.get('strength_defence_home', 50) / 100
            away_defence_rating = team.get('strength_defence_away', 50) / 100
            
            # If no FPL strength data, use basic team analytics
            if matches_df is not None and len(matches_df) > 0:
                finished_matches = matches_df[matches_df.get('finished', False) == True]
                home_matches = finished_matches[finished_matches.get('home_team') == team_id]
                away_matches = finished_matches[finished_matches.get('away_team') == team_id]
                
                if len(home_matches) > 0:
                    avg_home_goals = home_matches.get('home_score', pd.Series([0])).mean()
                    home_attack_rating = max(home_attack_rating, avg_home_goals / 2)  # Normalize to 0-1 range
                
                if len(away_matches) > 0:
                    avg_away_goals = away_matches.get('away_score', pd.Series([0])).mean()
                    away_attack_rating = max(away_attack_rating, avg_away_goals / 2)
            
            score = {
                'team_id': team_id,
                'team_name': team.get('name', 'Unknown'),
                'fpl_team_id': team_id,  # Assuming team_id is FPL ID
                'home_attack_difficulty': round(home_attack_rating, 3),
                'away_attack_difficulty': round(away_attack_rating, 3),
                'home_defence_difficulty': round(1 - home_defence_rating, 3),  # Lower defence = higher difficulty for opponents
                'away_defence_difficulty': round(1 - away_defence_rating, 3),
                'overall_difficulty_rating': round((home_attack_rating + away_attack_rating + (2 - home_defence_rating - away_defence_rating)) / 4, 3),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            fixture_scores.append(score)
        
        df = pd.DataFrame(fixture_scores)
        print(f"✅ Calculated fixture difficulty for {len(df)} teams using bronze layer data only")
        return df
    
    def calculate_ml_features(self) -> pd.DataFrame:
        """Calculate machine learning features for predictive models"""
        print("📊 Calculating ML features...")
        
        # Load performance metrics (should be calculated first)
        performance_df = self.load_silver_data('player_performance')
        if performance_df is None:
            print("⚠️  Player performance data not available for ML features")
            return pd.DataFrame()
        
        ml_features = performance_df.copy()
        
        # Add derived features for ML
        ml_features['minutes_per_match_ratio'] = ml_features['avg_minutes_per_match'] / 90
        ml_features['goal_conversion_rate'] = ml_features['total_goals'] / np.maximum(ml_features['total_xg'], 1)
        ml_features['assist_conversion_rate'] = ml_features['total_assists'] / np.maximum(ml_features['total_xa'], 1)
        ml_features['points_per_minute'] = ml_features['fpl_total_points'] / np.maximum(ml_features['total_minutes'], 1)
        
        # Position-specific features
        ml_features['is_goalkeeper'] = (ml_features['position'] == 'Goalkeeper').astype(int)
        ml_features['is_defender'] = (ml_features['position'] == 'Defender').astype(int)
        ml_features['is_midfielder'] = (ml_features['position'] == 'Midfielder').astype(int)
        ml_features['is_forward'] = (ml_features['position'] == 'Forward').astype(int)
        
        # Value features
        ml_features['value_score'] = ml_features['fpl_points_per_game'] / np.maximum(ml_features['fpl_cost'], 0.1)
        ml_features['form_momentum'] = ml_features['fpl_form'] / np.maximum(ml_features['fpl_points_per_game'], 0.1)
        
        # Clean up any infinite or NaN values
        ml_features = ml_features.replace([np.inf, -np.inf], 0)
        ml_features = ml_features.fillna(0)
        
        print(f"✅ Calculated ML features for {len(ml_features)} players")
        return ml_features
    
    def run_full_gold_aggregation(self) -> Dict[str, Path]:
        """Run complete gold layer aggregation"""
        print("🥇 GOLD LAYER AGGREGATION STARTED") 
        print("=" * 50)
        
        results = {}
        
        try:
            # 1. Player Performance Metrics
            performance_df = self.calculate_player_performance_metrics()
            if not performance_df.empty:
                results['player_performance'] = self.save_gold_data(
                    performance_df, 
                    'player_performance'
                )
            
            # 2. Team Analytics
            team_analytics_df = self.calculate_team_analytics()
            if not team_analytics_df.empty:
                results['team_analytics'] = self.save_gold_data(
                    team_analytics_df,
                    'team_analytics'
                )
            
            # 3. Fixture Difficulty
            fixture_difficulty_df = self.calculate_fixture_difficulty_scores()
            if not fixture_difficulty_df.empty:
                results['fixture_difficulty'] = self.save_gold_data(
                    fixture_difficulty_df,
                    'fixture_difficulty'
                )
            
            # 4. ML Features (depends on player performance)
            ml_features_df = self.calculate_ml_features()
            if not ml_features_df.empty:
                results['ml_features'] = self.save_gold_data(
                    ml_features_df,
                    'ml_features',
                    partition_col='position'
                )
            
            print(f"\n✅ Gold aggregation complete!")
            print(f"Generated {len(results)} gold datasets")
            
        except Exception as e:
            print(f"❌ Error during gold aggregation: {e}")
            
        return results

def main():
    """Main execution for gold layer aggregation"""
    config = MedallionConfig()
    aggregator = GoldAggregationManager(config)
    
    results = aggregator.run_full_gold_aggregation()
    
    print(f"\n📊 GOLD LAYER SUMMARY:")
    for dataset, path in results.items():
        print(f"  ✅ {dataset}: {path}")

if __name__ == "__main__":
    main()