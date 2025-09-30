#!/usr/bin/env python3
"""
Example usage of the modular NANDA agent bridge.
Shows how to start an agent with the new modular architecture.
"""
import os

# Set environment variables for the agent
os.environ['AGENT_ID'] = 'example_agent'
os.environ['PORT'] = '6000'
os.environ['TERMINAL_PORT'] = '6010'
os.environ['IMPROVE_MESSAGES'] = 'true'
os.environ['UI_MODE'] = 'false'  # Set to 'true' for UI mode

# Optional: Set API keys
# os.environ['ANTHROPIC_API_KEY'] = 'your_anthropic_key'
# os.environ['SMITHERY_API_KEY'] = 'your_smithery_key'

# Optional: Set registry and URLs for networking
# os.environ['PUBLIC_URL'] = 'https://your-agent-url.com'
# os.environ['API_URL'] = 'https://your-api-url.com'
# os.environ['UI_CLIENT_URL'] = 'https://your-ui-client.com/webhook'

if __name__ == "__main__":
    print("Starting modular NANDA agent...")
    print(f"Agent ID: {os.getenv('AGENT_ID')}")
    print(f"Port: {os.getenv('PORT')}")
    print(f"Message improvement: {os.getenv('IMPROVE_MESSAGES')}")
    print(f"UI Mode: {os.getenv('UI_MODE')}")
    
    # Import and start the modular agent bridge
    from nanda_adapter.core.modular_agent_bridge import start_modular_agent_bridge
    
    try:
        start_modular_agent_bridge()
    except KeyboardInterrupt:
        print("\n👋 Agent stopped by user")
    except Exception as e:
        print(f"❌ Error starting agent: {e}")