"""
Claude AI integration module for NANDA Agent Bridge.
Handles all Anthropic Claude API interactions and message improvement.
"""
import os
import traceback
import logging
from typing import Optional
from datetime import datetime
from anthropic import Anthropic, APIStatusError
from .logging_utils import log_message

# Disable httpx INFO logging to reduce debug output
logging.getLogger("httpx").setLevel(logging.WARNING)


# Set API key through environment variable or directly in the code
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or "your key"

# Toggle for message improvement feature
IMPROVE_MESSAGES = os.getenv("IMPROVE_MESSAGES", "true").lower() in ("true", "1", "yes", "y")

# Create Anthropic client with explicit API key
anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

# Configure system prompts based on agent ID
SYSTEM_PROMPTS = {
    "default": "You are Claude assisting a user (Agent). Assume the messages you get are part of a conversation with other agents. Help the user communicate effectively with other agents."
}

# Configure message improvement prompts
IMPROVE_MESSAGE_PROMPTS = {    
    "default": "Improve the following message to make it more clear, compelling, and professional without changing the core content or adding fictional information. Keep the same overall meaning but enhance the phrasing and structure. Don't make it too verbose - keep it concise but impactful. Return only the improved message without explanations or introductions."
}


def get_agent_id() -> str:
    """Get AGENT_ID dynamically from environment variables"""
    return os.getenv("AGENT_ID", "default")


def call_claude(prompt: str, additional_context: str, conversation_id: str, current_path: str, system_prompt: str = None, agent_id: str = None) -> Optional[str]:
    """Wrapper that never raises: returns text or None on failure."""
    try:
        # print(f"[CLAUDE_INTEGRATION] call_claude() called")
        # print(f"[CLAUDE_INTEGRATION] Input prompt length: {len(prompt)}")
        # print(f"[CLAUDE_INTEGRATION] Input prompt preview: '{prompt[:100]}...'")
        # print(f"[CLAUDE_INTEGRATION] Additional context: '{additional_context}'")
        
        # Check for empty prompt
        if not prompt or not prompt.strip():
            # print(f"[CLAUDE_INTEGRATION] ERROR: Empty prompt detected! prompt='{prompt}'")
            return "Error: Empty message content provided"
            
        # Use the specified system prompt or default to the agent's system prompt
        if system_prompt:
            system = system_prompt
        else:
            # Use the agent's specific prompt if available, otherwise use default
            system = SYSTEM_PROMPTS["default"]
        
        # Combine the prompt with additional context if provided
        full_prompt = prompt
        if additional_context and additional_context.strip():
            full_prompt = f"ADDITIONAL CONTEXT FROM USER: {additional_context}\n\nMESSAGE: {prompt}"
        
        # print(f"[CLAUDE_INTEGRATION] Full prompt length: {len(full_prompt)}")
        # print(f"[CLAUDE_INTEGRATION] Full prompt preview: '{full_prompt[:200]}...'")
        
        # Check for empty full prompt
        if not full_prompt or not full_prompt.strip():
            # print(f"[CLAUDE_INTEGRATION] ERROR: Empty full_prompt after processing! full_prompt='{full_prompt}'")
            return "Error: Empty message content after processing"
        
        # Use provided agent_id or get from environment
        if not agent_id:
            agent_id = get_agent_id()
            
        # print(f"[CLAUDE_INTEGRATION] Agent {agent_id}: Calling Claude API...")
        # print(f"[CLAUDE_INTEGRATION] System prompt: '{system[:100]}...')")
        
        resp = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=512,
            messages=[{"role":"user","content":full_prompt}],
            system=system
        )
        response_text = resp.content[0].text
        
        # print(f"[CLAUDE_INTEGRATION] Claude response length: {len(response_text)}")
        # print(f"[CLAUDE_INTEGRATION] Claude response preview: '{response_text[:100]}...'")
        
        # Log the Claude response
        log_message(conversation_id, current_path, f"Claude {agent_id}", response_text)
        
        return response_text
    except APIStatusError as e:
        if not agent_id:
            agent_id = get_agent_id()
        print(f"Agent {agent_id}: Anthropic API error:", e.status_code, e.message, flush=True)
        # If we hit a credit limit error, return a fallback message
        if "credit balance is too low" in str(e):
            return f"Agent {agent_id} processed (API credit limit reached): {prompt}"
    except Exception as e:
        if not agent_id:
            agent_id = get_agent_id()
        print(f"Agent {agent_id}: Anthropic SDK error:", e, flush=True)
        traceback.print_exc()
    return None


