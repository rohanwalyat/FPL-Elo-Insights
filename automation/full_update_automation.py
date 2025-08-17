#!/usr/bin/env python3
"""
Complete FPL Data Update Automation

This script handles the complete end-to-end workflow:
1. Check GitHub fork for updates
2. Pull latest data from fork
3. Update draft league data from FPL API
4. Ingest all updated data into PostgreSQL database
5. Provide comprehensive logging and error handling

This is the master automation script that orchestrates everything.
"""

import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

class FullUpdateAutomation:
    def __init__(self):
        """Initialize the automation system"""
        # Load environment variables
        load_dotenv()
        
        # Set up paths
        self.script_dir = Path(__file__).parent
        self.repo_path = self.script_dir.parent
        self.log_dir = self.repo_path / "logs"
        
        # Ensure log directory exists
        self.log_dir.mkdir(exist_ok=True)
        
        # Track what was updated
        self.update_summary = {
            'github_updated': False,
            'draft_updated': False,
            'database_updated': False,
            'errors': [],
            'start_time': datetime.now(),
            'steps_completed': []
        }

    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {level}: {message}"
        print(log_message)
        
        # Also write to log file
        log_file = self.log_dir / "full_update_automation.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')

    def run_command(self, command, description, cwd=None, capture_output=True):
        """Run a command with proper logging"""
        self.log(f"Running: {description}")
        self.log(f"Command: {command}")
        
        try:
            if capture_output:
                result = subprocess.run(
                    command, shell=True, capture_output=True, 
                    text=True, cwd=cwd or self.repo_path
                )
                
                if result.returncode == 0:
                    self.log(f"✅ {description} completed successfully")
                    if result.stdout.strip():
                        self.log(f"Output: {result.stdout.strip()}")
                    return True, result.stdout
                else:
                    self.log(f"❌ {description} failed", "ERROR")
                    self.log(f"Error: {result.stderr.strip()}", "ERROR")
                    return False, result.stderr
            else:
                # For commands that need real-time output
                result = subprocess.run(
                    command, shell=True, cwd=cwd or self.repo_path
                )
                return result.returncode == 0, ""
                
        except Exception as e:
            self.log(f"❌ Exception running {description}: {e}", "ERROR")
            return False, str(e)

    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        self.log("=== Checking Prerequisites ===")
        
        # Check if we're in a git repository
        if not (self.repo_path / ".git").exists():
            self.log("❌ Not in a git repository", "ERROR")
            return False
        
        # Check database connection
        success, _ = self.run_command(
            f'source .env && PGPASSWORD="$PGPASSWORD" psql -U postgres -d fpl_elo -c "SELECT 1;" > /dev/null',
            "Testing database connection"
        )
        if not success:
            self.log("❌ Database connection failed", "ERROR")
            return False
        
        # Check if virtual environment exists
        venv_path = self.repo_path / "fpl-venv"
        if not venv_path.exists():
            self.log("⚠ Virtual environment not found, will use system Python", "WARNING")
        
        self.log("✅ All prerequisites check passed")
        return True

    def check_for_github_updates(self):
        """Check if there are updates available from GitHub upstream fork"""
        self.log("=== Checking for GitHub Updates from Upstream Fork ===")
        
        # Fetch latest from upstream fork
        success, _ = self.run_command(
            "git fetch upstream",
            "Fetching latest changes from upstream fork"
        )
        if not success:
            self.log("❌ Failed to fetch from upstream fork", "ERROR")
            return False
        
        # Check if local main is behind upstream main
        success, output = self.run_command(
            "git log HEAD..upstream/main --oneline",
            "Checking for new commits in upstream"
        )
        
        if success and output.strip():
            self.log("📦 Updates available from upstream fork")
            self.log(f"New commits found:\n{output.strip()}")
            return True
        elif success:
            self.log("✅ Repository is up to date with upstream")
            return False
        else:
            self.log("⚠ Unable to determine update status", "WARNING")
            return False

    def pull_github_updates(self):
        """Pull latest updates from GitHub upstream fork"""
        self.log("=== Pulling GitHub Updates from Upstream ===")
        
        # Check for local changes and stash if needed
        success, status = self.run_command(
            "git status --porcelain",
            "Checking for local changes"
        )
        
        if success and status.strip():
            self.log("📦 Local changes detected, stashing...")
            success, _ = self.run_command(
                "git stash",
                "Stashing local changes"
            )
            if not success:
                self.log("❌ Failed to stash changes", "ERROR")
                return False
        
        # Merge latest changes from upstream
        success, output = self.run_command(
            "git merge upstream/main",
            "Merging latest changes from upstream main branch"
        )
        
        if not success:
            # Try master branch
            success, output = self.run_command(
                "git merge upstream/master",
                "Merging latest changes from upstream master branch"
            )
        
        if success:
            self.log("✅ Successfully merged latest changes from upstream")
            self.update_summary['github_updated'] = True
            self.update_summary['steps_completed'].append('Upstream Update')
            return True
        else:
            self.log("❌ Failed to merge upstream updates", "ERROR")
            self.update_summary['errors'].append('Upstream merge failed')
            return False

    def update_draft_league_data(self):
        """Update draft league data from FPL API"""
        self.log("=== Updating Draft League Data ===")
        
        # Check if draft fetch script exists
        draft_script = self.repo_path / "scripts" / "simple_draft_fetch.py"
        if not draft_script.exists():
            self.log("⚠ Draft league fetch script not found, skipping", "WARNING")
            return True
        
        # Run draft league data fetch
        venv_path = self.repo_path / "fpl-venv"
        if venv_path.exists():
            command = f"source fpl-venv/bin/activate && python scripts/simple_draft_fetch.py"
        else:
            command = "python3 scripts/simple_draft_fetch.py"
        
        success, output = self.run_command(
            command,
            "Fetching latest draft league data from FPL API",
            capture_output=False
        )
        
        if success:
            self.log("✅ Successfully updated draft league data")
            self.update_summary['draft_updated'] = True
            self.update_summary['steps_completed'].append('Draft League Update')
            return True
        else:
            self.log("❌ Failed to update draft league data", "ERROR")
            self.update_summary['errors'].append('Draft league update failed')
            # Don't fail the entire process for draft league issues
            return True

    def update_database(self):
        """Update database with latest data"""
        self.log("=== Updating Database ===")
        
        # Check if database ingestion script exists
        db_script = self.script_dir / "database_ingestion.py"
        if not db_script.exists():
            self.log("❌ Database ingestion script not found", "ERROR")
            return False
        
        # Run database ingestion
        venv_path = self.repo_path / "fpl-venv"
        if venv_path.exists():
            command = f"source fpl-venv/bin/activate && python automation/database_ingestion.py"
        else:
            command = "python3 automation/database_ingestion.py"
        
        success, output = self.run_command(
            command,
            "Ingesting data into PostgreSQL database",
            capture_output=False
        )
        
        if success:
            self.log("✅ Successfully updated database")
            self.update_summary['database_updated'] = True
            self.update_summary['steps_completed'].append('Database Update')
            return True
        else:
            self.log("❌ Failed to update database", "ERROR")
            self.update_summary['errors'].append('Database update failed')
            return False

    def get_database_summary(self):
        """Get a summary of current database state"""
        self.log("=== Database Summary ===")
        
        success, output = self.run_command(
            '''source .env && PGPASSWORD="$PGPASSWORD" psql -U postgres -d fpl_elo -c "
            SELECT 'Teams' as table_name, COUNT(*) as count FROM teams
            UNION ALL
            SELECT 'Players', COUNT(*) FROM players  
            UNION ALL
            SELECT 'Matches', COUNT(*) FROM matches
            UNION ALL
            SELECT 'Player Stats', COUNT(*) FROM playermatchstats
            UNION ALL
            SELECT 'Draft Managers', COUNT(*) FROM draft_managers
            UNION ALL
            SELECT 'Draft Picks', COUNT(*) FROM draft_picks;"''',
            "Getting database summary"
        )
        
        if success:
            self.log("📊 Current Database State:")
            for line in output.strip().split('\n')[2:-1]:  # Skip header and footer
                self.log(f"   {line.strip()}")
        else:
            self.log("⚠ Could not retrieve database summary", "WARNING")

    def resync_metabase(self):
        """Trigger Metabase database resync"""
        self.log("=== Resyncing Metabase ===")
        
        # Check if Metabase resync script exists
        metabase_script = self.repo_path / "scripts" / "metabase_resync.sh"
        if not metabase_script.exists():
            self.log("⚠ Metabase resync script not found, skipping", "WARNING")
            return True
        
        # Run Metabase resync
        success, output = self.run_command(
            "./scripts/metabase_resync.sh",
            "Triggering Metabase database resync",
            capture_output=False
        )
        
        if success:
            self.log("✅ Successfully triggered Metabase resync")
            self.update_summary['steps_completed'].append('Metabase Resync')
            return True
        else:
            self.log("❌ Failed to resync Metabase", "ERROR")
            self.update_summary['errors'].append('Metabase resync failed')
            # Don't fail the entire process for Metabase issues
            return True

    def print_final_summary(self):
        """Print final summary of the automation run"""
        end_time = datetime.now()
        duration = end_time - self.update_summary['start_time']
        
        self.log("=" * 60)
        self.log("🏁 FULL UPDATE AUTOMATION SUMMARY")
        self.log("=" * 60)
        
        # Time information
        self.log(f"⏱️  Start Time: {self.update_summary['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"⏱️  End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"⏱️  Duration: {duration}")
        
        # Steps completed
        if self.update_summary['steps_completed']:
            self.log("✅ Steps Completed:")
            for step in self.update_summary['steps_completed']:
                self.log(f"   • {step}")
        
        # Update status
        self.log(f"📦 GitHub Updated: {'Yes' if self.update_summary['github_updated'] else 'No'}")
        self.log(f"🏆 Draft League Updated: {'Yes' if self.update_summary['draft_updated'] else 'No'}")
        self.log(f"🗄️  Database Updated: {'Yes' if self.update_summary['database_updated'] else 'No'}")
        
        # Metabase status
        metabase_updated = 'Metabase Resync' in self.update_summary['steps_completed']
        self.log(f"📊 Metabase Resynced: {'Yes' if metabase_updated else 'No'}")
        if metabase_updated:
            self.log("🌐 Metabase URL: http://localhost:3000")
        
        # Errors
        if self.update_summary['errors']:
            self.log("❌ Errors Encountered:")
            for error in self.update_summary['errors']:
                self.log(f"   • {error}")
        
        # Overall status
        if self.update_summary['database_updated']:
            self.log("🎉 AUTOMATION COMPLETED SUCCESSFULLY!")
        elif self.update_summary['errors']:
            self.log("⚠️  AUTOMATION COMPLETED WITH ERRORS")
        else:
            self.log("ℹ️  NO UPDATES WERE NEEDED")
        
        self.log("=" * 60)

    def run_full_automation(self):
        """Run the complete automation workflow"""
        self.log("🚀 Starting Full FPL Data Update Automation")
        self.log("=" * 60)
        
        try:
            # Step 1: Check prerequisites
            if not self.check_prerequisites():
                self.log("❌ Prerequisites check failed, exiting", "ERROR")
                return False
            
            # Step 2: Check for GitHub updates
            updates_available = self.check_for_github_updates()
            
            # Step 3: Pull GitHub updates if available
            if updates_available:
                if not self.pull_github_updates():
                    self.log("❌ GitHub update failed, stopping automation", "ERROR")
                    return False
            else:
                self.log("ℹ️  No GitHub updates available, continuing with existing data")
            
            # Step 4: Update draft league data (always try to get latest)
            self.update_draft_league_data()
            
            # Step 5: Update database (only if we have updates or this is first run)
            if updates_available or self.update_summary['draft_updated']:
                if not self.update_database():
                    self.log("❌ Database update failed", "ERROR")
                    return False
            else:
                # Check if database is empty and needs initial load
                success, output = self.run_command(
                    '''source .env && PGPASSWORD="$PGPASSWORD" psql -U postgres -d fpl_elo -c "SELECT COUNT(*) FROM players;"''',
                    "Checking if database needs initial load"
                )
                
                if success and "0" in output:
                    self.log("📊 Database is empty, performing initial load")
                    if not self.update_database():
                        self.log("❌ Initial database load failed", "ERROR")
                        return False
                else:
                    self.log("ℹ️  Database is up to date, no update needed")
            
            # Step 6: Get database summary
            self.get_database_summary()
            
            # Step 7: Resync Metabase (if database was updated)
            if self.update_summary['database_updated']:
                self.resync_metabase()
            
            return True
            
        except Exception as e:
            self.log(f"❌ Unexpected error in automation: {e}", "ERROR")
            self.update_summary['errors'].append(f'Unexpected error: {e}')
            return False
        
        finally:
            # Always print summary
            self.print_final_summary()

def main():
    """Main execution function"""
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    automation = FullUpdateAutomation()
    success = automation.run_full_automation()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()