#!/usr/bin/env python3
"""
Two-Agent Local Communication Example.

Demonstrates SimpleNANDA with two agents communicating locally
without external registries, SSL, or complex setup.

Usage:
    Terminal 1: python examples/two_agents_local.py agent_a
    Terminal 2: python examples/two_agents_local.py agent_b
    Terminal 3: curl -X POST http://localhost:6000/a2a -H "Content-Type: application/json" \\
                -d '{"role":"user","content":{"type":"text","text":"@agent_b What is 2+2?"},"conversation_id":"test"}'
"""

import sys
import os
from pathlib import Path

# Ensure local nanda_adapter is used
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nanda_adapter.simple import SimpleNANDA
from nanda_adapter.core.registry import LocalRegistry


def main():
    if len(sys.argv) < 2:
        print("Usage: python two_agents_local.py <agent_id>")
        print("Example: python two_agents_local.py agent_a")
        sys.exit(1)

    agent_id = sys.argv[1]

    # Determine port based on agent ID
    if agent_id == "agent_a":
        host = "localhost:6000"
    elif agent_id == "agent_b":
        host = "localhost:6002"
    else:
        host = f"localhost:{6000 + hash(agent_id) % 1000}"

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("=" * 60)
        print("ERROR: ANTHROPIC_API_KEY not set")
        print("=" * 60)
        print("\nPlease set your API key:")
        print("  export ANTHROPIC_API_KEY=sk-your-key-here")
        print("\nOr run without Claude:")
        print("  python examples/simple_agent_no_claude.py")
        print("=" * 60)
        sys.exit(1)

    # Create shared registry in project root (not examples dir)
    registry_path = PROJECT_ROOT / ".nanda_registry.json"
    registry = LocalRegistry(str(registry_path))

    # Create and start agent
    print("=" * 60)
    print(f"Starting {agent_id} with Claude integration")
    print("=" * 60)
    print(f"Shared registry: {registry_path}")

    agent = SimpleNANDA(agent_id, host, registry=registry)
    agent.start()


if __name__ == "__main__":
    main()