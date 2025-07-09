# NANDA Agent Framework

A customizable AI Agent Communication Framework with pluggable message improvement logic, built on top of the python_a2a communication framework.

## Features

- **Pluggable Message Improvement**: Easily customize how your agents improve messages
- **Multiple AI Frameworks**: Support for LangChain, CrewAI, and custom logic
- **Agent-to-Agent Communication**: Built-in A2A communication system
- **Registry System**: Automatic agent discovery and registration
- **SSL Support**: Production-ready with Let's Encrypt certificates
- **Example Agents**: Ready-to-use examples for common use cases

## Installation

### Basic Installation

```bash
pip install nanda-agent
```

### With LangChain Support

```bash
pip install nanda-agent[langchain]
```

### With CrewAI Support

```bash
pip install nanda-agent[crewai]
```

### With All Dependencies

```bash
pip install nanda-agent[all]
```

## Quick Start

### 1. Set Your API Key

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 2. Run a Simple Example

```bash
# Simple pirate agent (no extra dependencies)
nanda-pirate

# LangChain-powered pirate agent
nanda-pirate-langchain

# CrewAI-powered sarcastic agent
nanda-sarcastic
```

### 3. Create Your Own Agent

```python
from nanda_agent import NANDA

def my_improvement_logic(message_text: str) -> str:
    """Custom logic to improve messages"""
    return f"✨ {message_text.upper()} ✨"

# Create and start your agent
nanda = NANDA(my_improvement_logic)
nanda.start_server()
```

## Usage

### Creating a Custom Agent

```python
#!/usr/bin/env python3
from nanda_agent import NANDA
import os

def create_custom_improvement():
    """Create your custom improvement function"""
    
    def custom_improvement_logic(message_text: str) -> str:
        """Transform messages according to your logic"""
        try:
            # Your custom transformation logic here
            improved_text = message_text.replace("hello", "greetings")
            improved_text = improved_text.replace("goodbye", "farewell")
            
            return improved_text
        except Exception as e:
            print(f"Error in improvement: {e}")
            return message_text  # Fallback to original
    
    return custom_improvement_logic

def main():
    # Create your improvement function
    my_improvement = create_custom_improvement()
    
    # Initialize NANDA with your custom logic
    nanda = NANDA(my_improvement)
    
    # Start the server
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    domain = os.getenv("DOMAIN_NAME", "localhost")
    
    if domain != "localhost":
        # Production API server
        nanda.start_server_api(anthropic_key, domain)
    else:
        # Development server
        nanda.start_server()

if __name__ == "__main__":
    main()
```

### Using with LangChain

```python
from nanda_agent import NANDA
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_anthropic import ChatAnthropic

def create_langchain_improvement():
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-haiku-20240307"
    )
    
    prompt = PromptTemplate(
        input_variables=["message"],
        template="Make this message more professional: {message}"
    )
    
    chain = prompt | llm | StrOutputParser()
    
    def langchain_improvement(message_text: str) -> str:
        return chain.invoke({"message": message_text})
    
    return langchain_improvement

# Use it
nanda = NANDA(create_langchain_improvement())
nanda.start_server()
```

### Using with CrewAI

```python
from nanda_agent import NANDA
from crewai import Agent, Task, Crew
from langchain_anthropic import ChatAnthropic

def create_crewai_improvement():
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-haiku-20240307"
    )
    
    improvement_agent = Agent(
        role="Message Improver",
        goal="Improve message clarity and professionalism",
        backstory="You are an expert communicator.",
        llm=llm
    )
    
    def crewai_improvement(message_text: str) -> str:
        task = Task(
            description=f"Improve this message: {message_text}",
            agent=improvement_agent,
            expected_output="An improved version of the message"
        )
        
        crew = Crew(agents=[improvement_agent], tasks=[task])
        result = crew.kickoff()
        return str(result)
    
    return crewai_improvement

# Use it
nanda = NANDA(create_crewai_improvement())
nanda.start_server()
```

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key (required)
- `DOMAIN_NAME`: Domain name for SSL certificates (default: localhost)
- `AGENT_ID`: Custom agent ID (optional, auto-generated if not provided)
- `PORT`: Agent bridge port (default: 6000)
- `IMPROVE_MESSAGES`: Enable/disable message improvement (default: true)

### Production Deployment

For production deployment with SSL:

```bash
export ANTHROPIC_API_KEY="your-api-key"
export DOMAIN_NAME="your-domain.com"
nanda-pirate
```

The framework will automatically:
- Generate SSL certificates using Let's Encrypt
- Set up proper agent registration
- Configure production-ready logging

## API Endpoints

When running with `start_server_api()`, the following endpoints are available:

- `GET /api/health` - Health check
- `POST /api/send` - Send message to agent
- `GET /api/agents/list` - List registered agents
- `POST /api/receive_message` - Receive message from agent
- `GET /api/render` - Get latest message

## Agent Communication

Agents can communicate with each other using the `@agent_id` syntax:

```
@agent123 Hello there!
```

The message will be improved using your custom logic before being sent.

## Command Line Tools

```bash
# Show help
nanda-agent --help

# List available examples
nanda-agent --list-examples

# Run specific examples
nanda-pirate              # Simple pirate agent
nanda-pirate-langchain    # LangChain pirate agent
nanda-sarcastic           # CrewAI sarcastic agent
```

## Architecture

The NANDA framework consists of:

1. **AgentBridge**: Core communication handler
2. **Message Improvement System**: Pluggable improvement logic
3. **Registry System**: Agent discovery and registration
4. **A2A Communication**: Agent-to-agent messaging
5. **Flask API**: External communication interface

## Development

### Running from Source

```bash
git clone https://github.com/nanda-ai/nanda-agent.git
cd nanda-agent
pip install -e .
```

### Creating Custom Agents

1. Create your improvement function
2. Initialize NANDA with your function
3. Start the server
4. Your agent is ready to communicate!

## Examples

The framework includes several example agents:

- **Simple Pirate Agent**: Basic string replacement
- **LangChain Pirate Agent**: AI-powered pirate transformation
- **CrewAI Sarcastic Agent**: Team-based sarcastic responses

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

## Support

For issues and questions:
- GitHub Issues: https://github.com/nanda-ai/nanda-agent/issues
- Email: support@nanda.ai

## Changelog

### v1.0.0
- Initial release
- Basic NANDA framework
- LangChain integration
- CrewAI integration
- Example agents
- Production deployment support