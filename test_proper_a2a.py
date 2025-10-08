#!/usr/bin/env python3
"""
Proper test of python-a2a run_server without port conflicts.
"""

import os
import sys
import traceback
import threading
import time

def test_proper_a2a_server():
    """Test A2A server properly without port conflicts."""
    print("🔬 Proper A2A Server Test")
    print("=" * 40)
    
    try:
        print("📦 Importing python-a2a...")
        from python_a2a import A2AServer, Message, MessageRole, TextContent, run_server
        print("✅ python-a2a imported successfully")
        
        print("🏗️ Creating A2A server...")
        
        class TestServer(A2AServer):
            def __init__(self):
                # Use localhost URL - this should work
                super().__init__(url="http://localhost:6002")
                print("✅ A2AServer created with URL: http://localhost:6002")

            def handle_message(self, msg: Message) -> Message:
                print(f"📨 Received: {msg.content.text}")
                return Message(
                    role=MessageRole.AGENT,
                    content=TextContent(text="Echo: " + msg.content.text),
                    parent_message_id=msg.message_id,
                    conversation_id=msg.conversation_id
                )
        
        server = TestServer()
        print("✅ Server instance created")
        
        print("🚀 Testing run_server directly...")
        
        # Capture any stdout/stderr from run_server
        import subprocess
        import tempfile
        
        # Create a simple script that runs the server
        test_script = """
import sys
sys.path.insert(0, '/home/ubuntu/adapter')
import os
os.environ['ANTHROPIC_API_KEY'] = 'dummy-key'

from python_a2a import A2AServer, Message, MessageRole, TextContent, run_server

class TestServer(A2AServer):
    def __init__(self):
        super().__init__(url="http://localhost:6002")
    
    def handle_message(self, msg):
        return Message(
            role=MessageRole.AGENT,
            content=TextContent(text="Echo: " + msg.content.text),
            parent_message_id=msg.message_id,
            conversation_id=msg.conversation_id
        )

server = TestServer()
print("Starting run_server...")
try:
    run_server(server, host="0.0.0.0", port=6002)
except Exception as e:
    print(f"run_server failed: {e}")
    import traceback
    traceback.print_exc()
"""
        
        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_script_path = f.name
        
        print(f"   Created test script: {temp_script_path}")
        
        # Run the script with timeout to see what happens
        try:
            print("   Running server script with 5 second timeout...")
            result = subprocess.run([
                'python3', temp_script_path
            ], capture_output=True, text=True, timeout=5)
            
            print("   ❌ run_server exited unexpectedly")
            print(f"   Return code: {result.returncode}")
            print(f"   STDOUT: {result.stdout}")
            print(f"   STDERR: {result.stderr}")
            
        except subprocess.TimeoutExpired:
            print("   ✅ run_server is running (timeout reached)")
            print("   This means the server started successfully!")
            
        except Exception as e:
            print(f"   ❌ Script execution failed: {e}")
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_script_path)
            except:
                pass
        
        # Also try direct inspection of what run_server does
        print("\n🔍 Inspecting run_server function...")
        import inspect
        
        try:
            # Get the source code of run_server
            source = inspect.getsource(run_server)
            print("   run_server source code (first 10 lines):")
            for i, line in enumerate(source.split('\n')[:10]):
                print(f"     {i+1}: {line}")
                
        except Exception as e:
            print(f"   Cannot inspect source: {e}")
        
        # Check what run_server actually calls
        print("\n🔍 Checking run_server module details...")
        print(f"   run_server.__module__: {run_server.__module__}")
        print(f"   run_server.__name__: {run_server.__name__}")
        
        # Try to import the module directly
        try:
            import python_a2a.server.http
            print(f"   python_a2a.server.http available")
            
            # Check if there are other functions we should use
            http_module_attrs = [attr for attr in dir(python_a2a.server.http) 
                               if not attr.startswith('_')]
            print(f"   Available functions: {http_module_attrs}")
            
        except Exception as e:
            print(f"   Cannot import http module: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_proper_a2a_server()
    sys.exit(0 if success else 1)