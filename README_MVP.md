# NANDA Adapter v2.0 - Local Development MVP

**Simple, local-first agent-to-agent communication.**

No external registries. No SSL certificates. No complex setup.
Just Python, a few lines of code, and you're running multi-agent systems locally.

---

## Quick Start (2 Minutes)

### 1. Install

```bash
pip install anthropic python-a2a
```

### 2. Set API Key

```bash
export ANTHROPIC_API_KEY=sk-your-key-here
```

### 3. Run Two Agents

**Terminal 1 - Agent A:**
```bash
python examples/two_agents_local.py agent_a
```

**Terminal 2 - Agent B:**
```bash
python examples/two_agents_local.py agent_b
```

**Terminal 3 - Test Communication:**
```bash
curl -X POST http://localhost:6000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": {"type": "text", "text": "@agent_b What is 2+2?"},
    "conversation_id": "test"
  }'
```

**Expected Output:**
```json
{
  "role": "agent",
  "content": {"type": "text", "text": "[agent_a] Message sent to agent_b"},
  "conversation_id": "test"
}
```

Check agent_b's terminal - you'll see Claude's response!

---

## Features

✅ **File-Based Registry** - No MongoDB, no external services
✅ **HTTP for Local** - No SSL certificates needed
✅ **Loop Prevention** - Depth tracking prevents infinite loops
✅ **JSONL Logging** - Easy debugging with standard tools
✅ **Optional Claude** - Works with or without API key
✅ **host:port Flexibility** - localhost, remote IPs (192.168.1.100:6002)
✅ **Modern Python** - Type hints, docstrings, best practices
✅ **101 Tests** - Comprehensive test coverage

---

## Usage Examples

### Basic Agent (With Claude)

```python
from nanda_adapter.simple import SimpleNANDA

agent = SimpleNANDA('my_agent', 'localhost:6000')
agent.start()
```

### Agent Without Claude (Custom Logic)

```python
from nanda_adapter.simple import SimpleNANDA

def my_improver(text):
    return text.upper()

agent = SimpleNANDA(
    'simple_agent',
    'localhost:6000',
    improvement_logic=my_improver,
    require_anthropic=False  # No API key needed!
)
agent.start()
```

### Remote Host

```python
# Agent on specific IP address
agent = SimpleNANDA('agent_c', '192.168.1.100:6004')
agent.start()
```

---

## How It Works

### 1. Agent Registration

Agents automatically register in `.nanda_registry.json`:

```json
{
  "agent_a": {
    "agent_url": "http://localhost:6000",
    "registered_at": "2025-09-29T10:00:00Z",
    "last_seen": "2025-09-29T10:00:00Z"
  },
  "agent_b": {
    "agent_url": "http://localhost:6002",
    "registered_at": "2025-09-29T10:01:00Z",
    "last_seen": "2025-09-29T10:01:00Z"
  }
}
```

### 2. Message Flow

```
User → Agent A: "@agent_b What is 2+2?"
        ↓
Agent A looks up agent_b in registry
        ↓
Agent A → Agent B: A2A message (depth=0)
        ↓
Agent B → Claude: "What is 2+2?"
        ↓
Agent B → Agent A: Response (depth=1)
        ↓
Agent A logs response (max depth reached, no loop)
```

### 3. Loop Prevention

- **depth=0**: Initial request
- **depth=1**: Response (MAX - stops here)
- **depth>=1**: Logged but not responded to

This prevents infinite agent-to-agent loops.

---

## Testing with curl

### Send to Another Agent

```bash
curl -X POST http://localhost:6000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": {"type": "text", "text": "@agent_b Hello!"},
    "conversation_id": "conv_001"
  }'
```

### Query Local Agent Directly

```bash
curl -X POST http://localhost:6000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": {"type": "text", "text": "/query What is A2A?"},
    "conversation_id": "conv_002"
  }'
```

### Get Help

```bash
curl -X POST http://localhost:6000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": {"type": "text", "text": "/help"},
    "conversation_id": "help"
  }'
```

---

## Conversation Logs

Logs are automatically saved in JSONL format:

```bash
# View logs
cat logs/agent_agent_a/conversation_test.jsonl

# Pretty print with jq
cat logs/agent_agent_a/conversation_test.jsonl | jq .

# Watch in real-time
tail -f logs/agent_agent_a/conversation_test.jsonl
```

