#!/usr/bin/env python3
"""
Quick agent setup verification script for EC2 instances.
Run this on each EC2 instance to verify the configuration.
"""
import os
import sys

def check_agent_setup():
    """Check if agent is properly configured"""
    print("🔍 Agent Setup Verification")
    print("=" * 40)
    
    # Check critical environment variables
    agent_id = os.getenv("AGENT_ID")
    public_url = os.getenv("PUBLIC_URL")
    api_url = os.getenv("API_URL")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    issues = []
    
    print(f"Agent ID: {agent_id or 'NOT SET'}")
    if not agent_id or agent_id == "default":
        issues.append("❌ AGENT_ID not set or using default")
    else:
        print("✅ Agent ID is configured")
    
    print(f"Public URL: {public_url or 'NOT SET'}")
    if not public_url:
        issues.append("❌ PUBLIC_URL not set")
    else:
        print("✅ Public URL is configured")
    
    print(f"API URL: {api_url or 'NOT SET'}")
    if not api_url:
        issues.append("❌ API_URL not set")
    else:
        print("✅ API URL is configured")
    
    if not anthropic_key or anthropic_key == "your key":
        issues.append("❌ ANTHROPIC_API_KEY not set or using placeholder")
    else:
        print("✅ Anthropic API key is configured")
    
    if issues:
        print("\n⚠️ Issues found:")
        for issue in issues:
            print(f"  {issue}")
        
        print("\n💡 To fix, set environment variables:")
        if not agent_id or agent_id == "default":
            print("  export AGENT_ID=your_unique_agent_name")
        if not public_url:
            print("  export PUBLIC_URL=https://your-agent-domain.com")
        if not api_url:
            print("  export API_URL=https://your-api-domain.com")
        if not anthropic_key or anthropic_key == "your key":
            print("  export ANTHROPIC_API_KEY=your_actual_api_key")
            
        print("\n📝 To make permanent, add to ~/.bashrc:")
        print("  echo 'export AGENT_ID=your_agent_name' >> ~/.bashrc")
        
        return False
    else:
        print("\n✅ All critical configuration is set!")
        
        # Test the modular system
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nanda_adapter'))
            from nanda_adapter.core.claude_integration import get_agent_id
            from nanda_adapter.core.modular_agent_bridge import ModularAgentBridge
            
            detected_agent_id = get_agent_id()
            print(f"✅ Detected agent ID from system: {detected_agent_id}")
            
            if detected_agent_id != agent_id:
                print(f"⚠️ Environment AGENT_ID ({agent_id}) != detected ID ({detected_agent_id})")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing modular system: {e}")
            return False

if __name__ == "__main__":
    success = check_agent_setup()
    sys.exit(0 if success else 1)