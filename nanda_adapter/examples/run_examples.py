#!/usr/bin/env python3
"""
Example usage and test script for the specialized NANDA agents
"""
import os
import sys

def print_usage():
    """Print usage instructions for the specialized agents"""
    print("\n🍽️  NANDA Specialized Agents 🍽️")
    print("=" * 50)
    print("\nAvailable Agents:")
    print("1. 🏴‍☠️ Pirate Agent (langchain_pirate.py)")
    print("   - Transforms messages into pirate English")
    print("   - Uses: LangChain + Anthropic Claude")
    
    print("\n2. 🐟 Seafood Expert Agent (seafood_expert.py)")
    print("   - Enhances messages with seafood expertise")
    print("   - Adds marine biology, sustainability, and preparation tips")
    print("   - Uses: LangChain + Anthropic Claude")
    
    print("\n3. 👨‍🍳 Chef Agent (chef_agent.py)")
    print("   - Enhances messages with culinary expertise")
    print("   - Adds cooking techniques, ingredients, and food knowledge")
    print("   - Uses: CrewAI + Anthropic Claude")
    
    print("\n4. 😏 Sarcastic Agent (crewai_sarcastic.py)")
    print("   - Transforms messages into witty, sarcastic responses")
    print("   - Uses: CrewAI + Anthropic Claude")
    
    print("\n" + "=" * 50)
    print("\n🚀 How to Run:")
    print("1. Set your ANTHROPIC_API_KEY environment variable:")
    print("   export ANTHROPIC_API_KEY='your-key-here'")
    
    print("\n2. Install dependencies:")
    print("   pip install -r requirements.txt")
    
    print("\n3. Run an agent:")
    print("   python langchain_pirate.py")
    print("   python seafood_expert.py")
    print("   python chef_agent.py")
    print("   python crewai_sarcastic.py")
    
    print("\n4. Each agent will start on a different port and can communicate with others!")
    
    print("\n💡 Agent Interaction Examples:")
    print("- Pirate → Chef: 'Arrr, what be the best way to cook fish, matey?'")
    print("- Chef → Seafood Expert: 'I need advice on sustainable salmon preparation techniques.'")
    print("- Seafood Expert → Sarcastic: 'Wild-caught Atlantic salmon (Salmo salar) is the premium choice.'")
    print("- Sarcastic → Pirate: 'Oh great, another fish lecture. How absolutely riveting.'")

def check_requirements():
    """Check if required dependencies are installed"""
    missing = []
    try:
        import langchain_core
        import langchain_anthropic
    except ImportError:
        missing.append("langchain-core, langchain-anthropic")
    
    try:
        import crewai
    except ImportError:
        missing.append("crewai")
    
    try:
        from nanda_adapter.core.nanda import NANDA
    except ImportError:
        missing.append("nanda-adapter")
    
    if missing:
        print("❌ Missing dependencies:")
        for dep in missing:
            print(f"   - {dep}")
        print("\nRun: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies are installed!")
    return True

def main():
    print_usage()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        print("\n🔍 Checking dependencies...")
        check_requirements()
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n⚠️  WARNING: ANTHROPIC_API_KEY environment variable not set!")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")

if __name__ == "__main__":
    main()