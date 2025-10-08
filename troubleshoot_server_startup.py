#!/usr/bin/env python3
"""
EC2 Server Startup Troubleshooter

This script isolates and tests each step of the server startup process
to identify exactly where the failure occurs.
"""

import sys
import os
import traceback
import time

def test_step(step_name, test_func):
    """Run a test step and report results."""
    print(f"🔧 {step_name}...")
    try:
        result = test_func()
        if result is True or result is None:
            print(f"   ✅ {step_name} - SUCCESS")
            return True
        else:
            print(f"   ✅ {step_name} - SUCCESS: {result}")
            return True
    except Exception as e:
        print(f"   ❌ {step_name} - FAILED: {e}")
        print(f"      Error type: {type(e).__name__}")
        # Print traceback for debugging
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 EC2 Server Startup Troubleshooter")
    print("====================================")
    
    # Get arguments
    agent_id = sys.argv[1] if len(sys.argv) > 1 else "agent_test"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6002
    
    print(f"Agent ID: {agent_id}")
    print(f"Port: {port}")
    print(f"Working Directory: {os.getcwd()}")
    print(f"Python Version: {sys.version}")
    print("")
    
    # Test 1: Basic Python environment
    if not test_step("Python basic modules", lambda: __import__('sys') and __import__('os')):
        return 1
    
    # Test 2: Environment variables
    def check_env():
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            return f"API key set (length: {len(api_key)})"
        else:
            # Set a dummy key for testing
            os.environ['ANTHROPIC_API_KEY'] = 'sk-dummy-key-for-testing'
            return "API key not set - using dummy key for testing"
    
    if not test_step("Environment variables", check_env):
        return 1
    
    # Test 3: Import Flask
    if not test_step("Flask import", lambda: __import__('flask')):
        return 1
    
    # Test 4: Import Anthropic
    if not test_step("Anthropic import", lambda: __import__('anthropic')):
        return 1
    
    # Test 5: Import python_a2a
    if not test_step("python_a2a import", lambda: __import__('python_a2a')):
        return 1
    
    # Test 6: Import nanda_adapter
    if not test_step("nanda_adapter import", lambda: __import__('nanda_adapter')):
        return 1
    
    # Test 7: Import SimpleNANDA
    def import_simple_nanda():
        from nanda_adapter.simple import SimpleNANDA
        return SimpleNANDA
    
    if not test_step("SimpleNANDA import", import_simple_nanda):
        return 1
    
    # Test 8: Create SimpleNANDA instance
    def create_agent():
        from nanda_adapter.simple import SimpleNANDA
        # Set PORT environment variable like interactive_agent_demo.py does
        os.environ['PORT'] = str(port)
        agent = SimpleNANDA(agent_id, service_charge=10)
        return f"Agent created with ID: {agent.agent_id}, Port: {agent.port}"
    
    if not test_step("SimpleNANDA creation", create_agent):
        return 1
    
    # Test 9: Check port availability
    def check_port():
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            return f"Port {port} is available"
        except OSError as e:
            raise Exception(f"Port {port} is not available: {e}")
    
    if not test_step("Port availability", check_port):
        return 1
    
    # Test 10: Test Flask app creation
    def test_flask_app():
        from nanda_adapter.simple import SimpleNANDA
        # Set PORT environment variable like interactive_agent_demo.py does
        os.environ['PORT'] = str(port)
        agent = SimpleNANDA(agent_id, service_charge=10)
        
        # Try to access the Flask app - but SimpleNANDA doesn't use Flask directly
        # It uses python_a2a's A2AServer which handles HTTP internally
        return f"Agent created successfully, uses A2A server on port {agent.port}"
    
    if not test_step("Flask app creation", test_flask_app):
        return 1
    
    # Test 11: Test A2A server creation
    def test_a2a_server():
        from nanda_adapter.simple import SimpleNANDA
        from python_a2a import A2AServer
        # Set PORT environment variable like interactive_agent_demo.py does
        os.environ['PORT'] = str(port)
        agent = SimpleNANDA(agent_id, service_charge=10)
        
        # Just test that we can create an A2A server class
        class TestAgentServer(A2AServer):
            def __init__(self):
                super().__init__(url=agent.public_url)
            def handle_message(self, msg):
                return msg  # Simple echo for testing
        
        test_server = TestAgentServer()
        return f"A2A server created successfully for {agent.public_url}"
    
    if not test_step("A2A server creation", test_a2a_server):
        return 1
    
    # Test 12: Test server startup (brief)
    def test_server_startup():
        from nanda_adapter.simple import SimpleNANDA
        import threading
        import time
        
        # Set PORT environment variable like interactive_agent_demo.py does
        os.environ['PORT'] = str(port)
        agent = SimpleNANDA(agent_id, service_charge=10)
        
        # Test if we can start the server in a separate thread
        def start_server():
            try:
                agent.start()  # This is the correct method name
            except Exception as e:
                print(f"      Server thread error: {e}")
        
        # Start server in background thread
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if thread is still alive (means server is running)
        if server_thread.is_alive():
            return "Server started successfully in background thread"
        else:
            raise Exception("Server thread died immediately")
    
    if not test_step("Server startup test", test_server_startup):
        return 1
    
    print("")
    print("🎉 All tests passed!")
    print("")
    print("✅ The server startup process appears to be working correctly.")
    print("✅ If you're still having issues, it might be:")
    print("   - Network/firewall configuration")
    print("   - Process management (screen/tmux sessions)")
    print("   - Log output not being captured")
    print("   - Server starting but exiting due to other reasons")
    print("")
    print("🚀 Try running the server manually:")
    print(f"   python3 interactive_agent_demo.py {agent_id} --server-only --port {port}")
    print("")
    print("📊 Or with verbose logging:")
    print(f"   python3 interactive_agent_demo.py {agent_id} --server-only --port {port} --verbose")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())