#!/usr/bin/env python3
"""
MCP Registry - MongoDB-based registry for MCP servers

This module provides registry functionality for MCP (Model Context Protocol) servers,
allowing agents to discover and connect to MCP servers dynamically.
"""

import os
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
import json
import logging

logger = logging.getLogger(__name__)

class MCPRegistry:
    """
    MongoDB-based registry for MCP servers.
    
    Stores MCP server configurations including:
    - Server name and qualified name
    - Endpoint URL  
    - Configuration details
    - Registry provider (smithery, etc.)
    """
    
    def __init__(self, mongodb_uri: str, database_name: str = "nanda", collection_name: str = "mcp_servers"):
        """
        Initialize MCP registry.
        
        Args:
            mongodb_uri: MongoDB connection string
            database_name: Database name (default: "nanda")
            collection_name: Collection name (default: "mcp_servers")
        """
        self.mongodb_uri = mongodb_uri
        self.database_name = database_name
        self.collection_name = collection_name
        self._client = None
        self._db = None
        self._collection = None
        
        # Establish connection immediately
        self._connect()
        
    @property
    def collection(self):
        """Get the MongoDB collection, ensuring connection is established."""
        if not self._collection:
            self._connect()
        return self._collection
        
    def _connect(self) -> bool:
        """
        Connect to MongoDB.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not self._client:
                # MongoDB Atlas connection with TLS configuration
                self._client = MongoClient(
                    self.mongodb_uri,
                    tls=True,
                    tlsAllowInvalidCertificates=True,  # Allow invalid certificates for dev
                    connectTimeoutMS=30000,
                    serverSelectionTimeoutMS=30000
                )
                self._db = self._client[self.database_name]
                self._collection = self._db[self.collection_name]
                
                # Test connection
                self._client.admin.command('ping')
                logger.info(f"✅ Connected to MCP registry: {self.database_name}.{self.collection_name}")
                return True
                
        except ConnectionFailure as e:
            logger.error(f"❌ Failed to connect to MCP registry: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error connecting to MCP registry: {e}")
            return False
            
        return True
    
    def register_server(self, server_name: str, qualified_name: str, endpoint: str, 
                       config: Dict[str, Any], registry_provider: str = "default") -> bool:
        """
        Register an MCP server in the registry.
        
        Args:
            server_name: Simple server name (e.g., "nanda-payments")
            qualified_name: Fully qualified name (e.g., "@nanda/payments-mcp")
            endpoint: Server endpoint URL
            config: Server configuration dictionary
            registry_provider: Registry provider name (e.g., "smithery")
            
        Returns:
            True if registration successful, False otherwise
        """
        if not self._connect():
            return False
            
        try:
            server_doc = {
                "server_name": server_name,
                "qualified_name": qualified_name,
                "endpoint": endpoint,
                "config": config,
                "registry_provider": registry_provider,
                "active": True
            }
            
            # Use upsert to update existing or create new
            result = self._collection.replace_one(
                {"qualified_name": qualified_name},
                server_doc,
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                logger.info(f"✅ Registered MCP server: {qualified_name} → {endpoint}")
                return True
            else:
                logger.warning(f"⚠️  No changes made when registering: {qualified_name}")
                return False
                
        except PyMongoError as e:
            logger.error(f"❌ Error registering MCP server {qualified_name}: {e}")
            return False
    
    def lookup_server(self, registry_provider: str, server_name: str) -> Optional[dict]:
        """
        Look up a specific MCP server configuration.
        
        Args:
            registry_provider: The registry provider (e.g., "nanda", "smithery")
            server_name: The server name (e.g., "payments", "weather")
            
        Returns:
            Server configuration dict or None if not found
        """
        if not self._connect():
            return None
            
        try:
            result = self._collection.find_one({
                "registry_provider": registry_provider,
                "server_name": server_name
            })
            
            if result:
                # Remove MongoDB _id from result
                result.pop('_id', None)
                
            return result
            
        except Exception as e:
            print(f"Error looking up MCP server {registry_provider}:{server_name}: {e}")
            return None

    def lookup_server_by_name(self, server_name: str) -> Optional[dict]:
        """
        Look up a MCP server by name only (fallback when registry provider not found).
        
        Args:
            server_name: The server name (e.g., "payments", "weather")
            
        Returns:
            Server configuration dict or None if not found
        """
        if not self._connect():
            return None
            
        try:
            result = self._collection.find_one({
                "server_name": server_name
            })
            
            if result:
                # Remove MongoDB _id from result
                result.pop('_id', None)
                
            return result
            
        except Exception as e:
            print(f"Error looking up MCP server by name {server_name}: {e}")
            return None
    
    def lookup_server_by_name(self, server_name: str) -> Optional[Dict[str, Any]]:
        """
        Look up an MCP server by simple server name.
        
        Args:
            server_name: Simple server name (e.g., "nanda-payments")
            
        Returns:
            Server configuration dict if found, None otherwise
        """
        if not self._connect():
            return None
            
        try:
            query = {
                "server_name": server_name,
                "active": True
            }
            
            result = self._collection.find_one(query)
            
            if result:
                logger.info(f"✅ Found MCP server by name: {server_name}")
                # Remove MongoDB internal fields
                result.pop('_id', None)
                return result
            else:
                logger.info(f"❌ MCP server not found by name: {server_name}")
                return None
                
        except PyMongoError as e:
            logger.error(f"❌ Error looking up MCP server by name {server_name}: {e}")
            return None
    
    def list_servers(self, registry_provider: Optional[str] = None) -> List[dict]:
        """
        List all MCP servers in the registry.
        
        Args:
            registry_provider: Optional filter by registry provider
            
        Returns:
            List of server configuration dicts
        """
        if not self._connect():
            return []
            
        try:
            query = {"active": True}
            if registry_provider:
                query["registry_provider"] = registry_provider
                
            results = list(self._collection.find(query))
            
            # Remove MongoDB _id from results
            for result in results:
                result.pop('_id', None)
                
            return results
            
        except Exception as e:
            print(f"Error listing MCP servers: {e}")
            return []
    
    def unregister_server(self, qualified_name: str) -> bool:
        """
        Unregister an MCP server (mark as inactive).
        
        Args:
            qualified_name: Qualified name of server to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        if not self._connect():
            return False
            
        try:
            result = self._collection.update_one(
                {"qualified_name": qualified_name},
                {"$set": {"active": False}}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Unregistered MCP server: {qualified_name}")
                return True
            else:
                logger.info(f"⚠️  MCP server not found for unregistration: {qualified_name}")
                return False
                
        except PyMongoError as e:
            logger.error(f"❌ Error unregistering MCP server {qualified_name}: {e}")
            return False
    
    def close(self):
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._collection = None
            logger.info("✅ Closed MCP registry connection")


def create_mcp_registry() -> Optional[MCPRegistry]:
    """
    Create MCP registry instance from environment variables.
    
    Returns:
        MCPRegistry instance if configuration available, None otherwise
    """
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        logger.warning("⚠️  MONGODB_URI not set, MCP registry unavailable")
        return None
        
    database_name = os.getenv("MONGODB_DATABASE", "nanda")
    collection_name = os.getenv("MCP_COLLECTION", "mcp_servers")
    
    return MCPRegistry(mongodb_uri, database_name, collection_name)


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create registry
    registry = create_mcp_registry()
    if not registry:
        print("❌ Could not create MCP registry")
        exit(1)
    
    # Example: Register a server
    success = registry.register_server(
        server_name="nanda-payments",
        qualified_name="@nanda/payments-mcp",
        endpoint="https://mcp.nanda.ai/payments",
        config={"version": "1.0", "features": ["payments", "invoices"]},
        registry_provider="nanda"
    )
    print(f"Registration success: {success}")
    
    # Example: Look up server
    server = registry.lookup_server("nanda", "@nanda/payments-mcp")
    if server:
        print(f"Found server: {server}")
    
    # Example: List all servers
    servers = registry.list_servers()
    print(f"Total servers: {len(servers)}")
    
    # Close connection
    registry.close()