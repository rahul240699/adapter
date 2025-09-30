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
    parser.add_argument("agent_id", choices=["agent_a", "agent_b"], help="Agent to run")
    parser.add_argument("--server-only", action="store_true", help="Run as server only (no chat interface)")
    
    args = parser.parse_args()
    
    port_map = {
        "agent_a": 6001,
        "agent_b": 6002
    }
    
    print(f"🚀 Starting interactive {args.agent_id} with @agent routing")
    print("=" * 60)
    
    # Create agent with Claude-based message improvement
    agent = SimpleNANDA(
        agent_id=args.agent_id,
        host=f"localhost:{port_map[args.agent_id]}",
        improvement_logic=create_claude_improver(),
        require_anthropic=True
    )
    
    print(f"\n✅ {args.agent_id} ready!")
    print(f"🌐 Running on: http://localhost:{port_map[args.agent_id]}")
    
    # If server-only mode, just start the server
    if args.server_only:
        print(f"\n🔧 Running in server-only mode")
        print(f"📡 {args.agent_id} server listening for A2A messages...")
        print(f"🛑 Press Ctrl+C to stop")
        print("=" * 60)
        try:
            agent.start()  # This blocks and runs the HTTP server
        except KeyboardInterrupt:
            print(f"\n\n👋 {args.agent_id} server shutting down...")
        return
    
    # Start agent server in background thread for interactive mode
    def start_server():
        try:
            agent.start()
        except KeyboardInterrupt:
            pass
    
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Give server time to start
    print(f"\n⏳ Starting {args.agent_id} server...")
    time.sleep(2)
    
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