def call_claude_direct(message_text: str, system_prompt: str = None) -> Optional[str]:
    """Wrapper that never raises: returns text or None on failure."""
    try:
        # Combine the prompt with additional context if provided
        full_prompt = f"MESSAGE: {message_text}"
        
        agent_id = get_agent_id()
        print(f"Agent {agent_id}: Calling Claude with prompt: {full_prompt[:50]}...")
        resp = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=512,
            messages=[{"role":"user","content":full_prompt}],
            system=system_prompt
        )
        response_text = resp.content[0].text
        
        return response_text
    except APIStatusError as e:
        agent_id = get_agent_id()
        print(f"Agent {agent_id}: Anthropic API error:", e.status_code, e.message, flush=True)
        # If we hit a credit limit error, return a fallback message
        if "credit balance is too low" in str(e):
            return f"Agent {agent_id} processed (API credit limit reached): {message_text}"
    except Exception as e:
        agent_id = get_agent_id()
        print(f"Agent {agent_id}: Anthropic SDK error:", e, flush=True)
        traceback.print_exc()
    return None


def improve_message(message_text: str, conversation_id: str, current_path: str, additional_prompt: str = None) -> str:
    """Improve a message using Claude before forwarding it to the other party."""
    if not IMPROVE_MESSAGES:
        return message_text
    
    try:
        if additional_prompt:
            system_prompt = additional_prompt + IMPROVE_MESSAGE_PROMPTS["default"]
        else:
            # Use the appropriate improvement prompt based on agent ID
            system_prompt = IMPROVE_MESSAGE_PROMPTS["default"]
        
        # Call Claude to improve the message
        improved_message = call_claude(message_text, "", conversation_id, current_path, system_prompt)
        
        # If Claude successfully improved the message, use that; otherwise, use the original
        return improved_message if improved_message else message_text
    except Exception as e:
        print(f"Error improving message: {e}")
        return message_text


# Message improvement decorator system
message_improvement_decorators = {}


def message_improver(name=None):
    """Decorator to register message improvement functions"""
    def decorator(func):
        decorator_name = name or func.__name__
        message_improvement_decorators[decorator_name] = func
        return func
    return decorator


def register_message_improver(name: str, improver_func):
    """Register a custom message improver function"""
    message_improvement_decorators[name] = improver_func


def get_message_improver(name: str):
    """Get a registered message improver by name"""
    return message_improvement_decorators.get(name)


def list_message_improvers():
    """List all registered message improvers"""
    return list(message_improvement_decorators.keys())


# Default improver
@message_improver("default_claude")
def default_claude_improver(message_text: str) -> str:
    """Default Claude-based message improvement"""
    if not IMPROVE_MESSAGES:
        return message_text
    
    try:
        additional_prompt = "Do not respond to the content of the message - it's intended for another agent. You are helping an agent communicate better with other agents."
        system_prompt = additional_prompt + IMPROVE_MESSAGE_PROMPTS["default"]
        print(system_prompt)
        improved_message = call_claude_direct(message_text, system_prompt)
        print(f"Improved message: {improved_message}")
        return improved_message if improved_message else message_text
    except Exception as e:
        print(f"Error improving message: {e}")
        return message_text