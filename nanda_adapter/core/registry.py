"""
Local file-based registry for agent discovery.

This module implements a simple JSON file-based registry for local development,
replacing the need for external HTTPS registries or MongoDB.
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict


class LocalRegistry:
    """File-based registry for local agent discovery"""

    def __init__(self, registry_file: str = ".nanda_registry.json"):
        """
        Initialize local registry.

        Args:
            registry_file: Path to registry JSON file (default: .nanda_registry.json)
        """
        self.registry_file = registry_file
        self.agents = self._load()

    def _load(self) -> Dict:
        """Load registry from file"""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If file is corrupted, start fresh
                return {}
        return {}

    def _save(self):
        """Save registry to file"""
        with open(self.registry_file, 'w') as f:
            json.dump(self.agents, f, indent=2, default=str)

    def register(self, agent_id: str, agent_url: str) -> bool:
        """
        Register or update an agent.

        Args:
            agent_id: Unique agent identifier
            agent_url: Full URL to agent (e.g., http://localhost:6000 or http://192.168.1.100:6002)

        Returns:
            True if successful
        """
        now = datetime.now(timezone.utc).isoformat()

        if agent_id in self.agents:
            # Update existing agent
            self.agents[agent_id]["agent_url"] = agent_url
            self.agents[agent_id]["last_seen"] = now
        else:
            # Register new agent
            self.agents[agent_id] = {
                "agent_url": agent_url,
                "registered_at": now,
                "last_seen": now
            }

        self._save()
        return True

    def lookup(self, agent_id: str) -> Optional[str]:
        """
        Get agent URL by ID.

        Args:
            agent_id: Agent identifier to look up

        Returns:
            Full URL to agent (e.g., http://localhost:6000) or None if not found
        """
        agent = self.agents.get(agent_id)
        return agent["agent_url"] if agent else None

    def list(self) -> List[Dict]:
        """
        List all registered agents.

        Returns:
            List of agent records with agent_id and metadata
        """
        return [
            {"agent_id": aid, **data}
            for aid, data in self.agents.items()
        ]

    def unregister(self, agent_id: str) -> bool:
        """
        Remove agent from registry.

        Args:
            agent_id: Agent identifier to remove

        Returns:
            True if agent was removed, False if not found
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            self._save()
            return True
        return False

    def clear(self):
        """
        Clear all agents (for testing/reset).

        Warning: This removes all registered agents from the registry.
        """
        self.agents = {}
        self._save()