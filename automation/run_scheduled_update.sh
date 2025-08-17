#!/bin/bash

# FPL Data Scheduled Update Script
# Runs the full automation pipeline at scheduled times (5:00 AM & 5:00 PM UTC)

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Create logs directory if it doesn't exist
mkdir -p "$REPO_DIR/logs"

# Set up log file with timestamp
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
LOG_FILE="$REPO_DIR/logs/scheduled_update_$TIMESTAMP.log"

# Function to log with timestamp
log() {
    echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] $1" | tee -a "$LOG_FILE"
}

log "🕐 Starting scheduled FPL data update"
log "📂 Repository: $REPO_DIR"
log "📝 Log file: $LOG_FILE"

# Change to repository directory
cd "$REPO_DIR" || {
    log "❌ Failed to change to repository directory: $REPO_DIR"
    exit 1
}

# Check if we're in the right directory
if [ ! -f "automation/full_update_automation.py" ]; then
    log "❌ Cannot find automation script. Current directory: $(pwd)"
    exit 1
fi

# Load environment variables if .env exists
if [ -f ".env" ]; then
    log "📋 Loading environment variables from .env"
    set -a
    source .env
    set +a
else
    log "⚠️  No .env file found, using system environment"
fi

# Check if virtual environment exists and activate it
if [ -d "fpl-venv" ]; then
    log "🐍 Activating virtual environment"
    source fpl-venv/bin/activate
else
    log "⚠️  No virtual environment found, using system Python"
fi

# Run the full automation
log "🚀 Running full update automation"
python3 automation/full_update_automation.py 2>&1 | tee -a "$LOG_FILE"

# Capture exit code
EXIT_CODE=${PIPESTATUS[0]}

if [ $EXIT_CODE -eq 0 ]; then
    log "✅ Scheduled update completed successfully"
else
    log "❌ Scheduled update failed with exit code: $EXIT_CODE"
fi

# Clean up old log files (keep last 30 days)
log "🧹 Cleaning up old log files"
find "$REPO_DIR/logs" -name "scheduled_update_*.log" -mtime +30 -delete 2>/dev/null || true

log "🏁 Scheduled update script finished"

exit $EXIT_CODE