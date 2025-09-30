# Migration Guide: From Monolithic to Modular NANDA Architecture

## Overview

The NANDA adapter has been refactored from a monolithic `agent_bridge.py` to a modular architecture. This guide helps users migrate their code to use the new structure.

## Quick Migration

### ✅ What Still Works (No Changes Required)

-   **NANDA class usage**: No changes needed
-   **Example scripts**: All examples continue to work
-   **Environment variables**: Same configuration
-   **API compatibility**: Same method signatures

```python
# This continues to work unchanged
from nanda_adapter import NANDA

def my_improver(text):
    return f"Improved: {text}"

nanda = NANDA(my_improver)
nanda.start_server()
```

### 🔄 Recommended Updates (New Imports)

#### Main Classes

```python
# OLD
from nanda_adapter.core.agent_bridge import AgentBridge

# NEW
from nanda_adapter.core.modular_agent_bridge import ModularAgentBridge
# OR for backward compatibility:
from nanda_adapter import AgentBridge  # Now an alias to ModularAgentBridge
```

#### Individual Functions

```python
# OLD - Everything from agent_bridge
from nanda_adapter.core.agent_bridge import call_claude, lookup_agent, log_message

# NEW - Import from specific modules
from nanda_adapter.core.claude_integration import call_claude
from nanda_adapter.core.registry import lookup_agent
from nanda_adapter.core.logging_utils import log_message
```

## Detailed Module Mapping

### Registry Functions

```python
# OLD
from nanda_adapter.core.agent_bridge import (
    get_registry_url, register_with_registry,
    lookup_agent, list_registered_agents
)

# NEW
from nanda_adapter.core.registry import (
    get_registry_url, register_with_registry,
    lookup_agent, list_registered_agents
)
```

### Claude Integration

```python
# OLD
from nanda_adapter.core.agent_bridge import (
    call_claude, call_claude_direct, improve_message,
    message_improver, register_message_improver
)

# NEW
from nanda_adapter.core.claude_integration import (
    call_claude, call_claude_direct, improve_message,
    message_improver, register_message_improver
)
```

### MCP Integration

```python
# OLD
from nanda_adapter.core.agent_bridge import (
    get_mcp_server_url, run_mcp_query, handle_mcp_command
)

# NEW
from nanda_adapter.core.mcp_integration import (
    get_mcp_server_url, run_mcp_query, handle_mcp_command
)
```

### A2A Messaging

```python
# OLD
from nanda_adapter.core.agent_bridge import send_to_agent, handle_external_message

# NEW
from nanda_adapter.core.a2a_messaging import (
    A2AMessageHandler, A2AMessage, A2AMessageEnvelope
)
# The send_to_agent function is now part of A2AMessageHandler
```

### Communication

```python
# OLD
from nanda_adapter.core.agent_bridge import send_to_terminal, send_to_ui_client

# NEW
from nanda_adapter.core.communication import send_to_terminal, send_to_ui_client
```

### Logging

```python
# OLD
from nanda_adapter.core.agent_bridge import log_message

# NEW
from nanda_adapter.core.logging_utils import log_message, get_log_directory
```

## Benefits of Migration

### 1. **Better Organization**

-   Clear separation of concerns
-   Easier to find specific functionality
-   Reduced coupling between components

### 2. **Enhanced Features**

-   **Intelligent A2A Communication**: Agents now generate smart replies instead of simple acknowledgments
-   **Structured Message Handling**: Dataclass-based message formats
-   **Improved Error Handling**: Module-specific error handling

### 3. **Development Benefits**

-   **Testing**: Each module can be tested independently
-   **Debugging**: Easier to isolate issues
-   **Extension**: Add new features without affecting other components

## Backward Compatibility

### Compatibility Layer

A compatibility layer (`agent_bridge_compat.py`) provides all old imports:

```python
# This works but shows deprecation warnings
from nanda_adapter.core.agent_bridge import AgentBridge, call_claude
```

### Gradual Migration Strategy

1. **Phase 1**: Keep using old imports (they still work)
2. **Phase 2**: Update imports to new modular structure
3. **Phase 3**: Take advantage of new features (enhanced A2A, structured messaging)

## New Features Available

### Enhanced A2A Communication

```python
# NEW: Intelligent agent-to-agent replies
from nanda_adapter.core.a2a_messaging import A2AMessageHandler

handler = A2AMessageHandler()
# Agents now generate intelligent contextual replies instead of simple "Message received"
```

### Structured Message Handling

```python
# NEW: Structured message formats
from nanda_adapter.core.a2a_messaging import A2AMessage, MessageType

message = A2AMessage(
    from_agent="sender_id",
    to_agent="receiver_id",
    content="Hello!",
    message_type=MessageType.AGENT_TO_AGENT,
    conversation_id="conv_123"
)
```

### Modular Server Startup

```python
# NEW: Direct modular server startup
from nanda_adapter.core.modular_agent_bridge import start_modular_agent_bridge

# Enhanced server with all modular components
start_modular_agent_bridge()
```

## Testing Your Migration

### 1. Import Test

```python
# Test that all your imports work
from nanda_adapter import NANDA, ModularAgentBridge
from nanda_adapter.core.claude_integration import call_claude
from nanda_adapter.core.registry import lookup_agent

print("✅ Migration successful!")
```

### 2. Functionality Test

```python
# Test that your existing NANDA usage works
def my_improvement(text):
    return f"Enhanced: {text}"

nanda = NANDA(my_improvement)
# Should work exactly as before
```

## Getting Help

If you encounter issues during migration:

1. **Check the backward compatibility**: Old imports should still work
2. **Review error messages**: They'll point to the specific import issues
3. **Use the module mapping**: Follow the NEW import examples above
4. **Test incrementally**: Migrate one module at a time

## Timeline

-   **Now**: Modular architecture available, old imports work with compatibility layer
-   **Future**: Old `agent_bridge.py` will be deprecated
-   **Recommendation**: Start migrating to modular imports for better maintainability

The modular architecture provides the same functionality with better organization and enhanced features! 🚀
