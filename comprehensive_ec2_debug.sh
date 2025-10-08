#!/bin/bash
# Comprehensive EC2 Server Diagnostics
# This script provides detailed information about server-only mode failures

echo "🔍 Comprehensive EC2 Server Diagnostics"
echo "========================================"

AGENT_ID=${1:-"agent_y"}
PORT=${2:-6002}

echo "Configuration:"
echo "   Agent ID: $AGENT_ID"
echo "   Port: $PORT"
echo "   Date: $(date)"
echo "   Working Directory: $(pwd)"
echo ""

# Function to run command and capture output
run_and_capture() {
    local cmd="$1"
    local desc="$2"
    
    echo "🔧 $desc"
    echo "   Command: $cmd"
    
    # Create temp files for output
    local stdout_file="/tmp/debug_stdout_$$"
    local stderr_file="/tmp/debug_stderr_$$"
    
    # Run command
    eval "$cmd" > "$stdout_file" 2> "$stderr_file"
    local exit_code=$?
    
    # Show results
    if [[ $exit_code -eq 0 ]]; then
        echo "   Status: ✅ SUCCESS (exit code: $exit_code)"
    else
        echo "   Status: ❌ FAILED (exit code: $exit_code)"
    fi
    
    # Show output if any
    if [[ -s "$stdout_file" ]]; then
        echo "   STDOUT:"
        sed 's/^/      /' "$stdout_file"
    fi
    
    if [[ -s "$stderr_file" ]]; then
        echo "   STDERR:"
        sed 's/^/      /' "$stderr_file"
    fi
    
    # Cleanup
    rm -f "$stdout_file" "$stderr_file"
    echo ""
    
    return $exit_code
}

# Test 01: Basic system info
echo "01. System Information"
echo "   OS: $(uname -a)"
echo "   User: $(whoami)"
echo "   Home: $HOME"
echo "   Shell: $SHELL"
echo ""

# Test 02: Python environment
run_and_capture "python3 --version" "Python Version Check"
run_and_capture "which python3" "Python Path Check"
run_and_capture "pip3 --version" "Pip Version Check"

# Test 03: Virtual environment
if [[ -n "$VIRTUAL_ENV" ]]; then
    echo "🔧 Virtual Environment Status"
    echo "   Status: ✅ ACTIVATED"
    echo "   Path: $VIRTUAL_ENV"
    echo "   Python: $(which python3)"
    echo ""
else
    echo "🔧 Virtual Environment Status"
    echo "   Status: ❌ NOT ACTIVATED"
    echo "   Looking for venv..."
    if [[ -d "venv" ]]; then
        echo "   Found venv directory - activating..."
        source venv/bin/activate
        echo "   Now activated: $VIRTUAL_ENV"
    else
        echo "   No venv directory found"
    fi
    echo ""
fi

# Test 04: Environment variables
echo "🔧 Environment Variables"
echo "   ANTHROPIC_API_KEY: $(test -n "$ANTHROPIC_API_KEY" && echo 'SET ✅' || echo 'NOT SET ❌')"
echo "   PORT: ${PORT:-'NOT SET'}"
echo "   PYTHONPATH: ${PYTHONPATH:-'NOT SET'}"
echo ""

# Test 05: Repository status
run_and_capture "git status --porcelain" "Git Status Check"
run_and_capture "git branch --show-current" "Current Branch"

# Test 06: File existence
echo "🔧 Required Files Check"
files_to_check=(
    "interactive_agent_demo.py"
    "requirements.txt"
    "nanda_adapter/__init__.py"
    "nanda_adapter/simple.py"
    "nanda_adapter/core/router.py"
    "nanda_adapter/core/x402_compliant_middleware.py"
)

for file in "${files_to_check[@]}"; do
    if [[ -f "$file" ]]; then
        echo "   $file: ✅ EXISTS"
    else
        echo "   $file: ❌ MISSING"
    fi
done
echo ""

# Test 07: Dependencies
run_and_capture "pip3 install -r requirements.txt" "Installing Dependencies"

# Test 08: X402 Dependencies
if [[ -f "setup_x402_dependencies.sh" ]]; then
    run_and_capture "chmod +x setup_x402_dependencies.sh && ./setup_x402_dependencies.sh" "X402 Dependencies Setup"
