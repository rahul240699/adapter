#!/usr/bin/env python3
"""
Debug script to help troubleshoot agent ID issues in A2A communication.
"""
import os
import sys

# Add the nanda_adapter to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nanda_adapter'))

def debug_agent_configuration():
    """Debug agent configuration and environment variables"""
    print("🔍 NANDA Agent Configuration Debug")
    print("=" * 50)
    
    # Check environment variables
    print("\n📋 Environment Variables:")
    important_vars = [
        'AGENT_ID', 'PORT', 'TERMINAL_PORT', 'PUBLIC_URL', 'API_URL',
        'ANTHROPIC_API_KEY', 'IMPROVE_MESSAGES', 'UI_MODE', 'UI_CLIENT_URL'
    ]
    
    for var in important_vars:
        value = os.getenv(var, 'NOT SET')
        # Mask sensitive values
        if 'KEY' in var and value != 'NOT SET':
            masked_value = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
            print(f"  {var}: {masked_value}")
        else:
            print(f"  {var}: {value}")
    
    # Test modular imports
    print("\n🔧 Testing Modular Imports:")
    try:
        from nanda_adapter.core.claude_integration import get_agent_id
        from nanda_adapter.core.modular_agent_bridge import ModularAgentBridge
        from nanda_adapter.core.a2a_messaging import A2AMessageHandler
        from nanda_adapter.core.command_handler import CommandHandler
        print("  ✅ All modular imports successful")
        
        # Test agent ID retrieval
        agent_id = get_agent_id()
        print(f"  🆔 Agent ID from get_agent_id(): {agent_id}")
        
        # Test bridge initialization
        bridge = ModularAgentBridge()
        print(f"  🌉 Bridge agent ID: {bridge.agent_id}")
        print(f"  📨 A2A handler agent ID: {bridge.a2a_handler.agent_id}")
        print(f"  ⚡ Command handler agent ID: {bridge.command_handler.agent_id}")
        
        # Check if they match
        if bridge.agent_id == bridge.a2a_handler.agent_id == bridge.command_handler.agent_id:
            print("  ✅ All agent IDs match correctly")
        else:
            print("  ❌ Agent ID mismatch detected!")
            
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False
    
    print("\n🌐 Network Configuration:")
    public_url = os.getenv("PUBLIC_URL")
    api_url = os.getenv("API_URL")
    if public_url:
        print(f"  Public URL: {public_url}")
        print(f"  API URL: {api_url}")
        
        # Test registry lookup
        try:
            from nanda_adapter.core.registry import lookup_agent, get_registry_url
            registry_url = get_registry_url()
            print(f"  Registry URL: {registry_url}")
            
            # Try to look up this agent
            agent_url = lookup_agent(agent_id)
            if agent_url:
                print(f"  ✅ Agent {agent_id} found in registry: {agent_url}")
            else:
                print(f"  ❌ Agent {agent_id} not found in registry")
                
        except Exception as e:
            print(f"  ❌ Registry lookup error: {e}")
    else:
        print("  ❌ No PUBLIC_URL set - agent will not be registered")
    
    print("\n💡 Recommendations:")
    if os.getenv("AGENT_ID") == "default" or not os.getenv("AGENT_ID"):
        print("  🔸 Set unique AGENT_ID environment variable (e.g., 'rahulsohandani')")
    if not os.getenv("PUBLIC_URL"):
        print("  🔸 Set PUBLIC_URL for agent registration")
    if not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "your key":
        print("  🔸 Set valid ANTHROPIC_API_KEY")
    
    return True

if __name__ == "__main__":
    debug_agent_configuration()