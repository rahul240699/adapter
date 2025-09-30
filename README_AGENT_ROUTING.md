# 🤖 NANDA @Agent Routing System

**Natural Agent-to-Agent Communication with Claude Enhancement**

This system enables natural conversational flow where users interact with one agent that intelligently routes messages to other agents using @mentions, just like social media or Slack.

## ✨ Key Features

-   **@Agent Routing**: Natural `@agent_b help me` syntax for inter-agent communication
-   **Claude Enhancement**: Messages are automatically improved for clarity and professionalism
-   **Local Registry**: File-based agent discovery (`.nanda_registry.json`)
-   **Secure Configuration**: API keys stored in `.env` files
-   **Bidirectional Flow**: Responses come back through the originating agent

## 🔄 How @Agent Routing Works

```
User → Agent_A → @agent_b detected → Claude improves message → Agent_B → Response → Agent_A → User
```

**Example Conversation:**

```
[agent_a] You: @agent_b help me debug this Python function

🧠 Improving message with Claude...
🤖 agent_a: [agent_a] Message sent to agent_b

📝 What happened:
  1. You sent message to agent_a
  2. agent_a detected @agent_b routing
  3. agent_a improved your message with Claude
  4. agent_a sent improved message to agent_b
  5. Result: [agent_a] Message sent to agent_b
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Add your Anthropic API key to .env
echo "ANTHROPIC_API_KEY=your_api_key_here" >> .env
```

### 2. Run Interactive Demo

```bash
# Terminal 1: Start agent_a
python3 interactive_agent_demo.py agent_a

# Terminal 2: Start agent_b (for testing)
python3 interactive_agent_demo.py agent_b
```

### 3. Test @Agent Routing

In agent_a terminal:

```
[agent_a] You: Hello, how are you?
🤖 agent_a: Hello! I'm doing well, thank you for asking...

[agent_a] You: @agent_b can you help me with a coding problem?
🧠 Improving message with Claude...
🤖 agent_a: [agent_a] Message sent to agent_b
```

## 📁 Project Structure

```
nanda_adapter/
├── core/
│   ├── router.py           # @Agent routing logic
│   ├── claude_integration.py  # Message improvement
│   ├── env_loader.py       # Secure environment loading
│   └── ...
├── simple.py              # SimpleNANDA class
└── examples/               # Demo scripts
```

## 🔧 Core Components

### MessageRouter (`router.py`)

-   Detects `@agent_name` patterns in messages
-   Improves messages using Claude API
-   Routes to target agents via A2A protocol
-   Handles response flow back to user

### SimpleNANDA (`simple.py`)

-   Streamlined agent setup with router integration
-   Automatic registry management
-   Built-in Claude enhancement support

### Environment Loader (`env_loader.py`)

-   Secure `.env` file loading
-   API key validation
-   Configuration verification

## 🎯 Usage Examples

### Basic Agent Creation

```python
from nanda_adapter.simple import SimpleNANDA

agent = SimpleNANDA(
    agent_id="my_agent",
    host="localhost:6000",
    require_anthropic=True
)
```

### Custom Message Improvement

```python
def custom_improver(text: str) -> str:
    # Your custom logic here
    return improved_text

agent = SimpleNANDA(
    agent_id="my_agent",
    improvement_logic=custom_improver
)
```

### Manual @Agent Routing

```python
response = agent.router.route("@agent_b help with this", "conversation_id")
print(response)  # "[my_agent] Message sent to agent_b"
```

## 🔒 Security & Configuration

### Environment Variables (`.env`)

```bash
ANTHROPIC_API_KEY=your_api_key_here
DEBUG=true
USE_LOCAL_REGISTRY=true
LOG_LEVEL=INFO
```

### Registry Management

-   Agents auto-register in `.nanda_registry.json`
-   No external dependencies
-   Local file-based discovery

## 🧪 Testing

### Complete Flow Test

```bash
python3 test_complete_flow.py
```

### Interactive Testing

```bash
python3 interactive_agent_demo.py agent_a
```

### Two Agent Example

```bash
python3 examples/two_agents_local.py
```

## 📊 Debug & Monitoring

### Enable Debug Logging

```bash
echo "DEBUG=true" >> .env
echo "LOG_LEVEL=DEBUG" >> .env
```

### View Logs

```bash
# Agent-specific logs
tail -f logs/agent_agent_a/conversation_test.jsonl

# Debug output in terminal
python3 interactive_agent_demo.py agent_a
```

## 🛠️ Advanced Features

### Custom Response Handlers

```python
def handle_response(response_data):
    # Process agent responses
    return formatted_response

agent.router.set_response_handler(handle_response)
```

### Registry Operations

```python
# List all agents
agents = agent.registry.list()

# Find specific agent
agent_info = agent.registry.get("agent_b")

# Check agent availability
is_available = agent.registry.is_agent_available("agent_b")
```

## 🚨 Troubleshooting

### Common Issues

**1. "No ANTHROPIC_API_KEY found"**

-   Ensure `.env` file exists with valid API key
-   Check `.env` is not in `.gitignore` during development

**2. "Agent not found in registry"**

-   Start target agent first to register it
-   Check `.nanda_registry.json` for available agents

**3. "@agent routing not working"**

-   Ensure message starts with `@agent_name`
-   Check target agent is running and registered
-   Verify Claude API key is valid

### Debug Mode

```bash
DEBUG=true python3 interactive_agent_demo.py agent_a
```

## 📝 Contributing

1. **Branch Strategy**: Create feature branches for new functionality
2. **Environment**: Always use `.env` files, never hardcode API keys
3. **Testing**: Test @agent routing flow before submitting
4. **Commits**: Ask before committing large changes

## 🎉 What's New in Enhanced A2A

-   ✅ Dynamic agent ID resolution (no more "default" issues)
-   ✅ @Agent routing with natural syntax
-   ✅ Claude-powered message improvement
-   ✅ Secure environment configuration
-   ✅ Local registry system
-   ✅ Comprehensive debug logging
-   ✅ Interactive demo tools

## 🔄 Migration from Previous Versions

**Old FROM:TO:CONTENT Format:**

```
FROM:agent_a:TO:agent_b:CONTENT:help me debug
```

**New @Agent Format:**

```
@agent_b help me debug
```

The system now handles user experience naturally - users chat with one agent and use @mentions for routing, just like they would in any modern chat application.

---

**Happy Agent Routing! 🤖💬**
