#!/bin/bash

# GitHub-based FPL Data Update Automation Script
# This script pulls latest data from your forked repo and updates the database

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/github_update.log"
PYTHON_SCRIPT="$SCRIPT_DIR/automation/update_from_github.py"

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

# Check if git is available and repo exists
check_git_repo() {
    REPO_PATH="$SCRIPT_DIR"
    
    if [ ! -d "$REPO_PATH/.git" ]; then
        log_message "ERROR: FPL-Elo-Insights is not a git repository"
        log_message "Please ensure it's properly cloned from GitHub"
        exit 1
    fi
    
    log_message "Git repository found ✓"
}

# Main execution
main() {
    log_message "=== Starting GitHub-based FPL Data Update ==="
    
    # Rotate logs if needed
    if [ -f "$SCRIPT_DIR/scripts/rotate_logs.sh" ]; then
        "$SCRIPT_DIR/scripts/rotate_logs.sh" >/dev/null 2>&1
    fi
    
    # Change to script directory
    cd "$SCRIPT_DIR" || {
        log_message "ERROR: Could not change to script directory"
        exit 1
    }
    
    # Check prerequisites
    check_postgres
    check_git_repo
    
    # Run the Python update script
    log_message "Running GitHub update script..."
    
    if python3 "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1; then
        log_message "SUCCESS: GitHub-based FPL data update completed successfully"
        
        # Optional: Send notification
        # osascript -e 'display notification "FPL data updated from GitHub" with title "FPL Analytics"'
        
    else
        log_message "ERROR: GitHub-based FPL data update failed"
        
        # Optional: Send error notification
        # osascript -e 'display notification "FPL GitHub update failed - check logs" with title "FPL Analytics" sound name "Glass"'
        
        exit 1
    fi
    
    log_message "=== GitHub-based FPL Data Update Complete ==="
}

# Run main function
main "$@"