"""
Registry management module for NANDA Agent Bridge.
Handles agent registration, lookup, and registry communication.
"""
import os
import requests
from typing import Optional, List, Dict, Any


def get_registry_url() -> str:
    """Get the registry URL from file or use default"""
    try:
        if os.path.exists("registry_url.txt"):
            with open("registry_url.txt", "r") as f:
                registry_url = f.read().strip()
                print(f"Using registry URL from file: {registry_url}")
                return registry_url
    except Exception as e:
        print(f"Error reading registry URL from file: {e}")
    
    # Default if file doesn't exist
    default_url = "https://chat.nanda-registry.com:6900"
    print(f"Using default registry URL: {default_url}")
    return default_url


def register_with_registry(agent_id: str, agent_url: str, api_url: str) -> bool:
    """Register this agent with the registry"""
    registry_url = get_registry_url()
    try:
        # Add /a2a to the URL during registration
        if not agent_url.endswith('/a2a'):
            agent_url = f"{agent_url}"

        data = {
            "agent_id": agent_id,
            "agent_url": agent_url,
            "api_url": api_url
        }
        print(f"Registering agent {agent_id} with URL {agent_url} at registry {registry_url}...")
        response = requests.post(f"{registry_url}/register", json=data)
        if response.status_code == 200:
            print(f"Agent {agent_id} registered successfully")
            return True
        else:
            print(f"Failed to register agent: {response.text}")
            return False
    except Exception as e:
        print(f"Error registering agent: {e}")
        return False


def lookup_agent(agent_id: str) -> Optional[str]:
    """Look up an agent's URL in the registry"""
    registry_url = get_registry_url()
    try:
        print(f"Looking up agent {agent_id} in registry {registry_url}...")
        response = requests.get(f"{registry_url}/lookup/{agent_id}")
        if response.status_code == 200:
            agent_url = response.json().get("agent_url")
            print(f"Found agent {agent_id} at URL: {agent_url}")
            return agent_url
        print(f"Agent {agent_id} not found in registry")
        return None
    except Exception as e:
        print(f"Error looking up agent {agent_id}: {e}")
        return None


def list_registered_agents() -> Optional[List[Dict[str, Any]]]:
    """Get a list of all registered agents from the registry"""
    registry_url = get_registry_url()
    try:
        print(f"Requesting list of agents from registry {registry_url}...")
        response = requests.get(f"{registry_url}/list")
        if response.status_code == 200:
            agents = response.json()
            return agents
        print(f"Failed to get list of agents from registry")
        return None
    except Exception as e:
        print(f"Error getting list of agents: {e}")
        return None