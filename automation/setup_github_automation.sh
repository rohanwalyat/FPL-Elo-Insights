#!/bin/bash

# Setup script for GitHub-based FPL data update automation

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATE_SCRIPT="$SCRIPT_DIR/run_github_update.sh"

echo "=== GitHub-based FPL Data Update Automation Setup ==="
echo ""

# Check if the update script exists
if [ ! -f "$UPDATE_SCRIPT" ]; then
    echo "ERROR: Update script not found at $UPDATE_SCRIPT"
    exit 1
fi

echo "This will set up automatic updates from your GitHub repository."
echo "The script will:"
echo "• Check for updates in your FPL-Elo-Insights repo"
echo "• Pull latest data when available"
echo "• Update your PostgreSQL database"
echo ""

echo "Available scheduling options:"
echo "1. Every 2 hours (good for active periods)"
echo "2. Every 6 hours"
echo "3. Once daily at 8 AM"
echo "4. Once daily at 6 PM"  
echo "5. Custom schedule"
echo "6. View current cron jobs"
echo "7. Remove GitHub update cron job"
echo ""

read -p "Select an option (1-7): " choice

case $choice in
    1)
        # Every 2 hours
        cron_entry="0 */2 * * * '$UPDATE_SCRIPT' >/dev/null 2>&1"
        echo "Setting up cron job to run every 2 hours..."
        ;;
    2)
        # Every 6 hours
        cron_entry="0 */6 * * * '$UPDATE_SCRIPT' >/dev/null 2>&1"
        echo "Setting up cron job to run every 6 hours..."
        ;;
    3)
        # Daily at 8 AM
        cron_entry="0 8 * * * '$UPDATE_SCRIPT' >/dev/null 2>&1"
        echo "Setting up cron job to run daily at 8 AM..."
        ;;
    4)
        # Daily at 6 PM
        cron_entry="0 18 * * * '$UPDATE_SCRIPT' >/dev/null 2>&1"
        echo "Setting up cron job to run daily at 6 PM..."
        ;;
    5)
        echo "Enter custom cron schedule (e.g., '0 */3 * * *' for every 3 hours):"
        read -p "Cron schedule: " custom_schedule
        cron_entry="$custom_schedule '$UPDATE_SCRIPT' >/dev/null 2>&1"
        echo "Setting up custom cron job..."
        ;;
    6)
        echo "Current cron jobs:"
        crontab -l | grep -E "(github|FPL|fpl)" || echo "No FPL-related cron jobs found"
        exit 0
        ;;
    7)
        echo "Removing GitHub update cron jobs..."
        (crontab -l | grep -v -E "(github_update|run_github_update)") | crontab -
        echo "GitHub update cron jobs removed"
        exit 0
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

# Add the cron job
echo "Adding cron job: $cron_entry"
(crontab -l 2>/dev/null | grep -v -E "(github_update|run_github_update)"; echo "$cron_entry") | crontab -

if [ $? -eq 0 ]; then
    echo ""
    echo "SUCCESS: GitHub-based automation set up successfully!"
    echo ""
    echo "Your FPL data will now update automatically when your GitHub repo is updated."
    echo "Logs will be written to: $(dirname "$SCRIPT_DIR")/logs/github_update.log"
    echo ""
    echo "The script will:"
    echo "• Check if updates are available in your repo"
    echo "• Only pull and update if changes are detected"
    echo "• Update your PostgreSQL database with fresh data"
    echo ""
    echo "To check current cron jobs: crontab -l"
    echo "To remove the automation, run this script again and choose option 7"
    echo ""
    echo "IMPORTANT: Make sure PostgreSQL is running when the cron job executes!"
else
    echo "ERROR: Failed to add cron job"
    exit 1
fi