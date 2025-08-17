#!/bin/bash

# Install Cron Jobs for FPL Data Updates
# Sets up scheduled jobs at 5:00 AM UTC and 5:00 PM UTC

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "🕐 Installing FPL Data Update Cron Jobs"
echo "📂 Repository: $REPO_DIR"

# Path to the scheduled update script
UPDATE_SCRIPT="$SCRIPT_DIR/run_scheduled_update.sh"

# Check if the update script exists
if [ ! -f "$UPDATE_SCRIPT" ]; then
    echo "❌ Update script not found: $UPDATE_SCRIPT"
    exit 1
fi

# Make sure the script is executable
chmod +x "$UPDATE_SCRIPT"

# Create temporary cron file
TEMP_CRON=$(mktemp)

# Get current crontab (if any) and filter out existing FPL entries
crontab -l 2>/dev/null | grep -v "FPL Data Update" > "$TEMP_CRON" || true

# Add new cron jobs
echo "" >> "$TEMP_CRON"
echo "# FPL Data Update Jobs - Check for new data from olbauday/FPL-Elo-Insights fork" >> "$TEMP_CRON"
echo "# 5:00 AM UTC (when fork typically updates)" >> "$TEMP_CRON"
echo "0 5 * * * $UPDATE_SCRIPT # FPL Data Update - Morning" >> "$TEMP_CRON"
echo "# 5:00 PM UTC (when fork typically updates)" >> "$TEMP_CRON"  
echo "0 17 * * * $UPDATE_SCRIPT # FPL Data Update - Evening" >> "$TEMP_CRON"

# Install the new crontab
crontab "$TEMP_CRON"

# Clean up
rm "$TEMP_CRON"

echo "✅ Cron jobs installed successfully!"
echo ""
echo "📅 Scheduled jobs:"
echo "   • 5:00 AM UTC (Daily) - Check for morning data updates"
echo "   • 5:00 PM UTC (Daily) - Check for evening data updates"
echo ""
echo "📝 Logs will be saved to: $REPO_DIR/logs/scheduled_update_*.log"
echo ""
echo "🔍 To view current cron jobs:"
echo "   crontab -l"
echo ""
echo "🗑️  To remove these cron jobs:"
echo "   crontab -l | grep -v 'FPL Data Update' | crontab -"
echo ""

# Show current crontab
echo "📋 Current crontab:"
crontab -l