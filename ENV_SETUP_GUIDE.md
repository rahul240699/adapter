# Environment Configuration Guide

## 🔧 Setting up Environment Variables

The NANDA Adapter uses environment variables for configuration, including sensitive information like API keys. This guide shows you how to set them up securely.

### 1. Create your .env file

Copy the example template:
```bash
cp .env.example .env
```

### 2. Add your API keys

Edit the `.env` file and add your actual values:
```bash
# Required: Your Anthropic Claude API key
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here

# Optional configurations
AGENT_ID=my_agent
USE_LOCAL_REGISTRY=true
DEBUG=true
LOG_LEVEL=INFO
```

### 3. Security Notes

- ✅ **The `.env` file is in `.gitignore`** - it will NOT be committed to git
- ❌ **Never commit API keys to version control**
- 🔒 **Keep your `.env` file secure and private**
- 📝 **Use `.env.example` for documentation/templates**

### 4. Usage in Code

The environment variables are automatically loaded when you import NANDA modules:

```python
from nanda_adapter.core.env_loader import load_env_file, get_anthropic_api_key

# Load .env file
load_env_file()

# Get API key safely
api_key = get_anthropic_api_key()
if api_key:
    print("✅ API key loaded successfully")
else:
    print("❌ API key not found")
```

### 5. Testing Configuration

You can test your environment setup:

```bash
python3 nanda_adapter/core/env_loader.py
```

This will show:
```
🔧 NANDA Adapter Environment Configuration
==================================================
✅ Loaded ANTHROPIC_API_KEY: ********************
✅ Loaded AGENT_ID: my_agent
✅ Loaded USE_LOCAL_REGISTRY: true
🎉 Environment configuration is valid!
```

### 6. Alternative: Export Environment Variables

If you prefer not to use a `.env` file, you can export variables directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
export AGENT_ID=my_agent
export USE_LOCAL_REGISTRY=true
```

### 7. Required vs Optional Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | ✅ Yes | Claude API key | None |
| `AGENT_ID` | ❌ No | Agent identifier | "default" |
| `USE_LOCAL_REGISTRY` | ❌ No | Use local vs remote registry | "false" |
| `DEBUG` | ❌ No | Enable debug logging | "false" |
| `LOG_LEVEL` | ❌ No | Logging level | "INFO" |

### 8. Troubleshooting

#### API Key Issues
```
❌ ANTHROPIC_API_KEY not found in environment variables
```
**Solution**: Make sure your `.env` file exists and contains the API key.

#### Permission Issues
```
❌ Error loading .env file: Permission denied
```
**Solution**: Check file permissions: `chmod 600 .env`

#### Invalid API Key
```
❌ ANTHROPIC_API_KEY is set to placeholder value
```
**Solution**: Replace "your_key_here" with your actual API key.

## 🚀 Quick Start

1. Copy template: `cp .env.example .env`
2. Edit `.env` with your API key
3. Test: `python3 nanda_adapter/core/env_loader.py`
4. Run agents: `python3 test_a2a_agents.py agent_a`

That's it! Your environment is now securely configured. 🔒✨