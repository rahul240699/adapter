#!/bin/bash

# NANDA Agent Deployment Tester
# Usage: ./test_deployment.sh [config_file]
# Run this after deploying agents to test connectivity and functionality

set -e

# Load configuration
CONFIG_FILE=${1:-"deployment_config.sh"}

if [ -f "$CONFIG_FILE" ]; then
    echo "📋 Loading test configuration from $CONFIG_FILE"
    source "$CONFIG_FILE"
elif [ -f "my_deployment_config.sh" ]; then
    echo "📋 Loading test configuration from my_deployment_config.sh"
    source "my_deployment_config.sh"
else
    echo "❌ No configuration file found!"
    echo "   Please provide configuration file as argument or create deployment_config.sh"
    exit 1
fi

REPO_NAME=${DEPLOY_DIR:-$(basename "$REPO_URL" .git)}

echo "🧪 NANDA Agent Deployment Test"
echo "==============================="
echo "Testing ${#INSTANCES[@]} instances:"
for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    echo "  - $ip ($agent_id:$port) [$mode]"
done
echo ""

# Function to test agent endpoint
test_agent_endpoint() {
    local ip=$1
    local port=$2
    local agent_name=$3
    
    echo "🔍 Testing $agent_name endpoint (http://$ip:$port)..."
    
    if curl -s --connect-timeout 5 "http://$ip:$port/health" > /dev/null; then
        echo "✅ $agent_name is responding on $ip:$port"
        return 0
    else
        echo "❌ $agent_name is not accessible on $ip:$port"
        return 1
    fi
}

# Function to check agent status on instance  
check_agent_status() {
    local ip=$1
    local agent_id=$2
    local description=$3
    
    echo "🔍 Checking $description status..."
    
    ssh -i "$SSH_KEY" -o ConnectTimeout=10 ubuntu@${ip} << EOF
echo "📊 System Status for $agent_id:"
echo "================================"

# Check if agent directory exists
if [ -d "$REPO_NAME" ]; then
    echo "✅ Repository cloned"
    cd "$REPO_NAME"
    
    # Check Python environment
    if [ -d "venv" ]; then
        echo "✅ Python virtual environment created"
        
        # Check if .env exists and has required vars
        if [ -f ".env" ]; then
            echo "✅ .env file exists"
            
            # Check for required environment variables (without showing values)
            echo "🔧 Environment Configuration:"
            if grep -q "ANTHROPIC_API_KEY=" .env && ! grep -q "your_actual_anthropic_api_key_here" .env; then
                echo "  ✅ ANTHROPIC_API_KEY configured"
            else
                echo "  ❌ ANTHROPIC_API_KEY needs configuration"
            fi
            
            if grep -q "MONGODB_URI=" .env && ! grep -q "username:password" .env; then
                echo "  ✅ MONGODB_URI configured"
            else
                echo "  ❌ MONGODB_URI needs configuration"
            fi
            
            if grep -q "AGENT_ID=$agent_id" .env; then
                echo "  ✅ AGENT_ID correctly set to $agent_id"
            else
                echo "  ❌ AGENT_ID not properly configured"
            fi
        else
            echo "❌ .env file missing"
        fi
        
        # Check if dependencies are installed
        source venv/bin/activate
        if python3 -c "import anthropic, pymongo, requests" 2>/dev/null; then
            echo "✅ Required Python packages installed"
        else
            echo "❌ Some Python packages missing"
        fi
        
        # Check network configuration
        echo "🌐 Network Configuration:"
        python3 -c "
from nanda_adapter.core.network_utils import print_network_debug_info
print_network_debug_info()
        " 2>/dev/null || echo "  ⚠️  Network utils check failed"
        
    else
        echo "❌ Python virtual environment missing"
    fi
else
    echo "❌ Repository not cloned"
fi

# Check if agent process is running
echo "🔄 Process Status:"
if pgrep -f "interactive_agent_demo.py $agent_id" > /dev/null; then
    echo "✅ Agent $agent_id process is running"
    echo "📊 Process details:"
    ps aux | grep "interactive_agent_demo.py $agent_id" | grep -v grep
else
    echo "❌ Agent $agent_id process not running"
fi

# Check network connectivity
echo "🌐 Network Connectivity:"
if ss -tlnp | grep ":$3 " > /dev/null; then
    echo "✅ Port $3 is listening"
else
    echo "❌ Port $3 is not listening"
fi

echo ""
EOF
}

