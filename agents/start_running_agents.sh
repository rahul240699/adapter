#!/bin/bash
source /opt/internet_of_agents/venv/bin/activate

# Configuration
START_BRIDGE_PORT=6000
START_API_PORT=6001
NUM_AGENTS=7 # number of agents to the created 

# Source .bashrc to get environment variables
source ~/.bashrc

# Check for required environment variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY not found in .bashrc"
    exit 1
fi

if [ -z "$AGENT_ID_PREFIX" ]; then
    echo "Error: AGENT_ID_PREFIX not found in .bashrc"
    exit 1
fi

DOMAIN=nanda-registry.com

# SSL Configuration
CERT_PATH="/etc/letsencrypt/live/chat${AGENT_ID_PREFIX}.${DOMAIN}/fullchain.pem"  # Path to SSL certificate
KEY_PATH="/etc/letsencrypt/live/chat${AGENT_ID_PREFIX}.${DOMAIN}/privkey.pem"   # Path to SSL private key

# Create logs directory if it doesn't exist
mkdir -p logs

# Generate the list of ports
BRIDGE_PORTS=()
API_PORTS=()
for ((i=0; i<NUM_AGENTS; i++)); do
    BRIDGE_PORTS+=($((START_BRIDGE_PORT + i*2)))
    API_PORTS+=($((START_API_PORT + i*2)))
done

# Get the server IP address (assumes a public IP)
SERVER_IP=$(curl -s http://checkip.amazonaws.com)

# If the above command fails, try another method
if [ -z "$SERVER_IP" ]; then
    SERVER_IP=$(curl -s ifconfig.me)
fi

# If both methods fail, use localhost
if [ -z "$SERVER_IP" ]; then
    SERVER_IP="localhost.com"
    echo "Could not determine IP automatically, using default: $SERVER_IP"
else
    echo "Detected server IP: $SERVER_IP"
fi

# Source .bashrc to get the ANTHROPIC_API_KEY
source ~/.bashrc

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY not found in .bashrc"
    exit 1
fi

# Start each agent
for i in "${!BRIDGE_PORTS[@]}"; do
    AGENT_ID="agentm${AGENT_ID_PREFIX}$((i))"
    BRIDGE_PORT=${BRIDGE_PORTS[$i]}
    API_PORT=${API_PORTS[$i]}
    PUBLIC_URL="http://$SERVER_IP:$BRIDGE_PORT"
    API_URL="https://chat${AGENT_ID_PREFIX}.${DOMAIN}:$API_PORT"
    
    echo "Starting $AGENT_ID on bridge port $BRIDGE_PORT and API port $API_PORT"
    echo "Public URL: $PUBLIC_URL"
    echo "API URL: $API_URL"
    
    nohup python3 -u run_ui_agent_https.py --id "$AGENT_ID" --port "$BRIDGE_PORT" --api-port "$API_PORT" --public-url "$PUBLIC_URL" --api-url "$API_URL" --registry https://chat.nanda-registry.com:6900 --ssl --cert "$CERT_PATH" --key "$KEY_PATH" > "logs/${AGENT_ID}_logs.txt" 2>&1 &
    
    # Store the process ID for later reference
    echo "$!" > "logs/${AGENT_ID}.pid"
    
    echo "$AGENT_ID started with PID $!"
    
    # Wait a few seconds between agent starts to avoid race conditions
    sleep 2
done

echo "All agents started successfully!"
echo "Use the following command to check if agents are running:"
echo "ps aux | grep run_ui_agent_https"
echo ""
echo "To stop all agents:"
echo "for pid in logs/*.pid; do kill \$(cat \$pid); done" 

sleep 180