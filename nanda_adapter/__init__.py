#!/usr/bin/env python3
"""
NANDA Agent Framework - Customizable AI Agent Communication System

This package provides a framework for creating customizable AI agents with pluggable
message improvement logic, built on top of the python_a2a communication framework.

Note: v2.0 refactor in progress. Old v1.x imports preserved for backward compatibility.
"""

__version__ = "2.0.0-dev"
__author__ = "NANDA Team"
__email__ = "support@nanda.ai"

# v1.x backward compatibility imports (only if dependencies available)
try:
    from .core.nanda import NANDA
    from .core.agent_bridge import (
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
    # New v2.0 code should import directly:
    #   from nanda_adapter.core.registry import LocalRegistry
    #   from nanda_adapter.simple import SimpleNANDA  (when available)
    __all__ = []