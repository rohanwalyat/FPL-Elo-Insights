#!/bin/bash

# Stop Metabase for FPL ELO Insights
# Usage: ./stop_metabase.sh

METABASE_DIR="/Users/rohanwalyat/Library/Mobile Documents/com~apple~CloudDocs/football-analytics/fpl-elo-insights/metabase"
PID_FILE="$METABASE_DIR/metabase.pid"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "PID file not found. Checking for Metabase processes..."
    
    # Try to find Metabase process by looking for java processes with metabase.jar
    METABASE_PIDS=$(ps aux | grep "metabase.jar" | grep -v grep | awk '{print $2}')
    
    if [ -z "$METABASE_PIDS" ]; then
        echo "No Metabase processes found."
        exit 0
    else
        echo "Found Metabase processes: $METABASE_PIDS"
        for PID in $METABASE_PIDS; do
            echo "Killing process $PID..."
            kill $PID
            sleep 2
            
            # Force kill if still running
            if ps -p $PID > /dev/null 2>&1; then
                echo "Force killing process $PID..."
                kill -9 $PID
            fi
        done
        echo "Metabase stopped."
        exit 0
    fi
fi

# Read PID from file
PID=$(cat "$PID_FILE")

# Check if process is running
if ! ps -p $PID > /dev/null 2>&1; then
    echo "Metabase process (PID: $PID) is not running."
    rm "$PID_FILE"
    exit 0
fi

echo "Stopping Metabase (PID: $PID)..."

# Try graceful shutdown first
kill $PID

# Wait for process to stop
for i in {1..10}; do
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "✅ Metabase stopped gracefully."
        rm "$PID_FILE"
        exit 0
    fi
    sleep 1
    echo "Waiting for shutdown... ($i/10)"
done

# Force kill if still running
echo "Force stopping Metabase..."
kill -9 $PID

# Wait a bit more
sleep 2

if ! ps -p $PID > /dev/null 2>&1; then
    echo "✅ Metabase force stopped."
    rm "$PID_FILE"
else
    echo "❌ Failed to stop Metabase. Process may still be running."
    exit 1
fi