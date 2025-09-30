#!/usr/bin/env python3
"""
BACKWARD COMPATIBILITY MODULE

This module provides backward compatibility for code that imports from the old agent_bridge.py.
All functionality now uses the new modular architecture but maintains the same API.

DEPRECATED: This module is provided for backward compatibility only.
Please update your imports to use the new modular structure:

OLD:
    from nanda_adapter.core.agent_bridge import AgentBridge, call_claude, lookup_agent

NEW:
    from nanda_adapter.core.modular_agent_bridge import ModularAgentBridge
    from nanda_adapter.core.claude_integration import call_claude
    from nanda_adapter.core.registry import lookup_agent
"""

# Import all functions from modular components to maintain compatibility
from .modular_agent_bridge import ModularAgentBridge as AgentBridge, start_modular_agent_bridge
from .claude_integration import (
    call_claude, call_claude_direct, improve_message, get_agent_id,
    message_improver, register_message_improver, get_message_improver, 
    list_message_improvers, default_claude_improver,
    IMPROVE_MESSAGES, ANTHROPIC_API_KEY
)
from .registry import (
    get_registry_url, register_with_registry, lookup_agent, list_registered_agents
)
from .logging_utils import log_message, get_log_directory
from .mcp_integration import (
    get_mcp_server_url, form_mcp_server_url, run_mcp_query, handle_mcp_command
)
from .communication import send_to_terminal, send_to_ui_client
from .a2a_messaging import (
    send_to_agent, handle_external_message, A2AMessage, A2AMessageEnvelope,
    A2AMessageHandler, MessageDirection, MessageType
)

# Backward compatibility aliases
message_improvement_decorators = {}

def start_agent_bridge():
    """Backward compatibility function - use start_modular_agent_bridge instead"""
    import warnings
    warnings.warn(
        "start_agent_bridge() is deprecated. Use start_modular_agent_bridge() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return start_modular_agent_bridge()

# Compatibility for the old main execution pattern
if __name__ == "__main__":
    start_modular_agent_bridge()