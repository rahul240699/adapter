#!/usr/bin/env python3
"""
Interactive @agent routing demo.

This creates a simple chat interface where you can test @agent routing:
- Type regular messages to chat with the agent
- Type @agent_b message to route to agent_b (improved by Claude)
- Type 'quit' to exit

Usage:
    python3 interactive_agent_demo.py agent_a
"""

import os
import sys
import argparse
import threading
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from nanda_adapter.core.env_loader import load_env_file, get_anthropic_api_key
load_env_file()

from nanda_adapter.simple import SimpleNANDA

def create_claude_improver():
    """Create a Claude-based message improver for @agent routing"""
    def improve_message(text: str) -> str:
        from nanda_adapter.core.claude_integration import call_claude
        
        print(f"🧠 Improving message with Claude...")
        improved = call_claude(
            prompt=f"Improve this message to be more professional and clear while keeping the same meaning: '{text}'. Make it suitable for inter-agent communication.",
            additional_context="This message will be sent to another agent for assistance",
            conversation_id="message-improvement",
            current_path="",
            agent_id="message_improver"
        )
        
        return improved if improved else text
    
    return improve_message

def main():
    parser = argparse.ArgumentParser(description="Interactive @agent routing demo")
    parser.add_argument("agent_id", help="Agent ID to run (e.g., agent_a, agent_b, agent_c, etc.)")
    parser.add_argument("--server-only", action="store_true", help="Run as server only (no chat interface)")
    parser.add_argument("--service-charge", type=int, default=0, help="Service charge in NP per request (0=free, >0=expert agent)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for troubleshooting")
    
    args = parser.parse_args()
    
    # Enable debug logging if requested
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        print("🔍 Debug logging enabled")
    
    # Enable verbose output for troubleshooting
    if args.verbose:
        print("🔊 Verbose mode enabled - detailed output will be shown")
        import logging
        logging.basicConfig(level=logging.INFO)
    
    # Default port mapping (can be overridden by environment)
    default_port_map = {
        "agent_a": 6001,
        "agent_b": 6002,
        "agent_c": 6003,
        "agent_d": 6004,
        "agent_e": 6005,
    }
    
    # Get default port or auto-assign based on agent_id
    def get_default_port(agent_id):
        if agent_id in default_port_map:
            return default_port_map[agent_id]
        # Auto-assign port based on agent name hash for consistency
        import hashlib
        hash_obj = hashlib.md5(agent_id.encode())
        # Generate port in range 6001-6999
        return 6001 + (int(hash_obj.hexdigest(), 16) % 999)
    
    print(f"🚀 Starting interactive {args.agent_id} with @agent routing")
    print("=" * 60)
    
    # Environment and dependency validation
    print(f"🔍 Environment validation:")
    print(f"   - Python version: {sys.version}")
    print(f"   - Working directory: {os.getcwd()}")
    print(f"   - Arguments: {vars(args)}")
    
    # Check critical dependencies
    try:
        from python_a2a import A2AServer, run_server
        print(f"   ✅ python_a2a library available")
    except ImportError as e:
        print(f"   ❌ python_a2a library missing: {e}")
        return
    
    try:
        from anthropic import Anthropic
        print(f"   ✅ anthropic library available")
    except ImportError as e:
        print(f"   ❌ anthropic library missing: {e}")
        return
    
    # Check environment variables
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        print(f"   ✅ ANTHROPIC_API_KEY set: {api_key[:10]}...")
    else:
        print(f"   ❌ ANTHROPIC_API_KEY not set")
        return
    
    # Get port from environment or use default
    port = int(os.getenv('PORT', get_default_port(args.agent_id)))
    
    # Set PORT environment variable so SimpleNANDA uses the correct port
    os.environ['PORT'] = str(port)
    
    # Determine service charge based on mode and command line args
    if args.service_charge > 0:
        # Use command line specified service charge
        final_service_charge = args.service_charge
        print(f"💰 Using specified service charge: {final_service_charge} NP per request")
    elif args.server_only:
        # Server-only agents default to expert mode requiring payment
        final_service_charge = 10  # 10 NP per request for expert agents
        print(f"💰 Server-only mode: Default expert charge {final_service_charge} NP per request")
    else:
        # Interactive mode defaults to free
        final_service_charge = 0
        print(f"🆓 Interactive mode: Free agent (0 NP per request)")
    
    print(f"\n🔧 Creating {args.agent_id} with service charge: {final_service_charge} NP")
    
    # Create agent with Claude-based message improvement
    # SimpleNANDA will handle network configuration through environment variables
    try:
        agent = SimpleNANDA(
            agent_id=args.agent_id,
            improvement_logic=create_claude_improver(),
            require_anthropic=True,
            service_charge=final_service_charge
        )
        print(f"✅ {args.agent_id} created successfully!")
    except Exception as e:
        print(f"❌ Failed to create agent {args.agent_id}: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n✅ {args.agent_id} initialized!")
    print(f"🌐 Public URL: {agent.agent_url}")
    print(f"💰 Service charge: {agent.service_charge} NP per request")
    
    # If server-only mode, just start the server
    if args.server_only:
        print(f"\n🔧 Running in server-only mode")
        print(f"📡 {args.agent_id} server will listen for A2A messages...")
        print(f"🌐 Binding to: {agent.internal_host}:{agent.port}")
        print(f"🔗 Public URL: {agent.public_url}")
        print(f"� Logs will be written to: {agent.logger.agent_log_dir}")
        print(f"�🛑 Press Ctrl+C to stop")
        print("=" * 60)
        
        try:
            print(f"🚀 Starting A2A server for {args.agent_id}...")
            
            # Add startup validation
            if args.verbose:
                print(f"   - Agent ID: {args.agent_id}")
                print(f"   - Service charge: {final_service_charge} NP")
                print(f"   - Internal host: {agent.internal_host}")
                print(f"   - Port: {agent.port}")
                print(f"   - Public URL: {agent.public_url}")
                print(f"   - Registry type: {type(agent.registry).__name__}")
                print(f"   - Log directory: {agent.logger.agent_log_dir}")
            
            # Test dependencies before starting
            try:
                from python_a2a import run_server
                if args.verbose:
                    print(f"   - python_a2a.run_server available ✅")
            except ImportError as e:
                print(f"   - python_a2a.run_server missing ❌: {e}")
                raise
            
            print(f"🔥 Server starting now...")
            agent.start()  # This blocks and runs the HTTP server
            
        except KeyboardInterrupt:
            print(f"\n\n👋 {args.agent_id} server shutting down...")
        except Exception as e:
            print(f"\n❌ Server failed to start: {e}")
            import traceback
            traceback.print_exc()
            
            # Additional debugging info
            if args.verbose:
                print(f"\n🔍 Debug Information:")
                print(f"   - Python path: {sys.path}")
                print(f"   - Current working directory: {os.getcwd()}")
                print(f"   - Environment variables:")
                for key in ['ANTHROPIC_API_KEY', 'PORT', 'INTERNAL_HOST', 'PUBLIC_URL']:
                    value = os.getenv(key, 'NOT_SET')
                    if key == 'ANTHROPIC_API_KEY' and value != 'NOT_SET':
                        value = value[:10] + '...'
                    print(f"     {key}: {value}")
        finally:
            print(f"✅ {args.agent_id} server stopped")
        return
    
    # Start agent server in background thread for interactive mode
    def start_server():
        try:
            print(f"🔄 Background server thread starting for {args.agent_id}...")
            agent.start()
        except KeyboardInterrupt:
            print(f"🛑 Background server thread interrupted for {args.agent_id}")
        except Exception as e:
            print(f"❌ Background server thread failed for {args.agent_id}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🔄 Starting {args.agent_id} server in background thread...")
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Give server time to start
    print(f"⏳ Waiting for {args.agent_id} server to initialize...")
    time.sleep(3)  # Increased from 2 to 3 seconds
    
    # Check if server thread is still alive (indication it started successfully)
    if server_thread.is_alive():
        print(f"✅ {args.agent_id} server thread is running")
    else:
        print(f"❌ {args.agent_id} server thread died during startup")
    
    # Show registry status
    print(f"\n📋 Available agents in registry:")
    for agent_info in agent.registry.list():
        status = "🟢 YOU" if agent_info['agent_id'] == args.agent_id else "🔵 OTHER"
        print(f"  • {agent_info['agent_id']}: {agent_info['agent_url']} {status}")
    
    print(f"\n💡 How to use:")
    print(f"  • Regular message: 'Hello, how are you?'")  
    print(f"  • Route to other agent: '@agent_b help me with this problem'")
    print(f"  • Exit: 'quit' or Ctrl+C")
    print("=" * 60)
    
    conversation_id = "interactive-session"
    
    try:
        while True:
            user_input = input(f"\n[{args.agent_id}] You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if not user_input:
                continue
            
            print(f"\n🔄 Processing...")
            
            # Route the message through the agent's router
            response = agent.router.route(user_input, conversation_id)
            
            print(f"🤖 {response}")
            
            # If it was an @agent message, show what happened behind the scenes
            if user_input.startswith('@'):
                target = user_input.split(' ')[0][1:]  # Remove @ and get agent name
                print(f"\n� Behind the scenes:")
                print(f"  • {args.agent_id} detected @{target} routing")
                print(f"  • Message improved with Claude")
                print(f"  • Sent to {target} and got response ↑")
                
    except KeyboardInterrupt:
        print(f"\n\n👋 {args.agent_id} shutting down...")
    
    print("✅ Demo completed!")

if __name__ == "__main__":
    main()