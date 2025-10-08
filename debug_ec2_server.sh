#!/bin/bash
# EC2 Server Debug Helper
# This script helps debug server-only mode issues on EC2

echo "🔍 EC2 Server Debug Helper"
echo "========================="

AGENT_ID=${1:-"agent_debug"}

echo "Agent ID: $AGENT_ID"
echo "Working directory: $(pwd)"
echo "Python version: $(python3 --version)"
echo ""

echo "🔧 Testing basic functionality..."

# Test 1: Check if Python can import required modules
echo "1️⃣ Testing Python imports..."
python3 -c "
try:
    import sys
    print('   ✅ sys module')
    import os
    print('   ✅ os module')
    import anthropic
    print('   ✅ anthropic module')
    from python_a2a import A2AServer, run_server
    print('   ✅ python_a2a module')
    from nanda_adapter.simple import SimpleNANDA
    print('   ✅ nanda_adapter.simple module')
    print('   All imports successful!')
except ImportError as e:
    print(f'   ❌ Import error: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Import test failed - check dependencies"
    exit 1
fi

# Test 2: Check environment variables
echo ""
echo "2️⃣ Testing environment variables..."
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "   ❌ ANTHROPIC_API_KEY not set"
    exit 1
else
    echo "   ✅ ANTHROPIC_API_KEY set"
fi

echo "   PORT: ${PORT:-'NOT_SET (will use default)'}"
echo "   INTERNAL_HOST: ${INTERNAL_HOST:-'NOT_SET (will use default)'}"
echo "   PUBLIC_URL: ${PUBLIC_URL:-'NOT_SET (will use auto-detection)'}"

# Test 3: Test the EC2 test script
echo ""
echo "3️⃣ Running comprehensive test..."
python3 test_ec2_server.py $AGENT_ID

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "4️⃣ Starting server with verbose logging..."
    echo "Press Ctrl+C to stop"
    echo ""
    
    # Start the actual server with verbose output
    python3 interactive_agent_demo.py $AGENT_ID --server-only --verbose --service-charge 10
else
    echo ""
    echo "❌ Tests failed - check the output above for issues"
    exit 1
fi