#!/bin/bash
# NANDA Agent Deployment Configuration
# This is a sample configuration for the specific EC2 instances mentioned

# SSH Configuration
SSH_KEY="nanda-agent-key.pem"        # Path to your SSH private key
SSH_USER="ubuntu"                    # SSH username (ubuntu for Ubuntu instances)

# Repository Configuration  
REPO_URL="https://github.com/rahul240699/adapter.git"  # Your repository URL
REPO_BRANCH="feature/remote-deployment"                # Branch to deploy

# Agent Instances Configuration
# Format: "IP:AGENT_ID:PORT:MODE"
# MODE can be "interactive" or "server"
INSTANCES=(
    "3.90.208.173:agent_a:6001:interactive"
    "3.80.76.207:agent_b:6002:server"
)

# Optional: Custom deployment directory (default: repository name)
# DEPLOY_DIR="custom-directory"