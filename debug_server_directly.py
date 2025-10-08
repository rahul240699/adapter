#!/usr/bin/env python3
"""
Direct server startup test to isolate the exact issue.
"""

import os
import sys
import traceback
import time
import threading

def test_direct_server_startup():
    """Test server startup directly to see the exact error."""
    print("🔧 Direct Server Startup Test")
    print("=" * 40)
    
    # Set environment like interactive_agent_demo.py does
    os.environ['PORT'] = '6002'
    os.environ['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', 'sk-dummy-key-for-testing')
    
    try:
        print("📦 Importing required modules...")
        from nanda_adapter.simple import SimpleNANDA
        from python_a2a import run_server
        print("✅ Imports successful")
        
        print("🏗️ Creating SimpleNANDA agent...")
        agent = SimpleNANDA('agent_y', service_charge=10)
        print("✅ Agent created successfully")
        
        print("🏗️ Creating A2A server class...")
        from python_a2a import A2AServer, Message, MessageRole, TextContent
        
        class TestAgentServer(A2AServer):
            def __init__(self, parent):
                print(f"🔧 Initializing A2AServer with URL: {parent.public_url}")
                super().__init__(url=parent.public_url)
                self.parent = parent
                print("✅ A2AServer initialized")

            def handle_message(self, msg: Message) -> Message:
                print(f"📨 Received message: {msg.content.text}")
                return Message(
                    role=MessageRole.AGENT,
                    content=TextContent(text=f"Echo: {msg.content.text}"),
                    parent_message_id=msg.message_id,
                    conversation_id=msg.conversation_id
                )
        
        print("🏗️ Creating server instance...")
        server = TestAgentServer(agent)
        print("✅ Server instance created")
        
        print(f"🚀 Starting server on {agent.internal_host}:{agent.port}")
        print(f"🔗 Public URL: {agent.public_url}")
        
        # Try to start server with detailed error handling
        def server_thread():
            try:
                print("🔥 About to call run_server...")
                run_server(server, host=agent.internal_host, port=agent.port)
                print("🔥 run_server returned (this shouldn't happen)")
            except Exception as e:
                print(f"❌ run_server failed: {e}")
                print(f"❌ Error type: {type(e).__name__}")
                traceback.print_exc()
                return False
            return True
        
        # Start in background thread to catch immediate failures
        thread = threading.Thread(target=server_thread, daemon=True)
        print("🔧 Starting server thread...")
        thread.start()
        
        # Give it time to start or fail
        print("⏳ Waiting 3 seconds to see if server starts...")
        time.sleep(3)
        
        if thread.is_alive():
            print("✅ Server thread is running!")
            print("🎉 Server startup successful")
            return True
        else:
            print("❌ Server thread died")
            print("❌ Server startup failed")
            return False
            
    except Exception as e:
        print(f"❌ Critical error: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_server_startup()
    sys.exit(0 if success else 1)