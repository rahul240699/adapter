"""
Registry implementations for agent discovery.

This module provides both local file-based and MongoDB-based registries
for agent discovery and registration.
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict
from abc import ABC, abstractmethod

# Optional MongoDB dependency
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, OperationFailure
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False


class RegistryInterface(ABC):
    """Abstract base class for registry implementations"""
    
    @abstractmethod
    def register(self, agent_id: str, agent_url: str, service_charge: int = 0, agent_name: Optional[str] = None) -> bool:
        """Register or update an agent"""
        pass
    
    @abstractmethod
    def lookup(self, agent_id: str) -> Optional[str]:
        """Get agent URL by ID"""
        pass
    
    @abstractmethod
    def list(self) -> List[Dict]:
        """List all registered agents"""
        pass
    
    @abstractmethod
    def unregister(self, agent_id: str) -> bool:
        """Remove agent from registry"""
        pass
    
    @abstractmethod
    def clear(self):
        """Clear all agents"""
        pass


class LocalRegistry(RegistryInterface):
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

    def register(self, agent_id: str, agent_url: str, service_charge: int = 0, agent_name: Optional[str] = None) -> bool:
        """
        Register or update an agent.

        Args:
            agent_id: Unique agent identifier
            agent_url: Full URL to agent (e.g., http://localhost:6000 or http://192.168.1.100:6002)
            service_charge: Points required per request (0 = free, >0 = expert agent)
            agent_name: Human-readable name for the agent (defaults to agent_id)

        Returns:
            True if successful
        """
        now = datetime.now(timezone.utc).isoformat()
        # Default agent_name to agent_id if not provided
        agent_name = agent_name or agent_id

        if agent_id in self.agents:
            # Update existing agent
            self.agents[agent_id]["agent_url"] = agent_url
            self.agents[agent_id]["last_seen"] = now
            self.agents[agent_id]["service_charge"] = service_charge
            self.agents[agent_id]["agent_name"] = agent_name
        else:
            # Register new agent
            self.agents[agent_id] = {
                "agent_url": agent_url,
                "registered_at": now,
                "last_seen": now,
                "service_charge": service_charge,
                "agent_name": agent_name
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

    def get_agent_info(self, agent_id: str) -> Optional[Dict]:
        """
        Get complete agent information including service charge.

        Args:
            agent_id: Agent identifier to look up

        Returns:
            Complete agent record or None if not found
        """
        return self.agents.get(agent_id)

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


class MongoRegistry(RegistryInterface):
    """MongoDB-based registry for distributed agent discovery"""

    def __init__(self, mongodb_uri: str, database: str = "nanda", collection: str = "agents"):
        """
        Initialize MongoDB registry.

        Args:
            mongodb_uri: MongoDB connection URI
            database: Database name (default: "nanda")
            collection: Collection name (default: "agents")
            
        Raises:
            ImportError: If pymongo is not installed
            ConnectionFailure: If cannot connect to MongoDB
        """
        if not MONGODB_AVAILABLE:
            raise ImportError(
                "pymongo is required for MongoDB registry. "
                "Install with: pip install pymongo"
            )
        
        self.mongodb_uri = mongodb_uri
        self.database_name = database
        self.collection_name = collection
        
        # Initialize MongoDB client with TLS configuration
        self.client = MongoClient(
            mongodb_uri,
            serverSelectionTimeoutMS=5000,
            tls=True,
            tlsAllowInvalidCertificates=True  # Allow invalid certificates for dev
        )
        
        # Test connection
        try:
            self.client.admin.command('ping')
            print(f"✓ Connected to MongoDB: {database}.{collection}")
        except ConnectionFailure as e:
            raise ConnectionFailure(f"Failed to connect to MongoDB: {e}")
        
        self.db = self.client[database]
        self.collection = self.db[collection]
        
        # Create index on agent_id for faster lookups
        self.collection.create_index("agent_id", unique=True)

    def register(self, agent_id: str, agent_url: str, service_charge: int = 0, agent_name: Optional[str] = None) -> bool:
        """
        Register or update an agent in MongoDB.

        Args:
            agent_id: Unique agent identifier
            agent_url: Full URL to agent
            service_charge: Points required per request (0 = free, >0 = expert agent)
            agent_name: Human-readable name for the agent (defaults to agent_id)

        Returns:
            True if successful

        Raises:
            OperationFailure: If MongoDB operation fails
        """
        try:
            now = datetime.now(timezone.utc)
            # Default agent_name to agent_id if not provided
            agent_name = agent_name or agent_id
            
            # Use upsert to update existing or create new
            result = self.collection.update_one(
                {"agent_id": agent_id},
                {
                    "$set": {
                        "agent_url": agent_url,
                        "last_seen": now,
                        "service_charge": service_charge,
                        "agent_name": agent_name
                    },
                    "$setOnInsert": {
                        "registered_at": now
                    }
                },
                upsert=True
            )
            
            if result.upserted_id:
                print(f"✓ Registered new agent '{agent_id}' at {agent_url}")
            else:
                print(f"✓ Updated agent '{agent_id}' at {agent_url}")
            
            return True
            
        except OperationFailure as e:
            print(f"✗ Failed to register agent '{agent_id}': {e}")
            return False

    def lookup(self, agent_id: str) -> Optional[str]:
        """
        Get agent URL by ID from MongoDB.

        Args:
            agent_id: Agent identifier to look up

        Returns:
            Full URL to agent or None if not found
        """
        try:
            agent = self.collection.find_one({"agent_id": agent_id})
            if agent:
                # Update last_seen timestamp
                self.collection.update_one(
                    {"agent_id": agent_id},
                    {"$set": {"last_seen": datetime.now(timezone.utc)}}
                )
                return agent["agent_url"]
            return None
            
        except OperationFailure as e:
            print(f"✗ Failed to lookup agent '{agent_id}': {e}")
            return None

    def get_agent_info(self, agent_id: str) -> Optional[Dict]:
        """
        Get complete agent information including service charge.

        Args:
            agent_id: Agent identifier to look up

        Returns:
            Complete agent record or None if not found
        """
        try:
            agent = self.collection.find_one({"agent_id": agent_id}, {"_id": 0})
            if agent:
                # Update last_seen timestamp
                self.collection.update_one(
                    {"agent_id": agent_id},
                    {"$set": {"last_seen": datetime.now(timezone.utc)}}
                )
            return agent
            
        except OperationFailure as e:
            print(f"✗ Failed to get agent info '{agent_id}': {e}")
            return None

    def list(self) -> List[Dict]:
        """
        List all registered agents from MongoDB.

        Returns:
            List of agent records with agent_id and metadata
        """
        try:
            agents = list(self.collection.find({}, {"_id": 0}))  # Exclude MongoDB _id field
            return agents
            
        except OperationFailure as e:
            print(f"✗ Failed to list agents: {e}")
            return []

    def unregister(self, agent_id: str) -> bool:
        """
        Remove agent from MongoDB registry.

        Args:
            agent_id: Agent identifier to remove

        Returns:
            True if agent was removed, False if not found
        """
        try:
            result = self.collection.delete_one({"agent_id": agent_id})
            if result.deleted_count > 0:
                print(f"✓ Unregistered agent '{agent_id}'")
                return True
            else:
                print(f"⚠ Agent '{agent_id}' not found for unregistration")
                return False
                
        except OperationFailure as e:
            print(f"✗ Failed to unregister agent '{agent_id}': {e}")
            return False

    def clear(self):
        """
        Clear all agents from MongoDB registry.

        Warning: This removes all registered agents from the registry.
        """
        try:
            result = self.collection.delete_many({})
            print(f"✓ Cleared {result.deleted_count} agents from registry")
            
        except OperationFailure as e:
            print(f"✗ Failed to clear registry: {e}")

    def close(self):
        """Close MongoDB connection"""
        if hasattr(self, 'client'):
            self.client.close()
            print("✓ MongoDB connection closed")

    def __del__(self):
        """Cleanup MongoDB connection on object destruction"""
        self.close()


def create_registry(mongodb_uri: str = None, use_local: bool = None) -> RegistryInterface:
    """
    Factory function to create appropriate registry based on configuration.
    
    Args:
        mongodb_uri: MongoDB connection URI (if None, reads from env)
        use_local: Force local registry (if None, reads from env)
        
    Returns:
        Registry instance (LocalRegistry or MongoRegistry)
    """
    from .env_loader import load_env_vars
    
    # Load environment variables if not provided
    if mongodb_uri is None or use_local is None:
        env_vars = load_env_vars()
        if mongodb_uri is None:
            mongodb_uri = env_vars.get("MONGODB_URI")
        if use_local is None:
            # Check both environment variable and current os.environ (for runtime changes)
            use_local_env = env_vars.get("USE_LOCAL_REGISTRY", "false").lower() in ("true", "1", "yes")
            use_local_current = os.getenv("USE_LOCAL_REGISTRY", "false").lower() in ("true", "1", "yes") 
            use_local = use_local_env or use_local_current
    
    # Decide which registry to use - prioritize use_local flag
    if use_local:
        print("🗂 Using LocalRegistry (file-based)")
        return LocalRegistry()
    elif mongodb_uri and not ("username:password" in mongodb_uri):
        print("🗂 Using MongoRegistry (MongoDB-based)")
        database = os.getenv("MONGODB_DATABASE", "nanda")
        collection = os.getenv("MONGODB_COLLECTION", "agents")
        return MongoRegistry(mongodb_uri, database, collection)
    else:
        print("🗂 Using LocalRegistry (file-based) - MongoDB URI not configured or is placeholder")
        return LocalRegistry()