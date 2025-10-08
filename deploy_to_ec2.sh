#!/bin/bash

# NANDA EC2 Deployment Script
# Usage: ./deploy_to_ec2.sh [config_file]
# Example: ./deploy_to_ec2.sh deployment_config.sh

set -e

# Load configuration
CONFIG_FILE=${1:-"deployment_config.sh"}

if [ -f "$CONFIG_FILE" ]; then
    echo "📋 Loading configuration from $CONFIG_FILE"
    source "$CONFIG_FILE"
else
    echo "⚠️  Configuration file '$CONFIG_FILE' not found."
    echo "Creating template configuration file..."
    
    cat > deployment_config.sh << 'EOF'
#!/bin/bash
# NANDA Agent Deployment Configuration

# SSH Configuration
SSH_KEY="your-key.pem"                    # Path to your SSH private key
SSH_USER="ubuntu"                         # SSH username (ubuntu for Ubuntu instances)

# Repository Configuration  
REPO_URL="https://github.com/user/repo.git"  # Your repository URL
REPO_BRANCH="main"                           # Branch to deploy

# Agent Instances Configuration
# Format: "IP:AGENT_ID:PORT:MODE"
# MODE can be "interactive" or "server"
INSTANCES=(
    "1.2.3.4:agent_a:6001:interactive"
    "5.6.7.8:agent_b:6002:server"
)

# Optional: Custom deployment directory (default: repository name)
# DEPLOY_DIR="custom-directory"
EOF
    
    echo "✅ Created template: deployment_config.sh"
    echo "Please edit it with your configuration and run again."
    exit 1
fi

# Validate configuration
if [ -z "$SSH_KEY" ] || [ -z "$SSH_USER" ] || [ -z "$REPO_URL" ] || [ -z "$REPO_BRANCH" ]; then
    echo "❌ Missing required configuration variables!"
    echo "   Please check your configuration file."
    exit 1
fi

if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key '$SSH_KEY' not found!"
    echo "   Please ensure the key path is correct."
    exit 1
fi

