#!/usr/bin/env python3
"""
NANDA Agent Framework - Core Components

This module contains the core components of the NANDA agent framework.

Note: v2.0 refactor in progress. Old v1.x imports preserved for backward compatibility.
New modules (registry.py, protocol.py, router.py) are standalone and don't need imports here.
"""

# v1.x backward compatibility imports (only if modules exist)
try:
    from .nanda import NANDA
    from .agent_bridge import (
        AgentBridge,
        message_improver,
        register_message_improver,
        get_message_improver,
        list_message_improvers
    )

    __all__ = [
        "NANDA",
        "AgentBridge",
        "message_improver",
        "register_message_improver",
        "get_message_improver",
        "list_message_improvers"
    ]
except ImportError:
    # During v2.0 refactor, old modules may have missing dependencies
    # New code should import directly: from nanda_adapter.core.registry import LocalRegistry
    __all__ = []