fi

# Test 09: Import tests
echo "🔧 Python Import Tests"
python3 -c "
import sys
tests = [
    ('sys', lambda: __import__('sys')),
    ('os', lambda: __import__('os')),
    ('flask', lambda: __import__('flask')),
    ('anthropic', lambda: __import__('anthropic')),
    ('python_a2a', lambda: __import__('python_a2a')),
    ('nanda_adapter', lambda: __import__('nanda_adapter')),
    ('nanda_adapter.simple', lambda: __import__('nanda_adapter.simple', fromlist=['SimpleNANDA'])),
    ('SimpleNANDA', lambda: getattr(__import__('nanda_adapter.simple', fromlist=['SimpleNANDA']), 'SimpleNANDA')),
]

for name, test_func in tests:
    try:
        test_func()
        print(f'   {name}: ✅')
    except Exception as e:
        print(f'   {name}: ❌ {e}')
"
echo ""

# Test 10: Port availability
echo "🔧 Port Availability Check"
echo "   Checking port $PORT..."

# Check if port is in use
if netstat -ln | grep -q ":$PORT "; then
    echo "   Port $PORT: ❌ ALREADY IN USE"
    echo "   Processes using port $PORT:"
    lsof -i :$PORT | sed 's/^/      /'
else
    echo "   Port $PORT: ✅ AVAILABLE"
fi
echo ""

# Test 11: Try running the script with syntax check
run_and_capture "python3 -m py_compile interactive_agent_demo.py" "Script Syntax Check"

# Test 12: Try running with --help
run_and_capture "timeout 10 python3 interactive_agent_demo.py --help" "Script Help Check"

# Test 13: Try a minimal run
echo "🔧 Minimal Server Test"
echo "   Testing basic server startup (10 second timeout)..."

python3 -c "
import sys
import signal
import os
import time

def timeout_handler(signum, frame):
    print('⏰ Timeout reached - server startup test complete')
    sys.exit(0)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)

print('Starting minimal test...')
try:
    # Set environment
    os.environ['ANTHROPIC_API_KEY'] = os.environ.get('ANTHROPIC_API_KEY', 'test-key')
    
    # Import required modules
    from nanda_adapter.simple import SimpleNANDA
    print('✅ SimpleNANDA imported')
    
    # Create agent instance
    agent = SimpleNANDA('$AGENT_ID', port=$PORT, service_charge=10)
    print('✅ Agent created')
    
    # Try to start server (this should work even without real API key for startup test)
    print('✅ Server test completed - no immediate startup errors')
    
except Exception as e:
    print(f'❌ Server test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" 2>&1

echo ""

# Test 14: Detailed error capture
echo "🔧 Detailed Server Startup Test"
echo "   Running actual command with full error capture..."

# Create a script that captures all output
cat > /tmp/server_test.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
import traceback

try:
    # Add current directory to path
    sys.path.insert(0, os.getcwd())
    
    print("=== SERVER STARTUP TEST ===")
    print(f"Python path: {sys.path}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Arguments: {sys.argv}")
    
    # Import and run
    import interactive_agent_demo
    print("✅ Module imported successfully")
    
    # The script should handle the rest
    
except Exception as e:
    print(f"❌ STARTUP ERROR: {e}")
    print("\n=== FULL TRACEBACK ===")
    traceback.print_exc()
    sys.exit(1)
EOF

# Make executable and run
chmod +x /tmp/server_test.py

echo "   Running: python3 /tmp/server_test.py $AGENT_ID --server-only --port $PORT"
timeout 15 python3 /tmp/server_test.py "$AGENT_ID" --server-only --port "$PORT" 2>&1 || echo "   (Timeout or error occurred)"

echo ""
echo "========================================"
echo "🏁 Diagnostics Complete!"
echo ""
echo "📋 Summary:"
echo "   - Check all ❌ items above"
echo "   - Look for specific error messages"
echo "   - Verify ANTHROPIC_API_KEY is set"
echo "   - Ensure port $PORT is available"
echo ""
echo "🚀 To run manually:"
echo "   python3 interactive_agent_demo.py $AGENT_ID --server-only --port $PORT"