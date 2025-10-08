#!/bin/bash
# Persistent Agent Server Starter
# This script starts the agent server in a way that persists after SSH disconnection

AGENT_ID=${1:-"agent_d"}
PORT=${2:-"6002"}
SERVICE_CHARGE=${3:-"10"}

echo "🚀 Persistent Agent Server Starter"
echo "=================================="
echo "Agent ID: $AGENT_ID"
echo "Port: $PORT"
echo "Service Charge: $SERVICE_CHARGE NP"
echo ""

# Check if screen is available
if ! command -v screen &> /dev/null; then
    echo "⚠️ screen not found, installing..."
    sudo apt-get update && sudo apt-get install -y screen
fi

# Set environment variables
export PORT=$PORT

# Create screen session name
SESSION_NAME="agent_${AGENT_ID}_${PORT}"

# Check if session already exists
if screen -list | grep -q "$SESSION_NAME"; then
    echo "⚠️ Screen session $SESSION_NAME already exists"
    echo "   To attach: screen -r $SESSION_NAME"
    echo "   To kill: screen -S $SESSION_NAME -X quit"
    echo ""
    read -p "Kill existing session and start new one? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        screen -S $SESSION_NAME -X quit
        sleep 2
    else
        echo "Exiting..."
        exit 1
    fi
fi

echo "🔄 Starting $AGENT_ID in screen session: $SESSION_NAME"

# Create startup command
STARTUP_CMD="cd $(pwd) && source venv/bin/activate && python3 interactive_agent_demo.py $AGENT_ID --server-only --verbose --service-charge $SERVICE_CHARGE"

echo "📝 Command: $STARTUP_CMD"
echo ""

# Start screen session with the agent
screen -dmS "$SESSION_NAME" bash -c "$STARTUP_CMD"

# Wait a moment for startup
sleep 3

# Check if screen session is running
if screen -list | grep -q "$SESSION_NAME"; then
    echo "✅ Agent $AGENT_ID started successfully in screen session"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs: screen -r $SESSION_NAME"
    echo "   Detach: Ctrl+A, then D"
    echo "   Kill session: screen -S $SESSION_NAME -X quit"
    echo "   List sessions: screen -list"
    echo ""
    echo "🌐 Agent should be available at: http://$(curl -s ifconfig.me):$PORT"
    echo ""
    echo "💡 The agent will keep running even after you disconnect from SSH!"
else
    echo "❌ Failed to start agent $AGENT_ID"
    echo "Check the logs with: screen -r $SESSION_NAME"
    exit 1
fi