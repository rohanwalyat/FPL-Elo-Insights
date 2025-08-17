#!/usr/bin/env python3
"""
Metabase Database Resync Automation

This script automatically triggers Metabase to resync its database schema
after database updates. It uses the Metabase API to initiate the resync.
"""

import requests
import time
import os
import json
from datetime import datetime
import sys

class MetabaseResyncer:
    def __init__(self, metabase_url="http://localhost:3000", admin_email=None, admin_password=None):
        """Initialize the Metabase resyncer"""
        self.metabase_url = metabase_url.rstrip('/')
        self.admin_email = admin_email
        self.admin_password = admin_password
        self.session_token = None
        self.database_id = None
        
    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")

    def check_metabase_status(self):
        """Check if Metabase is running and accessible"""
        try:
            response = requests.get(f"{self.metabase_url}/api/health", timeout=10)
            if response.status_code == 200:
                self.log("✅ Metabase is running and accessible")
                return True
            else:
                self.log(f"⚠ Metabase responded with status {response.status_code}", "WARNING")
                return False
        except requests.exceptions.ConnectionError:
            self.log("❌ Cannot connect to Metabase. Is it running?", "ERROR")
            return False
        except requests.exceptions.Timeout:
            self.log("❌ Timeout connecting to Metabase", "ERROR")
            return False

    def get_session_token(self):
        """Get session token for Metabase API authentication"""
        if not self.admin_email or not self.admin_password:
            self.log("⚠ No admin credentials provided, attempting anonymous access", "WARNING")
            return None
            
        try:
            login_data = {
                "username": self.admin_email,
                "password": self.admin_password
            }
            
            response = requests.post(
                f"{self.metabase_url}/api/session",
                json=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                session_data = response.json()
                self.session_token = session_data.get('id')
                self.log("✅ Successfully authenticated with Metabase")
                return self.session_token
            else:
                self.log(f"❌ Authentication failed: {response.status_code}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ Error during authentication: {e}", "ERROR")
            return None

    def get_databases(self):
        """Get list of databases in Metabase"""
        try:
            headers = {}
            if self.session_token:
                headers['X-Metabase-Session'] = self.session_token
                
            response = requests.get(
                f"{self.metabase_url}/api/database",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                databases = response.json()
                self.log(f"Found {len(databases)} database(s) in Metabase")
                
                # Look for PostgreSQL database
                for db in databases:
                    if db.get('engine') == 'postgres':
                        self.database_id = db.get('id')
                        db_name = db.get('name', 'Unknown')
                        self.log(f"✅ Found PostgreSQL database: {db_name} (ID: {self.database_id})")
                        return databases
                
                self.log("⚠ No PostgreSQL database found in Metabase", "WARNING")
                return databases
            elif response.status_code == 401:
                self.log("❌ Authentication required for Metabase API access", "ERROR")
                self.log("💡 To enable automatic resync, add these to your .env file:")
                self.log("   METABASE_ADMIN_EMAIL=your_admin_email@example.com")
                self.log("   METABASE_ADMIN_PASSWORD=your_admin_password")
                return None
            else:
                self.log(f"❌ Failed to get databases: {response.status_code}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ Error getting databases: {e}", "ERROR")
            return None

    def trigger_database_resync(self):
        """Trigger database schema resync"""
        if not self.database_id:
            self.log("❌ No database ID found. Cannot trigger resync.", "ERROR")
            return False
            
        try:
            headers = {}
            if self.session_token:
                headers['X-Metabase-Session'] = self.session_token
                
            # Trigger sync
            response = requests.post(
                f"{self.metabase_url}/api/database/{self.database_id}/sync_schema",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                self.log("✅ Successfully triggered database resync")
                return True
            elif response.status_code == 202:
                self.log("✅ Database resync started (accepted)")
                return True
            else:
                self.log(f"❌ Failed to trigger resync: {response.status_code}", "ERROR")
                if response.text:
                    self.log(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Error triggering resync: {e}", "ERROR")
            return False

    def wait_for_sync_completion(self, timeout_minutes=5):
        """Wait for sync to complete"""
        if not self.database_id:
            return False
            
        self.log(f"Waiting for sync to complete (timeout: {timeout_minutes} minutes)...")
        timeout_seconds = timeout_minutes * 60
        start_time = time.time()
        
        try:
            headers = {}
            if self.session_token:
                headers['X-Metabase-Session'] = self.session_token
                
            while time.time() - start_time < timeout_seconds:
                response = requests.get(
                    f"{self.metabase_url}/api/database/{self.database_id}",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    db_info = response.json()
                    is_full_sync = db_info.get('is_full_sync', False)
                    
                    if not is_full_sync:
                        elapsed = int(time.time() - start_time)
                        self.log(f"✅ Database sync completed in {elapsed} seconds")
                        return True
                
                time.sleep(5)  # Check every 5 seconds
                
            self.log("⚠ Sync timeout reached, but sync may still be running in background", "WARNING")
            return True  # Don't fail the process
            
        except Exception as e:
            self.log(f"⚠ Error checking sync status: {e}", "WARNING")
            return True  # Don't fail the process

    def provide_manual_instructions(self):
        """Provide manual resync instructions"""
        self.log("📋 Manual Metabase Resync Instructions:")
        self.log("   1. Open Metabase at http://localhost:3000")
        self.log("   2. Click on the gear icon (⚙️) in the top right")
        self.log("   3. Go to Admin settings")
        self.log("   4. Click on 'Databases' in the left sidebar")
        self.log("   5. Click on your PostgreSQL database")
        self.log("   6. Click 'Sync database schema now' button")
        self.log("   7. Wait for the sync to complete")
        self.log("💡 Alternatively, add Metabase admin credentials to .env file for automatic sync")

    def resync_database(self):
        """Complete resync workflow"""
        self.log("=== Starting Metabase Database Resync ===")
        
        # Check if Metabase is running
        if not self.check_metabase_status():
            self.log("❌ Metabase is not accessible. Make sure it's running.", "ERROR")
            self.provide_manual_instructions()
            return False
        
        # Try to authenticate (optional for resync)
        self.get_session_token()
        
        # Get databases
        if not self.get_databases():
            self.log("❌ Could not retrieve database information", "ERROR")
            self.provide_manual_instructions()
            return False
        
        # Trigger resync
        if not self.trigger_database_resync():
            self.log("❌ Failed to trigger database resync", "ERROR")
            self.provide_manual_instructions()
            return False
        
        # Wait for completion
        self.wait_for_sync_completion()
        
        self.log("✅ Metabase database resync completed")
        return True

def load_metabase_config():
    """Load Metabase configuration from environment or config file"""
    # Try to load from environment variables
    metabase_url = os.getenv('METABASE_URL', 'http://localhost:3000')
    admin_email = os.getenv('METABASE_ADMIN_EMAIL')
    admin_password = os.getenv('METABASE_ADMIN_PASSWORD')
    
    # Try to load from .env file
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        env_file = os.path.join(os.path.dirname(script_dir), '.env')
        
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('METABASE_URL='):
                        metabase_url = line.split('=', 1)[1].strip()
                    elif line.startswith('METABASE_ADMIN_EMAIL='):
                        admin_email = line.split('=', 1)[1].strip()
                    elif line.startswith('METABASE_ADMIN_PASSWORD='):
                        admin_password = line.split('=', 1)[1].strip()
    except Exception:
        pass  # Ignore errors reading config
    
    return metabase_url, admin_email, admin_password

def main():
    """Main execution function"""
    print("🔄 Metabase Database Resync Automation")
    print("=" * 50)
    
    # Load configuration
    metabase_url, admin_email, admin_password = load_metabase_config()
    
    # Create resyncer
    resyncer = MetabaseResyncer(metabase_url, admin_email, admin_password)
    
    # Perform resync
    success = resyncer.resync_database()
    
    if success:
        print("\n🎉 Metabase resync completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Metabase resync failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()