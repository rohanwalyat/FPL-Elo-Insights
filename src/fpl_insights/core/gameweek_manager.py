#!/usr/bin/env python3
"""
Gameweek Manager

Handles dynamic gameweek detection and file naming across the project.
Determines current gameweek, next gameweek, and manages file naming conventions.

Usage:
    from gameweek_manager import GameweekManager
    gw = GameweekManager()
    current_gw = gw.get_current_gameweek()
    next_gw = gw.get_prediction_gameweek()
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import os
from typing import Optional, Tuple

class GameweekManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent.parent.parent
        self.data_dir = self.base_dir / "data" / "analytics"
        self._current_gameweek = None
        self._prediction_gameweek = None
        
    def get_current_gameweek_from_fpl_api(self) -> Optional[int]:
        """Get current gameweek from FPL API"""
        try:
            url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Find current gameweek (the one that's active or just finished)
                current_gw = None
                for event in data['events']:
                    if event['is_current']:
                        current_gw = event['id']
                        break
                
                # If no current gameweek found, look for the next one
                if current_gw is None:
                    for event in data['events']:
                        if event['is_next']:
                            current_gw = event['id'] - 1  # Previous gameweek
                            break
                
                return current_gw
                
        except Exception as e:
            print(f"⚠️  Warning: Could not get gameweek from FPL API: {e}")
            
        return None
        
    def get_current_gameweek_from_files(self) -> Optional[int]:
        """Determine current gameweek from existing files"""
        try:
            # Look for betting odds files to determine latest gameweek
            # Look in all gw folders
            betting_files = list(self.data_dir.glob("gw*/betting_odds_analysis_gw*.csv"))
            if betting_files:
                # Extract gameweek numbers and return the highest
                gameweeks = []
                for file in betting_files:
                    try:
                        gw_num = int(file.stem.split('_gw')[1])
                        gameweeks.append(gw_num)
                    except (IndexError, ValueError):
                        continue
                        
                if gameweeks:
                    return max(gameweeks)
                    
            # Look for expected points files as fallback
            ep_files = list(self.data_dir.glob("all_players_expected_points_gw*.csv"))
            if ep_files:
                gameweeks = []
                for file in ep_files:
                    try:
                        gw_num = int(file.stem.split('_gw')[1])
                        gameweeks.append(gw_num)
                    except (IndexError, ValueError):
                        continue
                        
                if gameweeks:
                    return max(gameweeks)
                    
        except Exception as e:
            print(f"⚠️  Warning: Could not determine gameweek from files: {e}")
            
        return None
        
    def get_current_gameweek(self) -> int:
        """Get the current completed gameweek (with actual data)"""
        if self._current_gameweek is None:
            # Try FPL API first
            gw_from_api = self.get_current_gameweek_from_fpl_api()
            
            # Try files as fallback
            gw_from_files = self.get_current_gameweek_from_files()
            
            # Use API if available, otherwise files, otherwise default to 1
            if gw_from_api is not None:
                self._current_gameweek = gw_from_api
            elif gw_from_files is not None:
                self._current_gameweek = gw_from_files
            else:
                print("⚠️  Warning: Could not determine current gameweek, defaulting to 1")
                self._current_gameweek = 1
                
        return self._current_gameweek
        
    def get_prediction_gameweek(self) -> int:
        """Get the gameweek we're making predictions for (next gameweek)"""
        if self._prediction_gameweek is None:
            self._prediction_gameweek = self.get_current_gameweek() + 1
            
        return self._prediction_gameweek
        
    def set_gameweek_manually(self, current_gw: int):
        """Manually set the current gameweek (for testing or manual override)"""
        self._current_gameweek = current_gw
        self._prediction_gameweek = current_gw + 1
        print(f"✅ Manually set current gameweek to {current_gw}, prediction gameweek to {current_gw + 1}")
        
    def get_file_path(self, file_type: str, gameweek_type: str = "prediction") -> Path:
        """
        Get standardized file paths for different file types with gameweek folder structure
        
        Args:
            file_type: Type of file (e.g., 'expected_points', 'transfer_recommendations', etc.)
            gameweek_type: 'current' for actual data, 'prediction' for prediction data
        """
        gw = self.get_current_gameweek() if gameweek_type == "current" else self.get_prediction_gameweek()
        
        # Create gameweek directory structure in analytics
        gw_data_dir = self.data_dir / f"gw{gw}"
        gw_data_dir.mkdir(parents=True, exist_ok=True)
        
        file_mapping = {
            'expected_points': f'all_players_expected_points_gw{gw}.csv',
            'available_players': f'available_players_gw{gw}.csv',
            'available_players_summary': f'available_players_summary_gw{gw}.csv',
            'transfer_recommendations': f'draft_transfer_recommendations_gw{gw}.csv',
            'squad_analysis': f'squad_expected_points_analysis_gw{gw}.csv',
            'squad_data': f'your_squad_gw{gw}.csv',
            'transfer_summary': f'transfer_summary_gw{gw}.csv',
            'betting_odds': f'betting_odds_analysis_gw{gw}.csv',
            'matchup_analysis': f'draft_matchup_analysis_gw{gw}.csv',
            'matchup_summary': f'draft_matchup_summary_gw{gw}.csv',
            'fixture_multipliers': f'fixture_multipliers_gw{gw}.csv',
            'fixture_difficulty_analysis': f'fixture_difficulty_analysis_gw{gw}.csv',
            'opponent_analysis': f'draft_opponent_analysis_gw{gw}.csv',
            'opponent_summary': f'draft_opponent_summary_gw{gw}.csv'
        }
        
        filename = file_mapping.get(file_type, f'{file_type}_gw{gw}.csv')
        return gw_data_dir / filename
        
    def get_report_path(self, report_type: str, gameweek_type: str = "prediction") -> Path:
        """Get standardized report paths with gameweek folder structure"""
        gw = self.get_current_gameweek() if gameweek_type == "current" else self.get_prediction_gameweek()
        
        # Create gameweek directory structure for reports
        gw_reports_dir = self.base_dir / "reports" / f"gw{gw}"
        gw_reports_dir.mkdir(parents=True, exist_ok=True)
        
        report_mapping = {
            'squad_analysis': f'squad_expected_points_report_gw{gw}.md',
            'available_players': f'weekly_available_players_report_gw{gw}.md',
            'betting_insights': f'betting_odds_fpl_insights_gw{gw}.md',
            'transfer_analysis': f'transfer_analysis_report_gw{gw}.md',
            'fixture_analysis': f'fixture_difficulty_analysis_gw{gw}.md'
        }
        
        filename = report_mapping.get(report_type, f'{report_type}_report_gw{gw}.md')
        return gw_reports_dir / filename
        
    def archive_previous_gameweek(self, target_gameweek: int):
        """Archive files from a specific gameweek to prevent confusion"""
        try:
            archive_dir = self.base_dir / "archive" / f"gw{target_gameweek}"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Move old prediction files to archive
            prediction_patterns = [
                f"*_gw{target_gameweek}.csv",
                f"*_gw{target_gameweek}.md"
            ]
            
            archived_count = 0
            for pattern in prediction_patterns:
                for file_path in self.data_dir.glob(pattern):
                    if 'betting_odds_analysis' not in file_path.name:  # Keep betting odds
                        archive_path = archive_dir / file_path.name
                        file_path.rename(archive_path)
                        archived_count += 1
                        
                # Also check reports
                for file_path in (self.base_dir / "reports").glob(pattern):
                    archive_path = archive_dir / file_path.name
                    file_path.rename(archive_path)
                    archived_count += 1
                    
            if archived_count > 0:
                print(f"📦 Archived {archived_count} files from GW{target_gameweek} to {archive_dir}")
                
        except Exception as e:
            print(f"⚠️  Warning: Could not archive GW{target_gameweek} files: {e}")
            
    def clean_old_files(self, keep_last_n_gameweeks: int = 3):
        """Clean up old files, keeping only the last N gameweeks"""
        try:
            current_gw = self.get_current_gameweek()
            cutoff_gw = current_gw - keep_last_n_gameweeks
            
            if cutoff_gw > 0:
                # Find files older than cutoff
                old_files = []
                for gw in range(1, cutoff_gw):
                    old_files.extend(self.data_dir.glob(f"*_gw{gw}.csv"))
                    old_files.extend((self.base_dir / "reports").glob(f"*_gw{gw}.md"))
                    
                if old_files:
                    for file_path in old_files:
                        try:
                            file_path.unlink()  # Delete file
                        except Exception:
                            pass  # Ignore errors
                            
                    print(f"🧹 Cleaned up {len(old_files)} old files (GW{cutoff_gw} and earlier)")
                    
        except Exception as e:
            print(f"⚠️  Warning: Could not clean old files: {e}")
            
    def get_status_summary(self) -> dict:
        """Get summary of current gameweek status"""
        current_gw = self.get_current_gameweek()
        prediction_gw = self.get_prediction_gameweek()
        
        # Check which files exist
        files_status = {}
        file_types = ['expected_points', 'available_players', 'transfer_recommendations', 
                     'squad_analysis', 'betting_odds']
        
        for file_type in file_types:
            current_file = self.get_file_path(file_type, "current")
            prediction_file = self.get_file_path(file_type, "prediction")
            
            files_status[file_type] = {
                'current_exists': current_file.exists(),
                'prediction_exists': prediction_file.exists(),
                'current_path': current_file,
                'prediction_path': prediction_file
            }
            
        return {
            'current_gameweek': current_gw,
            'prediction_gameweek': prediction_gw,
            'files_status': files_status,
            'data_dir': self.data_dir,
            'reports_dir': self.base_dir / "reports"
        }
        
    def print_status(self):
        """Print current gameweek status"""
        status = self.get_status_summary()
        
        print("🎯 GAMEWEEK STATUS")
        print("=" * 50)
        print(f"Current Gameweek (actual data): {status['current_gameweek']}")
        print(f"Prediction Gameweek: {status['prediction_gameweek']}")
        print(f"Data Directory: {status['data_dir']}")
        print()
        
        print("📁 FILE STATUS:")
        print("-" * 30)
        for file_type, status_info in status['files_status'].items():
            current_status = "✅" if status_info['current_exists'] else "❌"
            prediction_status = "✅" if status_info['prediction_exists'] else "❌"
            print(f"{file_type:20} | Current: {current_status} | Prediction: {prediction_status}")

def main():
    """Demo the gameweek manager"""
    gw_manager = GameweekManager()
    gw_manager.print_status()

if __name__ == "__main__":
    main()