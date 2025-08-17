#!/bin/bash

# Metabase Database Resync Script
# This script triggers Metabase to resync its database schema after updates

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
METABASE_DIR="$PROJECT_ROOT/metabase"
PID_FILE="$METABASE_DIR/metabase.pid"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if Metabase is running
is_metabase_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0  # Running
        fi
    fi
    return 1  # Not running
}

# Function to start Metabase if not running
ensure_metabase_running() {
    if is_metabase_running; then
        log_message "✅ Metabase is already running"
        return 0
    fi
    
    log_message "🚀 Metabase is not running, starting it..."
    
    # Start Metabase
    cd "$SCRIPT_DIR"
    ./start_metabase.sh
    
    if [ $? -eq 0 ]; then
        log_message "✅ Metabase started successfully"
        
        # Wait a bit more for full initialization
        log_message "⏳ Waiting for Metabase to fully initialize..."
        sleep 10
        
        return 0
    else
        log_message "❌ Failed to start Metabase"
        return 1
    fi
}

# Function to check if port 3000 is accessible
check_metabase_accessible() {
    for i in {1..12}; do  # Try for 1 minute (12 * 5 seconds)
        if curl -s -f http://localhost:3000/api/health > /dev/null 2>&1; then
            log_message "✅ Metabase is accessible on http://localhost:3000"
            return 0
        fi
        
        log_message "⏳ Waiting for Metabase to be accessible... ($i/12)"
        sleep 5
    done
    
    log_message "❌ Metabase is not accessible after 1 minute"
    return 1
}

# Main execution
log_message "🔄 Starting Metabase Database Resync"
log_message "Project root: $PROJECT_ROOT"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    log_message "❌ Python 3 is required but not found"
    exit 1
fi

# Check if requests library is available
python3 -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    log_message "⚠ Installing requests library..."
    pip3 install requests
    if [ $? -ne 0 ]; then
        log_message "❌ Failed to install requests library"
        exit 1
    fi
fi

# Ensure Metabase is running
if ! ensure_metabase_running; then
    log_message "❌ Cannot start Metabase"
    exit 1
fi

# Check if Metabase is accessible
if ! check_metabase_accessible; then
    log_message "❌ Metabase is not accessible"
    exit 1
fi

# Check if virtual environment exists and activate it
VENV_PATH="$PROJECT_ROOT/fpl-venv"
if [ -d "$VENV_PATH" ]; then
    log_message "✅ Activating virtual environment"
    source "$VENV_PATH/bin/activate"
fi

# Run the Python resync script
log_message "🔄 Triggering Metabase database resync..."
cd "$PROJECT_ROOT"
python3 scripts/metabase_resync.py

RESYNC_EXIT_CODE=$?

# Check result
if [ $RESYNC_EXIT_CODE -eq 0 ]; then
    log_message "✅ Metabase database resync completed successfully"
    log_message "🌐 Your Metabase dashboards should now show the latest data"
    log_message "🔗 Access Metabase at: http://localhost:3000"
else
    log_message "❌ Metabase database resync failed"
    log_message "💡 Try manually refreshing the database in Metabase settings"
fi

# Deactivate virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

exit $RESYNC_EXIT_CODE