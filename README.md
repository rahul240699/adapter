# Internet of Agents

A distributed agent system that enables multiple agents to run and communicate with each other over HTTP/HTTPS.

## Overview

This system allows you to run multiple agents with unique IDs, each operating on different ports for bridge and API communication. The agents can communicate with each other and with external services through a registry.

## Prerequisites

- Python 3.x
- Bash shell
- Internet connectivity
- Anthropic API key

## Configuration

Before running the agents, you need to set up your Anthropic API key in your `.bashrc` file:

```bash
# Add this line to your ~/.bashrc
export ANTHROPIC_API_KEY="your-api-key-here"
```

## Agent Configuration

The agent system can be configured through the following parameters in `start_running_agents.sh`:

```bash
# Starting port numbers for bridge and API
START_BRIDGE_PORT=6000
START_API_PORT=6001

# Number of agents to create
NUM_AGENTS=7

# Prefix number for agent IDs (e.g., agentm6 will create agentm60, agentm61, etc.)
AGENT_ID_PREFIX=6
```

### Port Configuration
- Bridge ports start from `START_BRIDGE_PORT` and increment by 2
- API ports start from `START_API_PORT` and increment by 2
- For example, with default settings:
  - Bridge ports: 6000, 6002, 6004, 6006, 6008, 6010, 6012
  - API ports: 6001, 6003, 6005, 6007, 6009, 6011, 6013

### Agent IDs
- Agent IDs follow the pattern: `agentm{PREFIX}{INDEX}`
- With default settings (PREFIX=6, NUM_AGENTS=7):
  - agentm60, agentm61, agentm62, agentm63, agentm64, agentm65, agentm66

## Usage

1. Ensure your Anthropic API key is set in `.bashrc`
2. Make the script executable:
   ```bash
   chmod +x start_running_agents.sh
   ```
3. Run the script:
   ```bash
   ./start_running_agents.sh
   ```

## Monitoring and Management

### Check Running Agents
```bash
ps aux | grep run_ui_agent_https
```

### Stop All Agents
```bash
for pid in logs/*.pid; do kill $(cat $pid); done
```

### Logs
- Agent logs are stored in the `logs` directory
- Each agent has its own log file: `logs/agentm{ID}_logs.txt`
- Process IDs are stored in: `logs/agentm{ID}.pid`

## Network Configuration

The system automatically detects the server's IP address using:
1. AWS checkip service
2. ifconfig.me service
3. Falls back to localhost.com if both fail

Each agent is configured with:
- Public URL: `http://{SERVER_IP}:{BRIDGE_PORT}`
- API URL: `https://{SERVER_IP}:{API_PORT}`

## Registry

Agents are registered with a central registry at:
- Registry URL: `https://chat.nanda-registry.com:6900`

## Security

- API communication is secured using SSL
- Anthropic API key is stored in environment variables
- Each agent runs in its own process

## Troubleshooting

1. If agents fail to start:
   - Check if ports are available
   - Verify Anthropic API key is set correctly
   - Check logs in the `logs` directory

2. If agents can't communicate:
   - Verify network connectivity
   - Check if registry is accessible
   - Ensure ports are not blocked by firewall

## License

MIT License

Copyright (c) 2024 Internet of Agents

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. 