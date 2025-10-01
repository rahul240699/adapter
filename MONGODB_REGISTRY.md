# MongoDB Registry Configuration

This document explains how to configure and use the MongoDB registry for distributed agent discovery in the NANDA adapter.

## Overview

The NANDA adapter supports two registry types:

-   **LocalRegistry**: File-based registry using `.nanda_registry.json` (default for local development)
-   **MongoRegistry**: MongoDB-based registry for distributed/production environments

## MongoDB Setup

### 1. Create MongoDB Cluster

You can use:

-   **MongoDB Atlas** (cloud): https://cloud.mongodb.com/
-   **Local MongoDB**: Install MongoDB locally
-   **Docker MongoDB**: Run MongoDB in a container

### 2. Get Connection String

For MongoDB Atlas:

1. Create a cluster
2. Create a database user
3. Whitelist your IP address
4. Get the connection string (looks like):

```
mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority
```

### 3. Configure Environment Variables

Update your `.env` file:

```bash
# MongoDB Configuration
MONGODB_URI=mongo_url
MONGODB_DATABASE=nanda
MONGODB_COLLECTION=agents

# Set to false to use MongoDB registry
USE_LOCAL_REGISTRY=false
```

## Configuration Options

| Environment Variable | Description               | Default              |
| -------------------- | ------------------------- | -------------------- |
| `MONGODB_URI`        | MongoDB connection string | Required for MongoDB |
| `MONGODB_DATABASE`   | Database name             | `nanda`              |
| `MONGODB_COLLECTION` | Collection name           | `agents`             |
| `USE_LOCAL_REGISTRY` | Force local registry      | `false`              |

## Testing MongoDB Registry

Run the test script to verify your MongoDB configuration:

```bash
python test_mongo_registry.py
```

This will:

-   Test MongoDB connection
-   Register test agents
-   Perform lookups
-   List all agents
-   Clean up test data

## Registry Auto-Detection

The system automatically chooses the registry type:

```python
from nanda_adapter.simple import SimpleNANDA

# Automatically uses MongoDB if MONGODB_URI is set and USE_LOCAL_REGISTRY=false
agent = SimpleNANDA('my_agent', 'localhost:6000')
```

## Manual Registry Selection

You can also manually specify the registry:

```python
from nanda_adapter.core.registry import MongoRegistry, LocalRegistry

# Force MongoDB registry
mongo_registry = MongoRegistry(
    mongodb_uri="mongodb+srv://...",
    database="nanda",
    collection="agents"
)
agent = SimpleNANDA('my_agent', 'localhost:6000', registry=mongo_registry)

# Force local registry
local_registry = LocalRegistry()
agent = SimpleNANDA('my_agent', 'localhost:6000', registry=local_registry)
```

## MongoDB Document Structure

Each agent is stored as a MongoDB document:

```json
{
    "agent_id": "agent_a",
    "agent_url": "http://localhost:6000",
    "registered_at": "2025-10-01T10:30:00.000Z",
    "last_seen": "2025-10-01T10:35:00.000Z"
}
```

## Benefits of MongoDB Registry

### Distributed Agents

-   Agents can be on different machines/networks
-   Centralized discovery service
-   Real-time agent availability

### Scalability

-   Handles thousands of agents
-   Fast lookups with indexing
-   Automatic failover with replica sets

### Monitoring

-   Track agent registration times
-   Monitor last seen timestamps
-   Query agent statistics

## Fallback Behavior

If MongoDB connection fails:

-   The system will show connection errors
-   You can fallback to LocalRegistry by setting `USE_LOCAL_REGISTRY=true`
-   Existing code continues to work without changes

## Security Considerations

### Connection Security

-   Use `mongodb+srv://` for encrypted connections
-   Enable authentication on your MongoDB cluster
-   Whitelist only necessary IP addresses

### Environment Variables

-   Never commit `.env` files to git
-   Use strong passwords for MongoDB users
-   Consider using MongoDB Atlas for managed security

### Network Security

-   Use VPC/private networks when possible
-   Enable MongoDB access logs
-   Monitor connection patterns

## Troubleshooting

### Connection Issues

```bash
# Test MongoDB connection
python -c "from pymongo import MongoClient; print(MongoClient('your-uri').admin.command('ping'))"
```

### Common Errors

**Error**: `ImportError: pymongo is required`
**Solution**: Install MongoDB driver

```bash
pip install pymongo
```

**Error**: `ConnectionFailure: Failed to connect`
**Solutions**:

-   Check your MongoDB URI
-   Verify network connectivity
-   Check IP whitelist in MongoDB Atlas
-   Verify credentials

**Error**: `OperationFailure: Authentication failed`
**Solutions**:

-   Check username/password in URI
-   Verify database user permissions
-   Check database name in URI

### Debug Mode

Enable debug logging in `.env`:

```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

This will show detailed MongoDB operation logs.

## Migration from Local to MongoDB

To migrate from LocalRegistry to MongoRegistry:

1. **Backup existing registry**:

```bash
cp .nanda_registry.json .nanda_registry.json.backup
```

2. **Set up MongoDB** (see setup section above)

3. **Update .env file**:

```bash
USE_LOCAL_REGISTRY=false
MONGODB_URI=your-mongodb-connection-string
```

4. **Test the connection**:

```bash
python test_mongo_registry.py
```

5. **Migrate existing agents** (if needed):

```python
from nanda_adapter.core.registry import LocalRegistry, MongoRegistry
import json

# Load from local
local = LocalRegistry()
local_agents = local.list()

# Save to MongoDB
mongo = MongoRegistry("your-mongodb-uri")
for agent in local_agents:
    mongo.register(agent['agent_id'], agent['agent_url'])
```

## Production Recommendations

### MongoDB Atlas Setup

-   Use M2 or higher cluster tiers for production
-   Enable backup and point-in-time recovery
-   Set up monitoring and alerts
-   Use connection pooling

### Connection String Best Practices

-   Use connection string parameters:

```
mongodb+srv://user:pass@cluster.net/nanda?retryWrites=true&w=majority&maxPoolSize=50&connectTimeoutMS=5000
```

### Monitoring

-   Monitor agent registration patterns
-   Set up alerts for connection failures
-   Track registry performance metrics
-   Log agent lifecycle events

This completes the MongoDB registry integration! 🎉
