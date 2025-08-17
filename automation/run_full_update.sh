#!/bin/bash

# Complete FPL Data Update Automation Wrapper
# This is the master script that runs the complete end-to-end workflow:
# 1. Check GitHub fork for updates
# 2. Pull latest data from fork
# 3. Update draft league data from FPL API  
# 4. Ingest all updated data into PostgreSQL database

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/full_update_automation.log"

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
log_message "🚀 Starting Complete FPL Data Update Automation"
log_message "Project root: $PROJECT_ROOT"
log_message "Log file: $LOG_FILE"
log_message "================================================================"

# Check basic prerequisites
log_message "Checking basic prerequisites..."

# Check if we're in the right directory
if [ ! -d "$PROJECT_ROOT/automation" ]; then
    log_message "❌ Automation directory not found"
    log_message "Make sure you're running this from the FPL-Elo-Insights project"
    exit 1
fi

# Check if PostgreSQL is available
if command_exists psql; then
    log_message "✅ PostgreSQL client found"
else
    log_message "❌ PostgreSQL client not found"
    log_message "Install PostgreSQL or ensure 'psql' is in your PATH"
    exit 1
fi

# Check if git is available
if command_exists git; then
    log_message "✅ Git found"
else
    log_message "❌ Git not found"
    log_message "Install Git to use this automation"
    exit 1
fi

# Check if Python is available
if command_exists python3; then
    log_message "✅ Python 3 found"
else
    log_message "❌ Python 3 not found"
    exit 1
fi

# Check if we're in a git repository
cd "$PROJECT_ROOT"
if [ ! -d ".git" ]; then
    log_message "❌ Not in a git repository"
    log_message "Make sure this project is a git repository"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    log_message "❌ .env file not found"
    log_message "Create a .env file with database credentials"
    log_message "Example:"
    log_message "PGHOST=localhost"
    log_message "PGPORT=5432"
    log_message "PGDATABASE=fpl_elo"
    log_message "PGUSER=postgres"
    log_message "PGPASSWORD=your_password"
    exit 1
fi

# Test database connection
log_message "Testing database connection..."
source .env 2>/dev/null
if PGPASSWORD="$PGPASSWORD" psql -U postgres -d fpl_elo -c "SELECT 1;" >/dev/null 2>&1; then
    log_message "✅ Database connection successful"
else
    log_message "❌ Database connection failed"
    log_message "Check your .env file and ensure PostgreSQL is running"
    log_message "Test manually: psql -U postgres -d fpl_elo"
    exit 1
fi

# Check if virtual environment exists and set up Python command
VENV_PATH="$PROJECT_ROOT/fpl-venv"
if [ -d "$VENV_PATH" ]; then
    log_message "✅ Virtual environment found"
    PYTHON_CMD="$VENV_PATH/bin/python"
    
    # Check if Python is working in venv
    if [ -f "$PYTHON_CMD" ]; then
        log_message "✅ Virtual environment Python found"
    else
        log_message "⚠ Virtual environment Python not found, using system Python"
        PYTHON_CMD="python3"
    fi
else
    log_message "⚠ Virtual environment not found, using system Python"
    PYTHON_CMD="python3"
fi

# Check if automation script exists
AUTOMATION_SCRIPT="$SCRIPT_DIR/full_update_automation.py"
if [ ! -f "$AUTOMATION_SCRIPT" ]; then
    log_message "❌ Automation script not found: $AUTOMATION_SCRIPT"
    exit 1
fi

# Install required Python packages if needed
log_message "Checking Python dependencies..."
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate" 2>/dev/null || true
fi

# Check for required packages
python3 -c "import pandas, psycopg2, dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    log_message "⚠ Some Python packages missing, installing..."
    pip install pandas psycopg2-binary python-dotenv requests
    if [ $? -ne 0 ]; then
        log_message "❌ Failed to install required packages"
        exit 1
    fi
    log_message "✅ Python packages installed"
else
    log_message "✅ Required Python packages available"
fi

# Run the complete automation
log_message "================================================================"
log_message "🎯 Running Complete FPL Data Update Automation"
log_message "================================================================"

# Execute the automation script
"$PYTHON_CMD" "$AUTOMATION_SCRIPT"
AUTOMATION_EXIT_CODE=$?

log_message "================================================================"

# Check automation result
if [ $AUTOMATION_EXIT_CODE -eq 0 ]; then
    log_message "🎉 Complete automation finished successfully!"
    
    # Show quick status
    log_message "📊 Quick Status Check:"
    PGPASSWORD="$PGPASSWORD" psql -U postgres -d fpl_elo -c "
        SELECT 
            'Last Updated: ' || NOW()::timestamp(0) as status
        UNION ALL
        SELECT 
            'Total Records: ' || (
                (SELECT COUNT(*) FROM teams) + 
                (SELECT COUNT(*) FROM players) + 
                (SELECT COUNT(*) FROM matches) + 
                (SELECT COUNT(*) FROM playermatchstats) +
                (SELECT COUNT(*) FROM draft_managers) +
                (SELECT COUNT(*) FROM draft_picks)
            )::text as status;
    " 2>/dev/null | tail -n +3 | head -n -1 | while read line; do
        log_message "   $line"
    done
    
else
    log_message "❌ Automation failed with exit code $AUTOMATION_EXIT_CODE"
    log_message "Check the logs above for details"
    exit 1
fi

log_message "================================================================"
log_message "✅ Complete FPL Data Update Automation Finished"
log_message "📁 Full log: $LOG_FILE"
log_message "================================================================"

# Deactivate virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi