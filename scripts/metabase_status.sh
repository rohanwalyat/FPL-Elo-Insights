#!/bin/bash

# Check Metabase status for FPL ELO Insights
# Usage: ./metabase_status.sh

METABASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/metabase"
PID_FILE="$METABASE_DIR/metabase.pid"
LOG_FILE="$METABASE_DIR/metabase.log"

echo "=== Metabase Status ==="

# Check PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "PID file found: $PID"
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Metabase is running (PID: $PID)"
        echo "🌐 URL: http://localhost:3000"
        
        # Check if port is actually listening
        if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
            echo "✅ Port 3000 is listening"
        else
            echo "⚠️  Port 3000 is not listening yet"
        fi
        
        # Show recent log entries
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "📝 Recent log entries:"
            tail -n 5 "$LOG_FILE"
        fi
        
    else
        echo "❌ Process not running (stale PID file)"
        echo "Removing stale PID file..."
        rm "$PID_FILE"
    fi
else
    echo "No PID file found."
    
    # Check for running processes
    METABASE_PIDS=$(ps aux | grep "metabase.jar" | grep -v grep | awk '{print $2}')
    
    if [ -z "$METABASE_PIDS" ]; then
        echo "❌ Metabase is not running"
        
        # Check if port is in use by something else
        if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
            echo "⚠️  Port 3000 is in use by another process:"
            lsof -Pi :3000 -sTCP:LISTEN
        fi
    else
        echo "⚠️  Found Metabase processes without PID file: $METABASE_PIDS"
        
        if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
            echo "✅ Port 3000 is listening"
            echo "🌐 URL: http://localhost:3000"
        fi
    fi
fi

echo ""
echo "📁 Metabase directory: $METABASE_DIR"
echo "📝 Log file: $LOG_FILE"
echo "🔧 Control scripts:"
echo "   Start: ./start_metabase.sh"
echo "   Stop:  ./stop_metabase.sh"