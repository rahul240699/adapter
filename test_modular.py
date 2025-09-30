#!/usr/bin/env python3
"""
Test script for the modular agent bridge implementation.
"""
import os
import sys

# Add the nanda_adapter to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nanda_adapter'))

try:
    # Test importing all modules
    print("Testing modular imports...")
    
    from nanda_adapter.core.registry import get_registry_url, lookup_agent
    print("✓ Registry module imported successfully")
    
    from nanda_adapter.core.logging_utils import log_message, get_log_directory
    print("✓ Logging utils module imported successfully")
    
    from nanda_adapter.core.claude_integration import get_agent_id, call_claude, IMPROVE_MESSAGES
    print("✓ Claude integration module imported successfully")
    
    from nanda_adapter.core.mcp_integration import get_mcp_server_url, handle_mcp_command
    print("✓ MCP integration module imported successfully")
    
    from nanda_adapter.core.communication import send_to_terminal, send_to_ui_client
    print("✓ Communication module imported successfully")
    
    from nanda_adapter.core.a2a_messaging import A2AMessageHandler, A2AMessage, A2AMessageEnvelope
    print("✓ A2A messaging module imported successfully")
    
    from nanda_adapter.core.command_handler import CommandHandler
    print("✓ Command handler module imported successfully")
    
    from nanda_adapter.core.modular_agent_bridge import ModularAgentBridge, start_modular_agent_bridge
    print("✓ Modular agent bridge imported successfully")
    
    print("\n🎉 All modular components imported successfully!")
    
    # Test some basic functionality
    print("\nTesting basic functionality...")
    
    # Test environment variables
    agent_id = get_agent_id()
    print(f"Agent ID: {agent_id}")
    
    registry_url = get_registry_url()
    print(f"Registry URL: {registry_url}")
    
    log_dir = get_log_directory()
    print(f"Log directory: {log_dir}")
    
    print(f"Message improvement enabled: {IMPROVE_MESSAGES}")
    
    # Test A2A message parsing
    print("\nTesting A2A message parsing...")
    test_message = "__EXTERNAL_MESSAGE__\n__FROM_AGENT__test_sender\n__TO_AGENT__test_receiver\n__MESSAGE_START__\nHello, this is a test message!\n__MESSAGE_END__"
    envelope = A2AMessageEnvelope.parse(test_message)
    if envelope:
        print(f"✓ Parsed message: {envelope.from_agent} -> {envelope.to_agent}: {envelope.content}")
    else:
        print("✗ Failed to parse test message")
    
    print("\n✅ Modular implementation test completed successfully!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)