#!/bin/bash

# Log rotation script for FPL Elo Insights
# Rotates logs when they exceed 10MB and keeps last 5 rotations

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS_DIR="$SCRIPT_DIR/logs"
METABASE_DIR="$SCRIPT_DIR/metabase"

# Maximum log size in bytes (10MB)
MAX_SIZE=10485760

# Number of rotations to keep
KEEP_ROTATIONS=5

rotate_log() {
    local log_file="$1"
    local base_name=$(basename "$log_file" .log)
    local dir_name=$(dirname "$log_file")
    
    if [ -f "$log_file" ]; then
        local file_size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null)
        
        if [ "$file_size" -gt "$MAX_SIZE" ]; then
            echo "Rotating $log_file (size: $file_size bytes)"
            
            # Rotate existing backup files
            for i in $(seq $((KEEP_ROTATIONS-1)) -1 1); do
                if [ -f "${dir_name}/${base_name}.log.$i" ]; then
                    mv "${dir_name}/${base_name}.log.$i" "${dir_name}/${base_name}.log.$((i+1))"
                fi
            done
            
            # Move current log to .1
            mv "$log_file" "${dir_name}/${base_name}.log.1"
            
            # Create new empty log file
            touch "$log_file"
            
            # Remove old rotations beyond our keep limit
            if [ -f "${dir_name}/${base_name}.log.$((KEEP_ROTATIONS+1))" ]; then
                rm "${dir_name}/${base_name}.log.$((KEEP_ROTATIONS+1))"
            fi
            
            echo "Log rotated: $log_file"
        else
            echo "Log $log_file is within size limit ($file_size bytes)"
        fi
    else
        echo "Log file $log_file does not exist"
    fi
}

echo "=== FPL Elo Insights Log Rotation ==="
echo "Max size: $MAX_SIZE bytes (10MB)"
echo "Keep rotations: $KEEP_ROTATIONS"
echo ""

# Rotate main logs
if [ -d "$LOGS_DIR" ]; then
    echo "Checking logs in $LOGS_DIR..."
    rotate_log "$LOGS_DIR/github_update.log"
    rotate_log "$LOGS_DIR/fpl_update.log"
    rotate_log "$LOGS_DIR/draft_update.log"
else
    echo "Logs directory $LOGS_DIR not found"
fi

# Rotate Metabase log
if [ -d "$METABASE_DIR" ]; then
    echo "Checking Metabase logs in $METABASE_DIR..."
    rotate_log "$METABASE_DIR/metabase.log"
else
    echo "Metabase directory $METABASE_DIR not found"
fi

echo ""
echo "Log rotation complete!"