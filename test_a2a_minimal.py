#!/usr/bin/env python3
"""
Minimal test to isolate the exact python-a2a run_server failure.
"""

import os
import sys
import traceback

def test_minimal_a2a_server():
    """Test the most minimal possible A2A server setup."""
    print("🔬 Minimal A2A Server Test")
    print("=" * 40)
    
    try:
        print("📦 Importing python-a2a...")
        from python_a2a import A2AServer, Message, MessageRole, TextContent, run_server
        print("✅ python-a2a imported successfully")
        
        print("🏗️ Creating minimal A2A server...")
        
        class MinimalServer(A2AServer):
            def __init__(self):
                # Try different URL formats to see what works
                test_urls = [
                    "http://127.0.0.1:6002",
                    "http://localhost:6002", 
                    "http://0.0.0.0:6002",
                    "http://54.226.80.138:6002"
                ]
                
                for url in test_urls:
                    try:
                        print(f"   Trying URL: {url}")
                        super().__init__(url=url)
                        print(f"   ✅ A2AServer created with URL: {url}")
                        self.successful_url = url
                        break
                    except Exception as e:
                        print(f"   ❌ Failed with {url}: {e}")
                        continue
                else:
                    raise Exception("All URL formats failed")

            def handle_message(self, msg: Message) -> Message:
                return Message(
                    role=MessageRole.AGENT,
                    content=TextContent(text="Echo: " + msg.content.text),
                    parent_message_id=msg.message_id,
                    conversation_id=msg.conversation_id
                )
        
        server = MinimalServer()
        print(f"✅ Server created successfully with URL: {server.successful_url}")
        
        print("🚀 Testing run_server with different host configurations...")
        
        # Test different host binding configurations
        host_configs = [
            ("127.0.0.1", 6002),
            ("localhost", 6002),
            ("0.0.0.0", 6002),
        ]
        
        for host, port in host_configs:
            print(f"\n🔧 Testing host={host}, port={port}")
            try:
                # Import Flask to see if we can start it directly
                from flask import Flask
                app = Flask(__name__)
                
                @app.route('/')
                def hello():
                    return "Test Flask server"
                
                print(f"   Flask app created, testing if we can bind to {host}:{port}")
                
                # Try to start Flask briefly to test binding
                import threading
                import time
                import requests
                
                def flask_thread():
                    try:
                        app.run(host=host, port=port, debug=False, use_reloader=False)
                    except Exception as e:
                        print(f"   Flask thread error: {e}")
                
                thread = threading.Thread(target=flask_thread, daemon=True)
                thread.start()
                time.sleep(1)
                
                # Test if Flask server is responsive
                try:
                    test_url = f"http://127.0.0.1:{port}/"
                    response = requests.get(test_url, timeout=1)
                    print(f"   ✅ Flask server responding: {response.status_code}")
                    break  # If Flask works, run_server should work too
                except Exception as e:
                    print(f"   ❌ Flask server not responding: {e}")
                    
            except Exception as e:
                print(f"   ❌ Flask test failed for {host}:{port}: {e}")
                continue
        
        print("\n🚀 Now testing run_server...")
        
        # Try run_server with the configuration that worked for Flask
        try:
            print("   About to call run_server...")
            print("   This will block - if you don't see an error in 3 seconds, it's working!")
            
            # Set a timeout to see if run_server starts
            import signal
            
            def timeout_handler(signum, frame):
                print("   ✅ run_server appears to be working (timeout reached)")
                raise KeyboardInterrupt("Timeout - server is running")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(3)  # 3 second timeout
            
            run_server(server, host="0.0.0.0", port=6002)
            
        except KeyboardInterrupt as e:
            if "Timeout" in str(e):
                print("   ✅ SUCCESS: run_server started successfully!")
                return True
            else:
                print("   🔧 Manual interrupt")
                return True
        except Exception as e:
            print(f"   ❌ run_server failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Critical error: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_minimal_a2a_server()
    sys.exit(0 if success else 1)