if [ ${#INSTANCES[@]} -eq 0 ]; then
    echo "❌ No instances configured!"
    echo "   Please add instances to the INSTANCES array."
    exit 1
fi

REPO_NAME=${DEPLOY_DIR:-$(basename "$REPO_URL" .git)}

echo "🚀 NANDA Agent EC2 Deployment"
echo "================================="
echo "Repository: $REPO_URL"
echo "Branch: $REPO_BRANCH" 
echo "Deploy to: $REPO_NAME"
echo "Instances: ${#INSTANCES[@]}"
for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    echo "  - $ip ($agent_id:$port) [$mode]"
done
echo ""

# Function to deploy to an instance
deploy_to_instance() {
    local instance_ip=$1
    local agent_id=$2
    local port=$3
    local mode=$4
    
    echo "🔧 Deploying $agent_id to $instance_ip..."
    
    # Create deployment commands
    cat > /tmp/deploy_${agent_id}.sh << EOF
#!/bin/bash
set -e

echo "🔧 Starting deployment for $agent_id on $instance_ip"

# Update system
echo "📦 Updating system packages..."
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv git curl

# Test network connectivity first
echo "🌐 Testing network connectivity..."
if ! curl -s --connect-timeout 10 https://google.com > /dev/null; then
    echo "⚠️  Warning: Network connectivity issues detected"
fi

# Clone repo
if [ -d "$REPO_NAME" ]; then
    echo "Repository exists, updating..."
    cd "$REPO_NAME"
    git pull origin $REPO_BRANCH
else
    git clone -b $REPO_BRANCH $REPO_URL
    cd "$REPO_NAME"
fi

# Setup Python environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install X402 dependencies
echo "🔧 Installing X402 payment system dependencies..."
./setup_x402_dependencies.sh || echo "⚠️  X402 setup completed with warnings"

# Run network diagnostics
echo "🩺 Running network diagnostics..."
python3 network_diagnostic.py || echo "⚠️  Diagnostics completed with warnings"

# Create .env file template (user needs to edit)
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || cat > .env << 'ENVEOF'
# Anthropic Claude API Key (Required - REPLACE WITH YOUR KEY)
ANTHROPIC_API_KEY=your_actual_anthropic_api_key_here

# Agent Configuration
AGENT_ID=$agent_id
USE_LOCAL_REGISTRY=false

# Network Configuration
PUBLIC_URL=auto
INTERNAL_HOST=0.0.0.0
PORT=$port

# Registry Configuration (REPLACE WITH YOUR MONGODB URI)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/nanda?retryWrites=true&w=majority
MONGODB_DATABASE=nanda
MONGODB_COLLECTION=agents

# Development settings
DEBUG=false
LOG_LEVEL=INFO
ENVEOF

    # Update specific values
    sed -i "s/AGENT_ID=.*/AGENT_ID=$agent_id/" .env
    sed -i "s/PORT=.*/PORT=$port/" .env
else
    echo "✅ .env file already exists, updating AGENT_ID and PORT"
    sed -i "s/AGENT_ID=.*/AGENT_ID=$agent_id/" .env
    sed -i "s/PORT=.*/PORT=$port/" .env
fi

echo "✅ $agent_id deployment complete!"
echo "📝 Next steps:"
echo "1. Edit .env file with your API keys:"
echo "   nano $REPO_NAME/.env"
echo "2. Start the agent:"
if [ "$mode" = "server" ]; then
    echo "   cd $REPO_NAME && source venv/bin/activate && python3 interactive_agent_demo.py $agent_id --server-only"
else
    echo "   cd $REPO_NAME && source venv/bin/activate && python3 interactive_agent_demo.py $agent_id"
fi
EOF

    # Copy and execute deployment script
    scp -i "$SSH_KEY" /tmp/deploy_${agent_id}.sh ${SSH_USER}@${instance_ip}:/tmp/
    ssh -i "$SSH_KEY" ${SSH_USER}@${instance_ip} "chmod +x /tmp/deploy_${agent_id}.sh && /tmp/deploy_${agent_id}.sh"
    
    # Clean up
    rm /tmp/deploy_${agent_id}.sh
    
    echo "✅ $agent_id deployed to $instance_ip"
    echo ""
}

# Deploy to all instances
counter=1
for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    echo "${counter}️⃣ Deploying $agent_id ($mode mode) to $ip..."
    deploy_to_instance "$ip" "$agent_id" "$port" "$mode"
    ((counter++))
done

echo "🎉 Deployment Complete!"
echo "======================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1️⃣ Configure environment on each instance:"
counter=1
for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    echo "   Instance $counter ($agent_id):"
    echo "   ssh -i \"$SSH_KEY\" ${SSH_USER}@${ip}"
    echo "   nano $REPO_NAME/.env  # Add your ANTHROPIC_API_KEY and MONGODB_URI"
    echo ""
    ((counter++))
done

echo "2️⃣ Start agents (server-only modes first):"
for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    if [ "$mode" = "server" ]; then
        echo "   ssh -i \"$SSH_KEY\" ${SSH_USER}@${ip}"
        echo "   cd $REPO_NAME && source venv/bin/activate"
        echo "   python3 interactive_agent_demo.py $agent_id --server-only"
        echo ""
    fi
done

echo "3️⃣ Then start interactive agents:"
for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    if [ "$mode" = "interactive" ]; then
        echo "   ssh -i \"$SSH_KEY\" ${SSH_USER}@${ip}"
        echo "   cd $REPO_NAME && source venv/bin/activate"
        echo "   python3 interactive_agent_demo.py $agent_id"
        echo ""
    fi
done

echo "4️⃣ Test A2A communication:"
echo "   In any interactive agent terminal, use: @other_agent_id message"
echo ""
echo "🔗 Required Configuration:"
echo "   - ANTHROPIC_API_KEY: Get from https://console.anthropic.com/"
echo "   - MONGODB_URI: Your MongoDB Atlas connection string"
echo ""
echo "🚀 Your distributed NANDA agents are ready to deploy!"