# Function to test registry connectivity
test_registry_connection() {
    local ip=$1
    local agent_id=$2
    
    echo "🗄️ Testing MongoDB registry connection for $agent_id..."
    
    ssh -i "$SSH_KEY" ubuntu@${ip} << 'EOF'
cd "$REPO_NAME"
source venv/bin/activate
python3 -c "
try:
    from nanda_adapter.core.registry import create_registry
    from nanda_adapter.core.env_loader import load_env
    
    load_env()
    registry = create_registry()
    agents = registry.list()
    
    print('✅ Registry connection successful')
    print(f'📋 Found {len(agents)} registered agents:')
    for agent in agents:
        print(f'  - {agent[\"agent_id\"]}: {agent[\"agent_url\"]}')
        
except Exception as e:
    print(f'❌ Registry connection failed: {e}')
" 2>/dev/null || echo "❌ Registry test failed"
EOF
}

echo "1️⃣ Checking Instance Connectivity"
echo "=================================="

# Test SSH connectivity
echo "🔗 Testing SSH connectivity..."
counter=1
for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    if ssh -i "$SSH_KEY" -o ConnectTimeout=10 ${SSH_USER}@${ip} "echo 'SSH OK'" > /dev/null 2>&1; then
        echo "✅ SSH to Instance $counter ($ip) working"
    else
        echo "❌ SSH to Instance $counter ($ip) failed"
        echo "   Check your SSH key and security groups"
        exit 1
    fi
    ((counter++))
done

echo ""
echo "2️⃣ Checking Agent Deployment Status"
echo "===================================="

for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    check_agent_status "$ip" "$agent_id" "$agent_id ($mode)" "$port"
    echo ""
done

echo ""
echo "3️⃣ Testing Agent Endpoints"
echo "=========================="

for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    test_agent_endpoint "$ip" "$port" "$agent_id"
done

echo ""
echo "4️⃣ Testing Registry Connections"
echo "==============================="

for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    test_registry_connection "$ip" "$agent_id"
    echo ""
done

echo ""
echo "5️⃣ Cross-Instance Connectivity Test"
echo "===================================="

echo "🔗 Testing cross-instance connectivity..."

# Test connectivity between all instances
for instance1 in "${INSTANCES[@]}"; do
    IFS=':' read -r ip1 agent_id1 port1 mode1 <<< "$instance1"
    
    for instance2 in "${INSTANCES[@]}"; do
        IFS=':' read -r ip2 agent_id2 port2 mode2 <<< "$instance2"
        
        # Skip self-test
        if [ "$ip1" != "$ip2" ]; then
            ssh -i "$SSH_KEY" ${SSH_USER}@${ip1} << EOF
echo "Testing $agent_id1 → $agent_id2:"
if curl -s --connect-timeout 5 "http://$ip2:$port2/health" > /dev/null; then
    echo "✅ $agent_id1 can reach $agent_id2"
else
    echo "❌ $agent_id1 cannot reach $agent_id2"
    echo "   Check security groups and network configuration"
fi
EOF
        fi
    done
done

echo ""
echo "🎯 Test Summary"
echo "==============="
echo ""
echo "If all tests passed ✅, your deployment is ready!"
echo ""
echo "🚀 To start your agents:"
echo ""

# Show commands for server-only agents first
counter=1
for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    if [ "$mode" = "server" ]; then
        echo "Terminal $counter - Start $agent_id (server-only):"
        echo "ssh -i \"$SSH_KEY\" ${SSH_USER}@${ip}"
        echo "cd $REPO_NAME && source venv/bin/activate"
        echo "python3 interactive_agent_demo.py $agent_id --server-only"
        echo ""
        ((counter++))
    fi
done

# Then show commands for interactive agents
for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    if [ "$mode" = "interactive" ]; then
        echo "Terminal $counter - Start $agent_id (interactive):"
        echo "ssh -i \"$SSH_KEY\" ${SSH_USER}@${ip}"
        echo "cd $REPO_NAME && source venv/bin/activate"
        echo "python3 interactive_agent_demo.py $agent_id"
        echo ""
        ((counter++))
    fi
done

echo "💬 Test A2A communication in any interactive agent terminal:"
echo "@other_agent_id your message here"
echo ""
echo "🔧 If tests failed ❌, check:"
echo "- .env files are properly configured with real API keys"
echo "- MongoDB URI is correct and accessible"
ports=()
for instance in "${INSTANCES[@]}"; do
    IFS=':' read -r ip agent_id port mode <<< "$instance"
    ports+=("$port")
done
echo "- Security groups allow inbound TCP on ports: ${ports[*]}"
echo "- All instances have internet access"