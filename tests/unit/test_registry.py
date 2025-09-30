"""
Unit tests for LocalRegistry.

Tests file-based registry operations including registration, lookup,
listing, unregistration, and persistence.
"""

import pytest
import os
import json
from nanda_adapter.core.registry import LocalRegistry


@pytest.fixture
def temp_registry_file(tmp_path):
    """Provide a temporary registry file path"""
    return str(tmp_path / "test_registry.json")


@pytest.fixture
def registry(temp_registry_file):
    """Provide a fresh LocalRegistry instance"""
    return LocalRegistry(temp_registry_file)


def test_register_agent(registry):
    """Test registering a new agent"""
    result = registry.register("agent_a", "http://localhost:6000")
    assert result == True
    assert registry.lookup("agent_a") == "http://localhost:6000"


def test_register_updates_existing(registry):
    """Test that re-registering updates the agent URL"""
    registry.register("agent_a", "http://localhost:6000")
    registry.register("agent_a", "http://localhost:6001")  # Update port
    assert registry.lookup("agent_a") == "http://localhost:6001"


def test_register_remote_host(registry):
    """Test registering with remote host IP"""
    result = registry.register("agent_b", "http://192.168.1.100:6002")
    assert result == True
    assert registry.lookup("agent_b") == "http://192.168.1.100:6002"


def test_register_persists(temp_registry_file):
    """Test that registration persists to file"""
    registry1 = LocalRegistry(temp_registry_file)
    registry1.register("agent_a", "http://localhost:6000")

    # Create new registry instance (reload from file)
    registry2 = LocalRegistry(temp_registry_file)
    assert registry2.lookup("agent_a") == "http://localhost:6000"


def test_register_creates_metadata(registry, temp_registry_file):
    """Test that registration creates registered_at and last_seen timestamps"""
    registry.register("agent_a", "http://localhost:6000")

    # Read file directly
    with open(temp_registry_file, 'r') as f:
        data = json.load(f)

    assert "agent_a" in data
    assert "agent_url" in data["agent_a"]
    assert "registered_at" in data["agent_a"]
    assert "last_seen" in data["agent_a"]


def test_lookup_nonexistent(registry):
    """Test looking up an agent that doesn't exist"""
    assert registry.lookup("nonexistent") is None


def test_list_agents(registry):
    """Test listing all registered agents"""
    registry.register("agent_a", "http://localhost:6000")
    registry.register("agent_b", "http://localhost:6002")

    agents = registry.list()
    assert len(agents) == 2

    agent_ids = [a["agent_id"] for a in agents]
    assert "agent_a" in agent_ids
    assert "agent_b" in agent_ids


def test_list_empty(registry):
    """Test listing when no agents registered"""
    agents = registry.list()
    assert len(agents) == 0
    assert agents == []


def test_unregister(registry):
    """Test unregistering an agent"""
    registry.register("agent_a", "http://localhost:6000")
    assert registry.lookup("agent_a") is not None

    result = registry.unregister("agent_a")
    assert result == True
    assert registry.lookup("agent_a") is None


def test_unregister_nonexistent(registry):
    """Test unregistering an agent that doesn't exist"""
    result = registry.unregister("nonexistent")
    assert result == False


def test_unregister_persists(temp_registry_file):
    """Test that unregistration persists to file"""
    registry1 = LocalRegistry(temp_registry_file)
    registry1.register("agent_a", "http://localhost:6000")
    registry1.unregister("agent_a")

    # Reload from file
    registry2 = LocalRegistry(temp_registry_file)
    assert registry2.lookup("agent_a") is None


def test_clear(registry):
    """Test clearing all agents"""
    registry.register("agent_a", "http://localhost:6000")
    registry.register("agent_b", "http://localhost:6002")
    assert len(registry.list()) == 2

    registry.clear()
    assert len(registry.list()) == 0


def test_clear_persists(temp_registry_file):
    """Test that clear persists to file"""
    registry1 = LocalRegistry(temp_registry_file)
    registry1.register("agent_a", "http://localhost:6000")
    registry1.clear()

    # Reload from file
    registry2 = LocalRegistry(temp_registry_file)
    assert len(registry2.list()) == 0


def test_corrupted_file_handling(temp_registry_file):
    """Test that registry handles corrupted JSON files gracefully"""
    # Write invalid JSON
    with open(temp_registry_file, 'w') as f:
        f.write("{ invalid json }")

    # Should not crash, should start fresh
    registry = LocalRegistry(temp_registry_file)
    assert len(registry.list()) == 0


def test_multiple_agents(registry):
    """Test registering and managing multiple agents"""
    agents = [
        ("agent_a", "http://localhost:6000"),
        ("agent_b", "http://localhost:6002"),
        ("agent_c", "http://192.168.1.100:6004"),
        ("agent_d", "http://192.168.1.101:6000"),
    ]

    for agent_id, url in agents:
        registry.register(agent_id, url)

    assert len(registry.list()) == 4

    for agent_id, url in agents:
        assert registry.lookup(agent_id) == url


def test_file_format(registry, temp_registry_file):
    """Test that registry file is properly formatted JSON"""
    registry.register("agent_a", "http://localhost:6000")

    # Read and parse file
    with open(temp_registry_file, 'r') as f:
        data = json.load(f)

    # Verify structure
    assert isinstance(data, dict)
    assert "agent_a" in data
    assert isinstance(data["agent_a"], dict)
    assert data["agent_a"]["agent_url"] == "http://localhost:6000"