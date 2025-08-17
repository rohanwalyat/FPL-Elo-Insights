#!/usr/bin/env python3
"""
Helper script to set up Draft League ID in .env file
"""

import os
import re
from pathlib import Path

def setup_draft_league_id():
    """Setup DRAFT_LEAGUE_ID in .env file"""
    
    # Get the repository root directory
    script_dir = Path(__file__).parent
    repo_dir = script_dir.parent
    env_file = repo_dir / ".env"
    
    print("🏆 FPL Draft League Setup")
    print("=" * 40)
    
    # Check if .env file exists
    if not env_file.exists():
        print("❌ .env file not found!")
        print(f"Expected location: {env_file}")
        return False
    
    # Get current DRAFT_LEAGUE_ID if any
    current_id = None
    env_content = env_file.read_text()
    
    # Look for existing DRAFT_LEAGUE_ID
    match = re.search(r'^DRAFT_LEAGUE_ID=(.*)$', env_content, re.MULTILINE)
    if match:
        current_id = match.group(1).strip()
        if current_id and current_id != 'YOUR_LEAGUE_ID_HERE':
            print(f"📊 Current Draft League ID: {current_id}")
            update = input("Do you want to update it? (y/N): ").strip().lower()
            if update != 'y':
                print("✅ Keeping existing Draft League ID")
                return True
    
    # Get new league ID from user
    print("\n📝 To find your Draft League ID:")
    print("   1. Go to https://draft.premierleague.com")
    print("   2. Navigate to your league")
    print("   3. Look at the URL: https://draft.premierleague.com/leagues/YOUR_ID/status")
    print("   4. Copy the number from the URL")
    print()
    
    while True:
        league_id = input("Enter your FPL Draft League ID: ").strip()
        
        if not league_id:
            print("❌ League ID cannot be empty!")
            continue
        
        # Basic validation - should be a number
        if not league_id.isdigit():
            print("❌ League ID should be a number!")
            continue
        
        # Confirm the ID
        print(f"\n🔍 You entered: {league_id}")
        confirm = input("Is this correct? (Y/n): ").strip().lower()
        if confirm in ['', 'y', 'yes']:
            break
        print("Let's try again...\n")
    
    # Update .env file
    try:
        if match:
            # Replace existing DRAFT_LEAGUE_ID line
            new_content = re.sub(
                r'^DRAFT_LEAGUE_ID=.*$',
                f'DRAFT_LEAGUE_ID={league_id}',
                env_content,
                flags=re.MULTILINE
            )
        else:
            # Add new DRAFT_LEAGUE_ID line
            if not env_content.endswith('\n'):
                env_content += '\n'
            new_content = env_content + f'\n# FPL Draft League Configuration\nDRAFT_LEAGUE_ID={league_id}\n'
        
        # Write back to file
        env_file.write_text(new_content)
        
        print(f"\n✅ Successfully updated .env file!")
        print(f"📊 Draft League ID set to: {league_id}")
        print(f"📁 File location: {env_file}")
        
        # Test the configuration
        print("\n🧪 Testing configuration...")
        os.environ['DRAFT_LEAGUE_ID'] = league_id
        
        test_script = script_dir / "simple_draft_fetch.py"
        if test_script.exists():
            print("✅ Draft fetch script found")
            print("\n💡 You can now run automated draft league updates!")
            print("   • Manual update: python scripts/simple_draft_fetch.py")
            print("   • Full automation: python automation/full_update_automation.py")
            print("   • Scheduled updates: ./automation/install_cron_jobs.sh")
        else:
            print("⚠️  Draft fetch script not found, but .env is configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False

def main():
    success = setup_draft_league_id()
    if not success:
        exit(1)

if __name__ == "__main__":
    main()