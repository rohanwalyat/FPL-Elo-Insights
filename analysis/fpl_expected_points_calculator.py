#!/usr/bin/env python3
"""
FPL Expected Points Calculator

This script calculates expected FPL points based on player match statistics,
using both actual performance and expected stats (xG, xA) to predict future performance.

FPL Scoring System (2024-25):
- Playing (>=1 min): 1 point
- Playing (>=60 min): 2 points  
- Goal (GK/DEF): 6 points
- Goal (MID): 5 points
- Goal (FWD): 4 points
- Assist: 3 points
- Clean Sheet (GK/DEF): 4 points
- Clean Sheet (MID): 1 point
- Save (GK): 1 point per 3 saves
- Penalty Save (GK): 5 points
- Penalty Miss: -2 points
- Own Goal: -2 points
- Yellow Card: -1 point
- Red Card: -3 points
- 2+ Goals Conceded (GK/DEF): -1 point
- NEW: Defensive Contributions (DEF): 2 points for 10+ CBIT
- NEW: Defensive Contributions (MID/FWD): 2 points for 12+ CBIRT
"""

import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os
from pathlib import Path

class FPLExpectedPointsCalculator:
    def __init__(self):
        """Initialize the FPL calculator"""
        load_dotenv()
        
        # FPL scoring constants
        self.SCORING_RULES = {
            'appearance': 1,
            'played_60_min': 2,
            'goal_points': {
                'Goalkeeper': 6,
                'Defender': 6, 
                'Midfielder': 5,
                'Forward': 4
            },
            'assist': 3,
            'clean_sheet': {
                'Goalkeeper': 4,
                'Defender': 4,
                'Midfielder': 1,
                'Forward': 0
            },
            'saves_per_point': 3,  # 1 point per 3 saves
            'penalty_save': 5,
            'penalty_miss': -2,
            'own_goal': -2,
            'yellow_card': -1,
            'red_card': -3,
            'goals_conceded_penalty': -1,  # -1 for every 2 goals conceded (GK/DEF)
            'defensive_contributions': 2  # NEW: 2 points for defensive contributions
        }

    def get_db_connection(self):
        """Create database connection"""
        return psycopg2.connect(
            host=os.getenv('PGHOST', 'localhost'),
            port=os.getenv('PGPORT', '5432'),
            database=os.getenv('PGDATABASE', 'fpl_elo'),
            user=os.getenv('PGUSER', 'postgres'),
            password=os.getenv('PGPASSWORD')
        )

    def load_player_stats(self):
        """Load player match stats from database"""
        query = """
        SELECT 
            pms.*,
            p.web_name,
            p.first_name,
            p.second_name,
            p.position,
            p.team_code
        FROM playermatchstats pms
        JOIN players p ON pms.player_id = p.player_id
        ORDER BY p.web_name, pms.match_id
        """
        
        conn = self.get_db_connection()
        try:
            df = pd.read_sql_query(query, conn)
            return df
        finally:
            conn.close()

    def load_playerstats_data(self):
        """Load FPL playerstats data from CSV files"""
        import glob
        from pathlib import Path
        
        # Find all playerstats.csv files
        data_dir = Path(__file__).parent.parent / "data"
        playerstats_files = glob.glob(str(data_dir / "**/playerstats.csv"), recursive=True)
        
        if not playerstats_files:
            print("⚠ No playerstats.csv files found")
            return pd.DataFrame()
        
        all_playerstats = []
        for file_path in playerstats_files:
            try:
                df = pd.read_csv(file_path)
                # Add source info
                df['source_file'] = file_path
                all_playerstats.append(df)
            except Exception as e:
                print(f"⚠ Error loading {file_path}: {e}")
        
        if all_playerstats:
            combined_df = pd.concat(all_playerstats, ignore_index=True)
            print(f"✅ Loaded {len(combined_df)} player stat records from {len(playerstats_files)} files")
            return combined_df
        else:
            return pd.DataFrame()

    def calculate_base_fpl_points(self, player_stats):
        """Calculate base FPL points for a player's performance (excluding bonus points)"""
        points = 0
        position = player_stats['position']
        
        # 1. Appearance points
        if player_stats['minutes_played'] >= 1:
            points += self.SCORING_RULES['appearance']
        
        # 2. Playing time bonus (60+ minutes)
        if player_stats['minutes_played'] >= 60:
            points += self.SCORING_RULES['played_60_min'] - self.SCORING_RULES['appearance']
        
        # 3. Goals
        goals = player_stats.get('goals', 0)
        if goals > 0:
            goal_points = self.SCORING_RULES['goal_points'].get(position, 4)
            points += goals * goal_points
        
        # 4. Assists
        assists = player_stats.get('assists', 0)
        if assists > 0:
            points += assists * self.SCORING_RULES['assist']
        
        # 5. Clean sheet (team didn't concede)
        team_goals_conceded = player_stats.get('team_goals_conceded', 0)
        if team_goals_conceded == 0 and player_stats['minutes_played'] >= 60:
            clean_sheet_points = self.SCORING_RULES['clean_sheet'].get(position, 0)
            points += clean_sheet_points
        
        # 6. Saves (Goalkeepers only)
        if position == 'Goalkeeper':
            saves = player_stats.get('saves', 0)
            save_points = saves // self.SCORING_RULES['saves_per_point']
            points += save_points
        
        # 7. Goals conceded penalty (GK/DEF only)
        if position in ['Goalkeeper', 'Defender'] and player_stats['minutes_played'] >= 60:
            goals_conceded_penalty = team_goals_conceded // 2
            points -= goals_conceded_penalty * abs(self.SCORING_RULES['goals_conceded_penalty'])
        
        # 8. Penalty misses
        penalty_misses = player_stats.get('penalties_missed', 0)
        if penalty_misses > 0:
            points += penalty_misses * self.SCORING_RULES['penalty_miss']
        
        # 9. NEW: Defensive Contributions (2024-25)
        defensive_contributions = self.calculate_defensive_contributions(player_stats, position)
        points += defensive_contributions
        
        return points

    def calculate_actual_fpl_points_with_bonus(self, player_stats):
        """Calculate total actual FPL points including bonus points"""
        base_points = self.calculate_base_fpl_points(player_stats)
        bonus_points = player_stats.get('bonus', 0) if pd.notna(player_stats.get('bonus', 0)) else 0
        return base_points + bonus_points

    def calculate_expected_base_fpl_points(self, player_stats):
        """Calculate expected base FPL points using xG and xA (excluding bonus points)"""
        points = 0
        position = player_stats['position']
        
        # 1. Appearance points (if played)
        if player_stats['minutes_played'] >= 1:
            points += self.SCORING_RULES['appearance']
        
        # 2. Playing time bonus (60+ minutes)
        if player_stats['minutes_played'] >= 60:
            points += self.SCORING_RULES['played_60_min'] - self.SCORING_RULES['appearance']
        
        # 3. Expected goals
        xg = player_stats.get('xg', 0)
        if xg > 0:
            goal_points = self.SCORING_RULES['goal_points'].get(position, 4)
            points += xg * goal_points
        
        # 4. Expected assists
        xa = player_stats.get('xa', 0)
        if xa > 0:
            points += xa * self.SCORING_RULES['assist']
        
        # 5. Clean sheet probability (simplified - use actual for now)
        team_goals_conceded = player_stats.get('team_goals_conceded', 0)
        if team_goals_conceded == 0 and player_stats['minutes_played'] >= 60:
            clean_sheet_points = self.SCORING_RULES['clean_sheet'].get(position, 0)
            points += clean_sheet_points
        
        # 6. Saves (use actual saves for now)
        if position == 'Goalkeeper':
            saves = player_stats.get('saves', 0)
            save_points = saves // self.SCORING_RULES['saves_per_point']
            points += save_points
        
        # 7. Goals conceded penalty (use actual)
        if position in ['Goalkeeper', 'Defender'] and player_stats['minutes_played'] >= 60:
            goals_conceded_penalty = team_goals_conceded // 2
            points -= goals_conceded_penalty * abs(self.SCORING_RULES['goals_conceded_penalty'])
        
        # 8. Penalty misses (use actual)
        penalty_misses = player_stats.get('penalties_missed', 0)
        if penalty_misses > 0:
            points += penalty_misses * self.SCORING_RULES['penalty_miss']
        
        # 9. NEW: Defensive Contributions (use actual)
        defensive_contributions = self.calculate_defensive_contributions(player_stats, position)
        points += defensive_contributions
        
        return points

    def calculate_defensive_contributions(self, player_stats, position):
        """Calculate defensive contribution points based on 2024-25 FPL rules"""
        # Get defensive stats
        clearances = player_stats.get('clearances', 0)
        blocks = player_stats.get('blocks', 0)
        interceptions = player_stats.get('interceptions', 0)
        tackles = player_stats.get('tackles_won', 0)  # Using tackles_won as main tackles stat
        
        if position == 'Defender':
            # Defenders: 2 points for 10+ CBIT (clearances, blocks, interceptions, tackles)
            cbit_total = clearances + blocks + interceptions + tackles
            if cbit_total >= 10:
                return self.SCORING_RULES['defensive_contributions']
        else:
            # Midfielders and Forwards: 2 points for 12+ CBIRT (+ recoveries)
            recoveries = player_stats.get('recoveries', 0)
            cbirt_total = clearances + blocks + interceptions + recoveries + tackles
            if cbirt_total >= 12:
                return self.SCORING_RULES['defensive_contributions']
        
        return 0

    def calculate_expected_bonus_points(self, player_bps, match_players_bps):
        """Calculate expected bonus points based on BPS ranking in match"""
        if not match_players_bps or len(match_players_bps) == 0:
            return 0
        
        # Sort players by BPS (descending)
        sorted_bps = sorted(match_players_bps, reverse=True)
        
        # Find player's rank
        try:
            player_rank = sorted_bps.index(player_bps)
        except ValueError:
            return 0
        
        # FPL bonus points system: 3, 2, 1 for top 3 BPS scores
        if player_rank == 0:  # Highest BPS
            return 3
        elif player_rank == 1:  # Second highest
            return 2
        elif player_rank == 2:  # Third highest
            return 1
        else:
            return 0

    def merge_with_playerstats(self, playermatchstats_df, playerstats_df):
        """Merge playermatchstats with playerstats data by gameweek"""
        if playerstats_df.empty:
            print("⚠ No playerstats data available, bonus points analysis will be limited")
            return playermatchstats_df
        
        # Filter playerstats to specific gameweek (GW1 in this case)
        # You can modify this to dynamically detect gameweek from match_id if needed
        target_gameweek = 1
        gw_playerstats = playerstats_df[playerstats_df['gw'] == target_gameweek].copy()
        
        if gw_playerstats.empty:
            print(f"⚠ No playerstats data found for gameweek {target_gameweek}")
            return playermatchstats_df
        
        print(f"✅ Found {len(gw_playerstats)} player records for gameweek {target_gameweek}")
        
        # Remove duplicates from playerstats (keep first occurrence for each player)
        gw_playerstats_unique = gw_playerstats.drop_duplicates(subset=['web_name'], keep='first')
        print(f"✅ After removing duplicates: {len(gw_playerstats_unique)} unique players")
        
        # Merge on web_name for the specific gameweek
        merged_df = playermatchstats_df.merge(
            gw_playerstats_unique[['web_name', 'bonus', 'bps', 'event_points', 'defensive_contribution']],
            on='web_name',
            how='left',
            suffixes=('', '_fpl')
        )
        
        print(f"✅ Merged with gameweek {target_gameweek} playerstats data: {len(merged_df)} records")
        return merged_df

    def analyze_players(self, min_minutes=30):
        """Analyze all players and calculate FPL points"""
        print("🔄 Loading player statistics from database...")
        df = self.load_player_stats()
        
        if df.empty:
            print("❌ No player statistics found in database")
            return None
        
        print(f"✅ Loaded {len(df)} player match records")
        
        # Load playerstats data for bonus points analysis
        print("🔄 Loading FPL playerstats data...")
        playerstats_df = self.load_playerstats_data()
        
        # Merge with playerstats data
        df = self.merge_with_playerstats(df, playerstats_df)
        
        # Filter players who played significant minutes
        df_filtered = df[df['minutes_played'] >= min_minutes].copy()
        
        print(f"📊 Analyzing {len(df_filtered)} records (players with {min_minutes}+ minutes)")
        
        # Calculate points for each record
        results = []
        
        for _, player_stats in df_filtered.iterrows():
            # Calculate base points (excluding bonus) for fair comparison
            actual_base_points = self.calculate_base_fpl_points(player_stats)
            expected_base_points = self.calculate_expected_base_fpl_points(player_stats)
            
            # Calculate total points including bonus
            actual_total_points = self.calculate_actual_fpl_points_with_bonus(player_stats)
            
            defensive_points = self.calculate_defensive_contributions(player_stats, player_stats['position'])
            
            # Get actual bonus points from FPL data
            actual_bonus = player_stats.get('bonus', 0) if pd.notna(player_stats.get('bonus', 0)) else 0
            player_bps = player_stats.get('bps', 0) if pd.notna(player_stats.get('bps', 0)) else 0
            fpl_event_points = player_stats.get('event_points', 0) if pd.notna(player_stats.get('event_points', 0)) else 0
            fpl_defensive_contribution = player_stats.get('defensive_contribution_fpl', 0) if pd.notna(player_stats.get('defensive_contribution_fpl', 0)) else 0
            
            # Calculate defensive contribution totals for display
            clearances = player_stats.get('clearances', 0)
            blocks = player_stats.get('blocks', 0)
            interceptions = player_stats.get('interceptions', 0)
            tackles = player_stats.get('tackles_won', 0)
            recoveries = player_stats.get('recoveries', 0)
            
            results.append({
                'player_name': player_stats['web_name'],
                'position': player_stats['position'],
                'team_code': player_stats['team_code'],
                'match_id': player_stats['match_id'],
                'minutes_played': player_stats['minutes_played'],
                'goals': player_stats['goals'],
                'assists': player_stats['assists'],
                'xg': player_stats['xg'],
                'xa': player_stats['xa'],
                'saves': player_stats.get('saves', 0),
                'team_goals_conceded': player_stats['team_goals_conceded'],
                'clearances': clearances,
                'blocks': blocks,
                'interceptions': interceptions,
                'tackles_won': tackles,
                'recoveries': recoveries,
                'defensive_contributions_points': defensive_points,
                'actual_bonus_points': actual_bonus,
                'bps_score': player_bps,
                'fpl_total_points': fpl_event_points,
                'fpl_defensive_contribution': fpl_defensive_contribution,
                'actual_base_points': actual_base_points,
                'expected_base_points': expected_base_points,
                'actual_total_points': actual_total_points,
                'base_points_difference': actual_base_points - expected_base_points
            })
        
        results_df = pd.DataFrame(results)
        return results_df

    def get_top_performers(self, results_df, metric='actual_total_points', top_n=20):
        """Get top performing players by specified metric"""
        return results_df.nlargest(top_n, metric)

    def get_best_value_players(self, results_df, top_n=20):
        """Get players with highest expected points per 90 minutes"""
        # Calculate per 90 minute stats
        results_df = results_df.copy()
        results_df['actual_base_points_per_90'] = (results_df['actual_base_points'] / results_df['minutes_played']) * 90
        results_df['expected_base_points_per_90'] = (results_df['expected_base_points'] / results_df['minutes_played']) * 90
        
        return results_df.nlargest(top_n, 'expected_base_points_per_90')

    def analyze_by_position(self, results_df):
        """Analyze performance by position"""
        position_analysis = results_df.groupby('position').agg({
            'actual_base_points': ['mean', 'max', 'std'],
            'expected_base_points': ['mean', 'max', 'std'],
            'actual_total_points': ['mean', 'max', 'std'],
            'minutes_played': 'mean',
            'player_name': 'count'
        }).round(2)
        
        position_analysis.columns = ['_'.join(col).strip() for col in position_analysis.columns]
        return position_analysis

    def print_analysis(self, results_df):
        """Print comprehensive analysis"""
        print("\n" + "="*80)
        print("📊 FPL EXPECTED POINTS ANALYSIS")
        print("="*80)
        
        # Overall stats
        total_players = len(results_df)
        avg_actual_base = results_df['actual_base_points'].mean()
        avg_expected_base = results_df['expected_base_points'].mean()
        avg_actual_total = results_df['actual_total_points'].mean()
        avg_bonus = results_df['actual_bonus_points'].mean()
        defensive_contributors = len(results_df[results_df['defensive_contributions_points'] > 0])
        
        print(f"📈 Overall Statistics:")
        print(f"   Total Player Performances: {total_players}")
        print(f"   Average Actual Base Points: {avg_actual_base:.2f}")
        print(f"   Average Expected Base Points: {avg_expected_base:.2f}")
        print(f"   Base Points Difference: {avg_actual_base - avg_expected_base:+.2f}")
        print(f"   Average Total Points (inc. bonus): {avg_actual_total:.2f}")
        print(f"   Average Bonus Points: {avg_bonus:.2f}")
        print(f"   Players with Defensive Contributions: {defensive_contributors}/{total_players}")
        
        # Top actual performers (total points including bonus)
        print(f"\n🏆 Top 10 Total FPL Performances (inc. bonus):")
        top_actual = self.get_top_performers(results_df, 'actual_total_points', 10)
        for _, player in top_actual.iterrows():
            bonus_info = f", Bonus:{player['actual_bonus_points']:.0f}" if player['actual_bonus_points'] > 0 else ""
            print(f"   {player['player_name']:<15} ({player['position']:<10}) - {player['actual_total_points']:4.1f} pts "
                  f"(Base:{player['actual_base_points']:.1f}{bonus_info}, G:{player['goals']}, A:{player['assists']})")
        
        # Top base performers (excluding bonus for fair comparison)
        print(f"\n⚡ Top 10 Base FPL Performances (exc. bonus):")
        top_base = self.get_top_performers(results_df, 'actual_base_points', 10)
        for _, player in top_base.iterrows():
            print(f"   {player['player_name']:<15} ({player['position']:<10}) - {player['actual_base_points']:4.1f} pts "
                  f"(G:{player['goals']}, A:{player['assists']}, {player['minutes_played']}min)")
        
        # Top expected performers  
        print(f"\n⭐ Top 10 Expected Base FPL Performances:")
        top_expected = self.get_top_performers(results_df, 'expected_base_points', 10)
        for _, player in top_expected.iterrows():
            print(f"   {player['player_name']:<15} ({player['position']:<10}) - {player['expected_base_points']:4.1f} xPts "
                  f"(xG:{player['xg']:.2f}, xA:{player['xa']:.2f}, {player['minutes_played']}min)")
        
        # Best value (per 90 mins)
        print(f"\n💎 Top 10 Expected Base Points per 90 Minutes:")
        best_value = self.get_best_value_players(results_df, 10)
        for _, player in best_value.iterrows():
            pts_per_90 = player['expected_base_points_per_90']
            print(f"   {player['player_name']:<15} ({player['position']:<10}) - {pts_per_90:4.1f} xPts/90 "
                  f"({player['minutes_played']}min played)")
        
        # NEW: Top Defensive Contributors (2024-25)
        print(f"\n🛡️  Top Defensive Contributors (2024-25 Feature):")
        defensive_contributors = results_df[results_df['defensive_contributions_points'] > 0]
        if len(defensive_contributors) > 0:
            for _, player in defensive_contributors.iterrows():
                if player['position'] == 'Defender':
                    cbit_total = player['clearances'] + player['blocks'] + player['interceptions'] + player['tackles_won']
                    print(f"   {player['player_name']:<15} ({player['position']:<10}) - {player['defensive_contributions_points']} pts "
                          f"(CBIT: {cbit_total:.0f}) - C:{player['clearances']}, B:{player['blocks']}, I:{player['interceptions']}, T:{player['tackles_won']}")
                else:
                    cbirt_total = player['clearances'] + player['blocks'] + player['interceptions'] + player['recoveries'] + player['tackles_won']
                    print(f"   {player['player_name']:<15} ({player['position']:<10}) - {player['defensive_contributions_points']} pts "
                          f"(CBIRT: {cbirt_total:.0f}) - C:{player['clearances']}, B:{player['blocks']}, I:{player['interceptions']}, R:{player['recoveries']}, T:{player['tackles_won']}")
        else:
            print("   No players reached defensive contribution thresholds in this dataset")
        
        # NEW: Bonus Points Analysis
        print(f"\n🏅 Bonus Points Analysis:")
        bonus_earners = results_df[results_df['actual_bonus_points'] > 0]
        if len(bonus_earners) > 0:
            print("   Players who earned bonus points:")
            for _, player in bonus_earners.iterrows():
                comparison = ""
                if player['fpl_total_points'] > 0:
                    comparison = f"(FPL Total: {player['fpl_total_points']:.0f})"
                print(f"   {player['player_name']:<15} ({player['position']:<10}) - "
                      f"Bonus: {player['actual_bonus_points']:.0f}, BPS: {player['bps_score']:.0f} {comparison}")
            
            # Top BPS performers
            top_bps = results_df.nlargest(5, 'bps_score')
            print(f"\n   Top 5 BPS Performers:")
            for _, player in top_bps.iterrows():
                print(f"   {player['player_name']:<15} ({player['position']:<10}) - "
                      f"BPS: {player['bps_score']:.0f}, Bonus: {player['actual_bonus_points']:.0f}")
        else:
            print("   No bonus points data available in current dataset")
        
        # Position analysis
        print(f"\n📊 Analysis by Position:")
        position_stats = self.analyze_by_position(results_df)
        print(position_stats)
        
        # Players outperforming xG/xA (fair comparison using base points)
        print(f"\n🔥 Players Outperforming Expected Base Points (Actual > Expected):")
        overperformers = results_df[results_df['base_points_difference'] > 0.5].nlargest(10, 'actual_base_points')
        for _, player in overperformers.iterrows():
            print(f"   {player['player_name']:<15} ({player['position']:<10}) - "
                  f"Actual: {player['actual_base_points']:4.1f}, Expected: {player['expected_base_points']:4.1f} "
                  f"(+{player['base_points_difference']:.1f})")
        
        # Players underperforming xG/xA (fair comparison using base points)
        print(f"\n⚡ Players with Highest Expected Base Points (Unlucky?):")
        underperformers = results_df[results_df['base_points_difference'] < -0.5].nlargest(10, 'expected_base_points')
        for _, player in underperformers.iterrows():
            print(f"   {player['player_name']:<15} ({player['position']:<10}) - "
                  f"Expected: {player['expected_base_points']:4.1f}, Actual: {player['actual_base_points']:4.1f} "
                  f"({player['base_points_difference']:+.1f})")

    def export_to_csv(self, results_df, filename=None):
        """Export results to CSV"""
        if filename is None:
            filename = f"fpl_expected_points_analysis.csv"
        
        # Create analysis directory if it doesn't exist
        analysis_dir = Path(__file__).parent
        filepath = analysis_dir / filename
        
        results_df.to_csv(filepath, index=False)
        print(f"\n💾 Analysis exported to: {filepath}")

def main():
    """Main execution function"""
    print("🚀 FPL Expected Points Calculator")
    print("="*50)
    
    calculator = FPLExpectedPointsCalculator()
    
    try:
        # Analyze all players
        results = calculator.analyze_players(min_minutes=30)
        
        if results is not None:
            # Print analysis
            calculator.print_analysis(results)
            
            # Export to CSV
            calculator.export_to_csv(results)
            
            print(f"\n✅ Analysis complete!")
            print(f"💡 Use this data to identify:")
            print(f"   • High expected points players for transfers")
            print(f"   • Players outperforming their underlying stats")
            print(f"   • Value picks based on minutes played")
            print(f"   • Position-specific point scoring patterns")
            print(f"   • 🆕 Defensive contributors earning bonus points (2024-25 feature)")
            print(f"   • 🆕 Centre-backs and defensive midfielders with high CBIT/CBIRT stats")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()