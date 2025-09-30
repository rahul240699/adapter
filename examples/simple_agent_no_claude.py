#!/usr/bin/env python3
"""
Simple Agent Without Claude.

Demonstrates SimpleNANDA with custom improvement logic,
no Claude API key required.

This example shows how to create agents that work completely
offline with custom message processing logic.

Usage:
    python examples/simple_agent_no_claude.py
"""

import sys
from pathlib import Path

# Ensure local nanda_adapter is used
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nanda_adapter.simple import SimpleNANDA


def uppercase_improver(text: str) -> str:
    """Simple message transformer - converts to uppercase."""
    return text.upper()


def pirate_improver(text: str) -> str:
    """Transform messages to pirate speak."""
    replacements = {
        "hello": "ahoy",
        "hi": "ahoy",
        "yes": "aye",
        "no": "nay",
        "you": "ye",
        "your": "yer",
        "my": "me",
        "friend": "matey",
        "is": "be",
        "are": "be",
    }

    result = text
    for old, new in replacements.items():
        # Case insensitive replacement
        import re
        result = re.sub(re.escape(old), new, result, flags=re.IGNORECASE)

    return result + ", arrr!"


def main():
    print("=" * 60)
    print("Simple Agent - No Claude Required")
    print("=" * 60)
    print("\nThis agent uses custom improvement logic (pirate speak)")
    print("No ANTHROPIC_API_KEY needed!\n")

    # Create agent with custom logic, no Claude
    agent = SimpleNANDA(
        agent_id="simple_agent",
        host="localhost:6000",
        improvement_logic=pirate_improver,
        require_anthropic=False  # No Claude needed!
    )

    print("\nTry sending:")
    print("  curl -X POST http://localhost:6000/a2a \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"role\":\"user\",\"content\":{\"type\":\"text\",\"text\":\"Hello friend!\"},\"conversation_id\":\"test\"}'")
    print()

    agent.start()


if __name__ == "__main__":
    main()