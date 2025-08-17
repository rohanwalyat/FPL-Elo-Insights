#!/usr/bin/env python3
"""
Helper script to set up Metabase authentication in .env file
"""

import os
import re
from pathlib import Path
import requests

def test_metabase_connection(url="http://localhost:3000"):
    """Test if Metabase is running"""
    try:
        response = requests.get(f"{url}/api/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_metabase_credentials(url, email, password):
    """Test Metabase credentials"""
    try:
        login_data = {
            "username": email,
            "password": password
        }
        response = requests.post(f"{url}/api/session", json=login_data, timeout=10)
        return response.status_code == 200
    except:
        return False

def setup_metabase_auth():
    """Setup Metabase authentication in .env file"""
    
    # Get the repository root directory
    script_dir = Path(__file__).parent
    repo_dir = script_dir.parent
    env_file = repo_dir / ".env"
    
    print("📊 Metabase Authentication Setup")
    print("=" * 40)
    
    # Check if .env file exists
    if not env_file.exists():
        print("❌ .env file not found!")
        print(f"Expected location: {env_file}")
        return False
    
    # Test Metabase connection first
    print("🔍 Checking if Metabase is running...")
    if test_metabase_connection():
        print("✅ Metabase is running at http://localhost:3000")
    else:
        print("⚠️  Metabase is not running or not accessible")
        print("💡 Start Metabase with: metabase")
        print("   Or check if it's running on a different port")
        
        custom_url = input("Enter Metabase URL (press Enter for http://localhost:3000): ").strip()
        if custom_url:
            if test_metabase_connection(custom_url):
                print(f"✅ Metabase found at {custom_url}")
                metabase_url = custom_url
            else:
                print(f"❌ Cannot connect to {custom_url}")
                print("Please start Metabase and run this script again")
                return False
        else:
            print("Continuing with default URL. You can update it later.")
            metabase_url = "http://localhost:3000"
    else:
        metabase_url = "http://localhost:3000"
    
    # Get current values from .env
    env_content = env_file.read_text()
    current_email = None
    current_password = None
    current_url = None
    
    # Look for existing values
    for pattern, var_name in [
        (r'^METABASE_ADMIN_EMAIL=(.*)$', 'email'),
        (r'^METABASE_ADMIN_PASSWORD=(.*)$', 'password'), 
        (r'^METABASE_URL=(.*)$', 'url')
    ]:
        match = re.search(pattern, env_content, re.MULTILINE)
        if match:
            value = match.group(1).strip()
            if var_name == 'email' and value != 'your_admin_email@example.com':
                current_email = value
            elif var_name == 'password' and value != 'your_admin_password':
                current_password = value
            elif var_name == 'url':
                current_url = value
    
    if current_email and current_password:
        print(f"📧 Current admin email: {current_email}")
        print("🔑 Admin password is configured")
        
        # Test existing credentials
        print("🧪 Testing existing credentials...")
        if test_metabase_credentials(current_url or metabase_url, current_email, current_password):
            print("✅ Existing credentials work!")
            update = input("Do you want to update them? (y/N): ").strip().lower()
            if update != 'y':
                print("✅ Keeping existing Metabase credentials")
                return True
        else:
            print("❌ Existing credentials don't work")
            print("Let's update them...")
    
    print("\n📝 Metabase Admin Setup:")
    print("   You need admin credentials to enable automatic database resync")
    print("   If you don't have admin access, automation will provide manual instructions")
    print()
    
    # Get admin email
    while True:
        email = input("Enter Metabase admin email (or press Enter to skip): ").strip()
        
        if not email:
            print("⚠️  Skipping Metabase authentication setup")
            print("💡 You can add credentials later by running this script again")
            return update_env_file(env_file, env_content, metabase_url, None, None)
        
        if '@' not in email:
            print("❌ Please enter a valid email address!")
            continue
        
        break
    
    # Get admin password
    import getpass
    try:
        password = getpass.getpass("Enter Metabase admin password: ")
    except KeyboardInterrupt:
        print("\n⚠️  Setup cancelled")
        return False
    
    if not password:
        print("❌ Password cannot be empty!")
        return False
    
    # Test credentials
    print("🧪 Testing credentials...")
    if test_metabase_connection(metabase_url):
        if test_metabase_credentials(metabase_url, email, password):
            print("✅ Credentials verified successfully!")
        else:
            print("❌ Authentication failed!")
            print("Please check your email and password")
            retry = input("Try again? (y/N): ").strip().lower()
            if retry == 'y':
                return setup_metabase_auth()  # Recursive retry
            else:
                return False
    else:
        print("⚠️  Cannot test credentials (Metabase not accessible)")
        print("Credentials will be saved but not verified")
    
    # Update .env file
    return update_env_file(env_file, env_content, metabase_url, email, password)

def update_env_file(env_file, env_content, metabase_url, email, password):
    """Update .env file with Metabase configuration"""
    try:
        # Update or add Metabase configuration
        new_content = env_content
        
        # Update URL
        if re.search(r'^METABASE_URL=', new_content, re.MULTILINE):
            new_content = re.sub(r'^METABASE_URL=.*$', f'METABASE_URL={metabase_url}', new_content, flags=re.MULTILINE)
        else:
            if not new_content.endswith('\n'):
                new_content += '\n'
            new_content += f'\n# Metabase Configuration\nMETABASE_URL={metabase_url}\n'
        
        # Update email
        if email:
            if re.search(r'^METABASE_ADMIN_EMAIL=', new_content, re.MULTILINE):
                new_content = re.sub(r'^METABASE_ADMIN_EMAIL=.*$', f'METABASE_ADMIN_EMAIL={email}', new_content, flags=re.MULTILINE)
            else:
                new_content += f'METABASE_ADMIN_EMAIL={email}\n'
        
        # Update password
        if password:
            if re.search(r'^METABASE_ADMIN_PASSWORD=', new_content, re.MULTILINE):
                new_content = re.sub(r'^METABASE_ADMIN_PASSWORD=.*$', f'METABASE_ADMIN_PASSWORD={password}', new_content, flags=re.MULTILINE)
            else:
                new_content += f'METABASE_ADMIN_PASSWORD={password}\n'
        
        # Write back to file
        env_file.write_text(new_content)
        
        print(f"\n✅ Successfully updated .env file!")
        print(f"📊 Metabase URL: {metabase_url}")
        if email:
            print(f"📧 Admin Email: {email}")
            print("🔑 Admin Password: [CONFIGURED]")
        print(f"📁 File location: {env_file}")
        
        print("\n💡 Automation will now be able to:")
        print("   • Automatically resync Metabase after database updates")
        print("   • Refresh dashboard data without manual intervention")
        print("   • Trigger schema updates when new tables are added")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False

def main():
    try:
        success = setup_metabase_auth()
        if not success:
            exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Setup cancelled by user")
        exit(1)

if __name__ == "__main__":
    main()