**Log Format:**
```json
{"timestamp":"2025-09-29T10:05:00Z","agent_id":"agent_a","conversation_id":"test","source":"incoming","message":"@agent_b Hello"}
{"timestamp":"2025-09-29T10:05:01Z","agent_id":"agent_a","conversation_id":"test","source":"outgoing","message":"[agent_a] Message sent to agent_b"}
```

---

## Configuration

### Constructor Parameters

```python
SimpleNANDA(
    agent_id: str,                    # Required: Unique agent identifier
    host: str = "localhost:6000",     # hostname:port
    improvement_logic: Callable = None,  # Optional message transformer
    anthropic_api_key: str = None,    # Or use ANTHROPIC_API_KEY env var
    require_anthropic: bool = True,   # Set False for no Claude
    registry: LocalRegistry = None,   # Custom registry instance
    log_dir: str = "./logs"          # Base log directory
)
```

### Environment Variables

Only **one** required (if using Claude):

```bash
ANTHROPIC_API_KEY=sk-your-key-here
```

That's it! Everything else has sensible defaults.

---

## Commands

Agents support these commands:

- **`@agent_id message`** - Send to another agent
- **`/query question`** - Query Claude directly (no routing)
- **`/help`** - Show available commands

---

## Architecture

### Core Modules (~650 LOC)

```
nanda_adapter/
├── core/
│   ├── registry.py      # File-based JSON registry
│   ├── protocol.py      # A2A message format + depth
│   ├── router.py        # Message routing + loops
│   └── logger.py        # JSONL conversation logs
└── simple.py            # SimpleNANDA entry point
```

### Tests (101 tests, all passing)

```
tests/unit/
├── test_registry.py     # 16 tests
├── test_protocol.py     # 30 tests
├── test_router.py       # 32 tests
└── test_logger.py       # 23 tests
```

---

## Troubleshooting

### "Agent not found in registry"

```bash
# Clear registry and restart agents
rm .nanda_registry.json
python examples/two_agents_local.py agent_a  # In terminal 1
python examples/two_agents_local.py agent_b  # In terminal 2
```

### "Connection refused"

```bash
# Check agent is running
lsof -i :6000

# Verify correct port
curl http://localhost:6000/a2a -v
```

### "ANTHROPIC_API_KEY not set"

```bash
# Set environment variable
export ANTHROPIC_API_KEY=sk-your-key-here

# Or run without Claude
python examples/simple_agent_no_claude.py
```

---

## What's Different from v1.x?

| Feature | v1.x | v2.0 MVP |
|---------|------|----------|
| **Registry** | External HTTPS | File-based JSON |
| **SSL** | Required | Not needed (HTTP) |
| **Setup Time** | ~15 min | < 2 min |
| **Dependencies** | 4+ (registry, certs) | 2 (Python libs) |
| **Env Vars** | 16 | 1 (API key) |
| **Offline** | ❌ No | ✅ Yes |
| **Tests** | 0 | 101 |
| **LOC** | ~2,400 | ~650 core |

---

## Next Steps

### Run the Examples

```bash
# With Claude
python examples/two_agents_local.py agent_a

# Without Claude
python examples/simple_agent_no_claude.py
```

### Read the Docs

- [Git Workflow](docs/GIT_WORKFLOW.md) - Branch naming, commit conventions
- [Testing Guide](docs/TESTING_GUIDE.md) - curl examples, debugging
- [Registry Spec](docs/REGISTRY_SPECIFICATION.md) - Local vs external
- [Bugs Fixed](docs/BUGS_AND_ISSUES.md) - API key lazy loading

### Build Your Own

```python
from nanda_adapter.simple import SimpleNANDA

# Your custom improvement logic
def my_logic(text):
    # Transform messages however you want
    return f"Enhanced: {text}"

agent = SimpleNANDA(
    'my_agent',
    'localhost:6000',
    improvement_logic=my_logic
)
agent.start()
```

---

## License

[Your License Here]

## Contributing

See [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) for branch naming and commit conventions.

**Important**: Never include AI tool branding in commits.

---

**Version**: 2.0.0-dev
**Branch**: feature/local-development-mvp
**Tests**: 101 passing
**Status**: Ready for PR