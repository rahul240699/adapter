#!/bin/bash
# Simple Server Crash Monitor
# This script runs the agent server and captures why it stops

AGENT_ID=${1:-"agent_d"}
PORT=${2:-"6002"}

echo "🔍 Server Crash Monitor"
echo "======================"
echo "Agent ID: $AGENT_ID"
echo "Port: $PORT"
echo "Time: $(date)"
echo ""

# Create log file
LOG_FILE="crash_monitor_${AGENT_ID}.log"
echo "=== Server Crash Monitor Log ===" > $LOG_FILE
echo "Started: $(date)" >> $LOG_FILE
echo "Agent: $AGENT_ID" >> $LOG_FILE
echo "Port: $PORT" >> $LOG_FILE
echo "" >> $LOG_FILE

# Function to log with timestamp
log_message() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" >> $LOG_FILE
}

# Check system info before starting
log_message "🔍 Pre-startup system check:"
log_message "   Memory: $(free -h | grep '^Mem:' | awk '{print $7}') available"
log_message "   Disk: $(df -h . | tail -1 | awk '{print $4}') available"
log_message "   Python: $(python3 --version)"
log_message "   Working dir: $(pwd)"

# Check if port is available
if netstat -tuln | grep -q ":$PORT "; then
    log_message "   ⚠️ Port $PORT is already in use!"
    netstat -tuln | grep ":$PORT " >> $LOG_FILE
else
    log_message "   ✅ Port $PORT is available"
fi

# Set environment
export PORT=$PORT

log_message "🚀 Starting server..."

# Run the server and capture exit status
python3 interactive_agent_demo.py $AGENT_ID --server-only --verbose --service-charge 10 2>&1 | while read line; do
    log_message "SERVER: $line"
done

# Capture exit status
EXIT_CODE=$?
log_message "❌ Server stopped with exit code: $EXIT_CODE"

# Log system state after crash
log_message "🔍 Post-crash system check:"
log_message "   Memory: $(free -h | grep '^Mem:' | awk '{print $7}') available"
log_message "   Disk: $(df -h . | tail -1 | awk '{print $4}') available"

# Check for any Python processes still running
PYTHON_PROCS=$(ps aux | grep python | grep -v grep | wc -l)
log_message "   Python processes running: $PYTHON_PROCS"

# Check system logs for any related errors
log_message "🔍 Checking system logs for errors..."
if [ -f /var/log/syslog ]; then
    tail -20 /var/log/syslog | grep -i error >> $LOG_FILE 2>/dev/null
fi

# Check dmesg for memory/system issues
log_message "🔍 Checking dmesg for system issues..."
dmesg | tail -20 >> $LOG_FILE 2>/dev/null

log_message "📄 Full log saved to: $LOG_FILE"
echo ""
echo "💡 To analyze the crash:"
echo "   cat $LOG_FILE"
echo "   grep -i error $LOG_FILE"
echo "   grep -i 'exit code' $LOG_FILE"