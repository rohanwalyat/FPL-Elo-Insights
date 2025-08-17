#!/bin/bash

# FPL Database Ingestion Runner Script
# This script runs the database ingestion automation with proper logging and error handling

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/database_ingestion.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Start logging
log_message "=== Starting FPL Database Ingestion ==="
log_message "Project root: $PROJECT_ROOT"
log_message "Log file: $LOG_FILE"

# Check prerequisites
log_message "Checking prerequisites..."

# Check if PostgreSQL is running
if command_exists psql; then
    log_message "✓ PostgreSQL client found"
    
    # Test database connection
    cd "$PROJECT_ROOT"
    if source .env 2>/dev/null && PGPASSWORD="$PGPASSWORD" psql -U postgres -d fpl_elo -c "SELECT 1;" >/dev/null 2>&1; then
        log_message "✓ Database connection successful"
    else
        log_message "✗ Database connection failed"
        log_message "Make sure PostgreSQL is running and credentials are correct"
        log_message "Check your .env file or try: psql -U postgres -d fpl_elo"
        exit 1
    fi
else
    log_message "✗ PostgreSQL client not found"
    log_message "Install PostgreSQL or ensure 'psql' is in your PATH"
    exit 1
fi

# Check if Python is available
if command_exists python3; then
    log_message "✓ Python 3 found"
else
    log_message "✗ Python 3 not found"
    exit 1
fi

# Check if virtual environment exists
VENV_PATH="$PROJECT_ROOT/fpl-venv"
if [ -d "$VENV_PATH" ]; then
    log_message "✓ Virtual environment found at $VENV_PATH"
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    log_message "✓ Virtual environment activated"
else
    log_message "⚠ Virtual environment not found, using system Python"
fi

# Check for required Python packages
log_message "Checking Python dependencies..."
python3 -c "import pandas, psycopg2, dotenv" 2>/dev/null
if [ $? -eq 0 ]; then
    log_message "✓ Required Python packages available"
else
    log_message "⚠ Some Python packages may be missing"
    log_message "Installing required packages..."
    pip install pandas psycopg2-binary python-dotenv
fi

# Check if data directory exists
DATA_DIR="$PROJECT_ROOT/data"
if [ -d "$DATA_DIR" ]; then
    log_message "✓ Data directory found"
    
    # Check for season data
    if [ -d "$DATA_DIR/2025-2026" ]; then
        log_message "✓ 2025-2026 season data found"
    else
        log_message "⚠ 2025-2026 season data not found"
    fi
    
    # Check for draft league data
    if [ -d "$DATA_DIR/draft_league" ]; then
        log_message "✓ Draft league data found"
    else
        log_message "⚠ Draft league data not found"
    fi
else
    log_message "✗ Data directory not found"
    log_message "Make sure you have data files in the correct location"
    exit 1
fi

# Change to project root directory
cd "$PROJECT_ROOT"

# Run the database ingestion script
log_message "Running database ingestion..."
log_message "----------------------------------------"

# Use the virtual environment's Python if available
VENV_PYTHON="$VENV_PATH/bin/python"
if [ -f "$VENV_PYTHON" ]; then
    PYTHON_CMD="$VENV_PYTHON"
elif [ -n "$VIRTUAL_ENV" ] && [ -f "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_CMD="$VIRTUAL_ENV/bin/python"
else
    PYTHON_CMD="python3"
fi

log_message "Using Python: $PYTHON_CMD"
"$PYTHON_CMD" automation/database_ingestion.py 2>&1 | tee -a "$LOG_FILE"
INGESTION_EXIT_CODE=${PIPESTATUS[0]}

log_message "----------------------------------------"

# Check if ingestion was successful
if [ $INGESTION_EXIT_CODE -eq 0 ]; then
    log_message "✅ Database ingestion completed successfully"
    
    # Show quick database summary
    log_message "Quick database summary:"
    source .env 2>/dev/null
    PGPASSWORD="$PGPASSWORD" psql -U postgres -d fpl_elo -c "
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
        SELECT 'Draft Picks', COUNT(*) FROM draft_picks;
    " 2>/dev/null | tee -a "$LOG_FILE"
    
else
    log_message "❌ Database ingestion failed with exit code $INGESTION_EXIT_CODE"
    log_message "Check the log above for error details"
    exit 1
fi

log_message "=== Database Ingestion Complete ==="
log_message "Log file: $LOG_FILE"

# Deactivate virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi