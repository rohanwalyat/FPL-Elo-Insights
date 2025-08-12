#!/bin/bash

# FPL Draft Data Update Script
# Fetches data from FPL Draft API and updates the database

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../logs/draft_update.log"
VENV_PYTHON="$SCRIPT_DIR/../fpl-venv/bin/python"

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if PostgreSQL is running
check_postgres() {
    if ! pgrep -x "postgres" > /dev/null; then
        log_message "ERROR: PostgreSQL is not running. Please start PostgreSQL first."
        exit 1
    fi
    log_message "PostgreSQL is running ✓"
}

# Check if virtual environment exists
check_venv() {
    if [ -f "$VENV_PYTHON" ]; then
        PYTHON_CMD="$VENV_PYTHON"
        log_message "Using FPL virtual environment ✓"
    else
        PYTHON_CMD="python3"
        log_message "Using system python3"
    fi
}

# Install required packages if needed
install_requirements() {
    log_message "Checking Python dependencies..."
    
    # Check if requests and pandas are available
    if ! $PYTHON_CMD -c "import requests, pandas" 2>/dev/null; then
        log_message "Installing required packages..."
        $PYTHON_CMD -m pip install requests pandas
    fi
    
    log_message "Dependencies verified ✓"
}

# Main execution
main() {
    log_message "=== Starting FPL Draft Data Update ==="
    
    # Change to script directory
    cd "$SCRIPT_DIR" || {
        log_message "ERROR: Could not change to script directory"
        exit 1
    }
    
    # Check prerequisites
    check_postgres
    check_venv
    install_requirements
    
    # Get league ID from user if not provided
    if [ -z "$1" ]; then
        echo "Enter your FPL Draft League ID:"
        read -r LEAGUE_ID
    else
        LEAGUE_ID="$1"
    fi
    
    if [ -z "$LEAGUE_ID" ]; then
        log_message "ERROR: League ID is required"
        exit 1
    fi
    
    log_message "Using League ID: $LEAGUE_ID"
    
    # Step 1: Fetch data from FPL Draft API
    log_message "Step 1: Fetching data from FPL Draft API..."
    
    if echo "$LEAGUE_ID" | $PYTHON_CMD fpl_draft_api.py >> "$LOG_FILE" 2>&1; then
        log_message "✓ API data fetch completed successfully"
    else
        log_message "✗ API data fetch failed"
        exit 1
    fi
    
    # Step 2: Update database
    log_message "Step 2: Updating database..."
    
    if $PYTHON_CMD draft_to_database.py "$LEAGUE_ID" >> "$LOG_FILE" 2>&1; then
        log_message "✓ Database update completed successfully"
    else
        log_message "✗ Database update failed"
        exit 1
    fi
    
    log_message "=== FPL Draft Data Update Complete ✅ ==="
    log_message "Check your database for updated draft league data!"
}

# Run main function
main "$@"