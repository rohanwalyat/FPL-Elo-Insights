#!/bin/bash

# Start Metabase for FPL ELO Insights
# Usage: ./start_metabase.sh

METABASE_DIR="/Users/rohanwalyat/Library/Mobile Documents/com~apple~CloudDocs/football-analytics/fpl-elo-insights/metabase"
METABASE_JAR="$METABASE_DIR/metabase.jar"
PID_FILE="$METABASE_DIR/metabase.pid"
LOG_FILE="$METABASE_DIR/metabase.log"

# Check if Metabase is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "Metabase is already running (PID: $PID)"
        echo "Access it at: http://localhost:3000"
        exit 1
    else
        echo "Removing stale PID file..."
        rm "$PID_FILE"
    fi
fi

# Check if port 3000 is in use
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Port 3000 is already in use. Please stop the service using that port."
    exit 1
fi

echo "Starting Metabase..."
echo "JAR file: $METABASE_JAR"
echo "Log file: $LOG_FILE"

# Start Metabase in background
cd "$METABASE_DIR"
nohup java -jar "$METABASE_JAR" > "$LOG_FILE" 2>&1 &
METABASE_PID=$!

# Save PID
echo $METABASE_PID > "$PID_FILE"

echo "Metabase started with PID: $METABASE_PID"
echo "Waiting for startup..."

# Wait for Metabase to start (check for successful startup in log)
for i in {1..30}; do
    if grep -q "Metabase Initialization COMPLETE" "$LOG_FILE" 2>/dev/null; then
        echo "✅ Metabase is ready!"
        echo "🌐 Access it at: http://localhost:3000"
        echo "📋 PID: $METABASE_PID"
        echo "📝 Logs: $LOG_FILE"
        exit 0
    fi
    sleep 2
    echo "Still starting... ($i/30)"
done

echo "⚠️  Metabase may still be starting. Check the log file: $LOG_FILE"
echo "🌐 Try accessing: http://localhost:3000"