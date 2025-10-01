#!/bin/bash

# EC2 NANDA Agent Setup Script
# Usage: ./setup_ec2_agent.sh <agent_id> [mode] [repo_url] [branch] [port]
# Example: ./setup_ec2_agent.sh agent_a interactive
# Example: ./setup_ec2_agent.sh agent_b server https://github.com/user/repo.git main 6001

set -e

# Parse arguments
AGENT_ID=${1:-agent_a}
MODE=${2:-interactive}
REPO_URL=${3:-"https://github.com/rahul240699/adapter.git"}
REPO_BRANCH=${4:-"feature/remote-deployment"}
PORT=${5:-6000}

echo "🚀 Setting up NANDA Agent: $AGENT_ID (mode: $MODE)"
echo "Repository: $REPO_URL"
echo "Branch: $REPO_BRANCH"
echo "Port: $PORT"
echo "================================================"

# Update system packages
echo "📦 Updating system packages..."
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv git curl

# Clone repository
echo "📥 Cloning repository..."
REPO_NAME=$(basename "$REPO_URL" .git)
if [ -d "$REPO_NAME" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd "$REPO_NAME"
    git pull origin $REPO_BRANCH
else
    git clone -b $REPO_BRANCH $REPO_URL
    cd "$REPO_NAME"
fi

# Setup Python virtual environment
echo "🐍 Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Setup environment file
echo "⚙️  Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo "🔧 Please edit .env file with your configuration:"
    echo "   - ANTHROPIC_API_KEY (your Claude API key)"
    echo "   - MONGODB_URI (your MongoDB connection string)"
    echo "   - Update AGENT_ID to: $AGENT_ID"
    echo "   - Update PORT to: $PORT"
    echo "   - Set PUBLIC_URL=auto (for auto-detection) or specify manually"
else
    echo "✅ .env file already exists"
fi

# Create systemd service file (optional)
echo "🔧 Creating systemd service template..."
sudo tee /tmp/nanda-$AGENT_ID.service > /dev/null <<EOF
[Unit]
Description=NANDA Agent $AGENT_ID
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/$REPO_NAME
Environment=PATH=/home/ubuntu/$REPO_NAME/venv/bin
ExecStart=/home/ubuntu/$REPO_NAME/venv/bin/python3 interactive_agent_demo.py $AGENT_ID $([ "$MODE" = "server" ] && echo "--server-only" || echo "")
Restart=always
RestartSec=3
StandardOutput=append:/var/log/nanda-$AGENT_ID.log
StandardError=append:/var/log/nanda-$AGENT_ID.log

[Install]
WantedBy=multi-user.target
EOF

echo "📋 Systemd service template created at /tmp/nanda-$AGENT_ID.service"
echo "   To install: sudo mv /tmp/nanda-$AGENT_ID.service /etc/systemd/system/"
echo "   Then run: sudo systemctl daemon-reload && sudo systemctl enable nanda-$AGENT_ID"

# Test network configuration
echo "🌐 Testing network configuration..."
python3 -c "
from nanda_adapter.core.network_utils import print_network_debug_info
print_network_debug_info()
" || echo "⚠️  Network utils not available, continuing..."

echo ""
echo "✅ Setup complete for $AGENT_ID!"
echo "================================================"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file with your API keys and MongoDB URI:"
echo "   nano .env"
echo ""
echo "2. Start the agent:"
if [ "$MODE" = "server" ]; then
    echo "   source venv/bin/activate"
    echo "   python3 interactive_agent_demo.py $AGENT_ID --server-only"
else
    echo "   source venv/bin/activate"  
    echo "   python3 interactive_agent_demo.py $AGENT_ID"
fi
echo ""
echo "3. Optional - Install as systemd service:"
echo "   sudo mv /tmp/nanda-$AGENT_ID.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable nanda-$AGENT_ID"
echo "   sudo systemctl start nanda-$AGENT_ID"
echo ""
echo "🎯 Agent $AGENT_ID setup ready!"