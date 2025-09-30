"""
Environment variable loader for NANDA Adapter

This module provides utilities for loading environment variables from .env files
and ensures proper configuration for the NANDA adapter system.
"""

import os
from pathlib import Path
from typing import Optional

def load_env_file(env_file: str = ".env") -> bool:
    """
    Load environment variables from a .env file.
    
    Args:
        env_file: Path to the .env file (default: ".env")
        
    Returns:
        True if the file was loaded successfully, False otherwise
    """
    env_path = Path(env_file)
    
    if not env_path.exists():
        print(f"⚠️  .env file not found at {env_path.absolute()}")
        return False
    
    try:
        with open(env_path, 'r') as f:
            lines = f.readlines()
            
        loaded_vars = 0
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
                
            if '=' not in line:
                print(f"⚠️  Invalid line {line_num} in .env: {line}")
                continue
                
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            
            # Set environment variable
            os.environ[key] = value
            loaded_vars += 1
            
            # Only show non-sensitive vars in output
            if 'API_KEY' in key or 'SECRET' in key or 'TOKEN' in key:
                print(f"✅ Loaded {key}: {'*' * min(len(value), 20)}")
            else:
                print(f"✅ Loaded {key}: {value}")
        
        print(f"🔧 Successfully loaded {loaded_vars} environment variables from {env_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error loading .env file: {e}")
        return False

def get_anthropic_api_key() -> Optional[str]:
    """
    Get the Anthropic API key from environment variables.
    
    Returns:
        The API key if found, None otherwise
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment variables")
        print("💡 Make sure to:")
        print("   1. Create a .env file with ANTHROPIC_API_KEY=your_key")
        print("   2. Call load_env_file() to load the .env file")
        print("   3. Or set the environment variable directly")
        return None
    
    if api_key in ["your_key", "your-key-here", ""]:
        print("❌ ANTHROPIC_API_KEY is set to placeholder value")
        print("💡 Please update .env file with your actual API key")
        return None
    
    return api_key

def verify_environment() -> bool:
    """
    Verify that all required environment variables are properly set.
    
    Returns:
        True if environment is properly configured, False otherwise
    """
    print("🔍 Verifying environment configuration...")
    
    required_vars = ["ANTHROPIC_API_KEY"]
    optional_vars = ["AGENT_ID", "USE_LOCAL_REGISTRY", "DEBUG", "LOG_LEVEL"]
    
    all_good = True
    
    # Check required variables
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            print(f"❌ Required variable {var} is not set")
            all_good = False
        elif value in ["your_key", "your-key-here", ""]:
            print(f"❌ Required variable {var} has placeholder value")
            all_good = False
        else:
            print(f"✅ Required variable {var} is set")
    
    # Check optional variables
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ Optional variable {var}: {value}")
        else:
            print(f"ℹ️  Optional variable {var} not set (using defaults)")
    
    if all_good:
        print("🎉 Environment configuration is valid!")
    else:
        print("⚠️  Environment configuration needs attention")
    
    return all_good

# Auto-load .env file when module is imported
if __name__ != "__main__":
    # Try to load .env file automatically when imported
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_env_file(str(env_file))

if __name__ == "__main__":
    # When run directly, perform environment check
    print("🔧 NANDA Adapter Environment Configuration")
    print("=" * 50)
    
    # Load .env file
    load_env_file()
    
    # Verify configuration
    verify_environment()
    
    # Test API key
    api_key = get_anthropic_api_key()
    if api_key:
        print(f"🔑 API Key loaded successfully: {api_key[:10]}...{api_key[-10:]}")
    else:
        print("❌ API Key validation failed")