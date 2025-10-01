# 🚀 NANDA EC2 Quick Reference

## 🎯 Quick Deploy (From Local Machine)

### 1. Create Configuration

```bash
# Use the provided sample or create your own
cp my_deployment_config.sh deployment_config.sh
# Edit deployment_config.sh with your instances and settings
```

### 2. Deploy to All Instances

```bash
./deploy_to_ec2.sh deployment_config.sh
```

### 3. Test Deployment

```bash
./test_deployment.sh deployment_config.sh
```

## ⚙️ Configuration Format

### deployment_config.sh Structure

```bash
#!/bin/bash
# SSH Configuration
SSH_KEY="your-key.pem"
SSH_USER="ubuntu"

# Repository Configuration
REPO_URL="https://github.com/user/repo.git"
REPO_BRANCH="main"

# Agent Instances (IP:AGENT_ID:PORT:MODE)
INSTANCES=(
    "1.2.3.4:agent_a:6001:interactive"
    "5.6.7.8:agent_b:6002:server"
)
```

## ⚙️ Manual Setup Per Instance

### 1. Connect & Setup

```bash
ssh -i "your-key.pem" ubuntu@your-instance-ip
curl -fsSL https://raw.githubusercontent.com/user/repo/branch/scripts/setup_ec2_agent.sh | bash -s -- agent_id mode repo_url branch port
```

### 2. Configure Environment

```bash
cd repo_name  # or whatever your repo is called
nano .env
```

**Required .env values:**

```bash
ANTHROPIC_API_KEY=your_real_key_here
AGENT_ID=your_agent_id
PUBLIC_URL=auto  # or specify manually
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/nanda
```

### 3. Start Agents

````bash
source venv/bin/activate

# For server-only agents
python3 interactive_agent_demo.py agent_id --server-only

# For interactive agents
python3 interactive_agent_demo.py agent_id
```## 🧪 Test A2A Communication
In any interactive agent terminal:
````

@other_agent_id what is the capital of France?

````

## 🔧 Troubleshooting
```bash
# Check logs
tail -f logs/agent_*/conversation_*.jsonl

# Check registry
python3 -c "from nanda_adapter.core.registry import create_registry; print(create_registry().list())"

# Check network endpoints
curl http://instance-ip:port/health
````

## 📋 Security Groups

Ensure inbound rules allow TCP on your configured ports and SSH (port 22).

## 📄 Sample Configuration (my_deployment_config.sh)

```bash
SSH_KEY="nanda-agent-key.pem"
SSH_USER="ubuntu"
REPO_URL="https://github.com/rahul240699/adapter.git"
REPO_BRANCH="feature/remote-deployment"
INSTANCES=(
    "3.90.208.173:agent_a:6001:interactive"
    "3.80.76.207:agent_b:6002:server"
)
```

Your distributed NANDA agents are ready! 🎉
