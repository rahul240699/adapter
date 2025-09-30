"""
Modular Agent Bridge for NANDA.
Main entry point that orchestrates all the different modules.
"""
import os
import uuid
from typing import Optional
from python_a2a import A2AServer, run_server, Message, TextContent, MessageRole, ErrorContent

# Import all our modular components
from .registry import register_with_registry
from .logging_utils import log_message, get_log_directory
from .claude_integration import (
    get_agent_id, IMPROVE_MESSAGES, 
    message_improvement_decorators, get_message_improver
)
from .a2a_messaging import A2AMessageHandler
from .command_handler import CommandHandler

# Environment configurations
PORT = int(os.getenv("PORT", "6000"))
TERMINAL_PORT = int(os.getenv("TERMINAL_PORT", "6010"))
UI_MODE = os.getenv("UI_MODE", "true").lower() in ("true", "1", "yes", "y")


class ModularAgentBridge(A2AServer):
    """Modular Agent Bridge - Separates concerns into dedicated modules"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_id = get_agent_id()
        self.a2a_handler = A2AMessageHandler()
        self.command_handler = CommandHandler()
        self.active_improver = "default_claude"  # Default improver
        
        print(f"Initialized Modular Agent Bridge for agent: {self.agent_id}")
    
    def set_message_improver(self, improver_name: str) -> bool:
        """Set the active message improver by name"""
        if improver_name in message_improvement_decorators:
            self.active_improver = improver_name
            print(f"Message improver set to: {improver_name}")
            return True
        else:
            available = list(message_improvement_decorators.keys())
            print(f"Unknown improver: {improver_name}. Available: {available}")
            return False
    
    def improve_message_direct(self, message_text: str) -> str:
        """Improve a message using the active registered improver"""
        improver_func = get_message_improver(self.active_improver)
        
        if improver_func:
            try:
                return improver_func(message_text)
            except Exception as e:
                print(f"Error with improver '{self.active_improver}': {e}")
                return message_text
        else:
            print(f"No improver found: {self.active_improver}")
            return message_text

    def handle_message(self, msg: Message) -> Message:
        """Main message handler - routes to appropriate processors"""
        # Ensure we have a conversation ID
        conversation_id = msg.conversation_id or str(uuid.uuid4())
        
        print(f"Agent {self.agent_id}: Received message with ID: {msg.message_id}")
        print(f"[DEBUG] Message type: {type(msg.content)}")
        print(f"Agent {self.agent_id}: Message metadata: {msg.metadata}")

        # Handle non-text content
        if not isinstance(msg.content, TextContent):
            print(f"Agent {self.agent_id}: Received non-text content. Returning error.")
            return Message(
                role=MessageRole.AGENT,
                content=ErrorContent(message="Only text payloads supported."),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )

        user_text = msg.content.text
        print(f"[MODULAR_BRIDGE] Received user_text length: {len(user_text)}")
        print(f"[MODULAR_BRIDGE] Received user_text: '{user_text}'")
        print(f"Agent {self.agent_id}: Received text: {user_text[:50]}...")
        
        # Check for empty text
        if not user_text or not user_text.strip():
            print(f"[MODULAR_BRIDGE] WARNING: Empty user_text detected!")
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=f"[AGENT {self.agent_id}] Error: Empty message received"),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )
        
        # Extract metadata
        metadata = self._extract_metadata(msg)
        path = metadata.get('path', '')
        source_agent = metadata.get('source_agent', '')
        is_from_peer = metadata.get('is_from_peer', False)
        additional_context = metadata.get('additional_context', '')
        
        # Add current agent ID to the path
        current_path = path + ('>' if path else '') + self.agent_id
        print(f"Agent {self.agent_id}: Current path: {current_path}")
        
        # Check for external A2A messages
        if user_text.startswith('__EXTERNAL_MESSAGE__'):
            print("--- External A2A Message Detected ---")
            # Use enhanced version that generates intelligent replies
            external_response = self.a2a_handler.handle_external_message_with_reply(user_text, conversation_id, msg)
            if external_response:
                return external_response
        
        # Handle messages from peer agents (already processed)
        if is_from_peer:
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=f"Message from peer received"),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )
        
        # Message from local terminal user - log it
        log_message(conversation_id, current_path, f"Local user to Agent {self.agent_id}", user_text)
        
        # Route to command handler
        return self.command_handler.process_command(
            user_text, conversation_id, current_path, additional_context, msg
        )
    
    def _extract_metadata(self, msg: Message) -> dict:
        """Extract and normalize metadata from message"""
        if hasattr(msg.metadata, 'custom_fields'):
            # Handle Metadata object format
            metadata = msg.metadata.custom_fields or {}
            print(f"Using custom_fields: {metadata}")
        else:
            # Handle dictionary format
            metadata = msg.metadata or {}
            print(f"Using direct metadata: {metadata}")
        
        return metadata


def start_modular_agent_bridge():
    """Start the modular agent bridge server"""
    # Get configuration
    agent_id = get_agent_id()
    port = int(os.getenv("PORT", "6000"))
    
    # Register with registry if PUBLIC_URL is set
    public_url = os.getenv("PUBLIC_URL")
    api_url = os.getenv("API_URL")
    if public_url:
        register_with_registry(agent_id, public_url, api_url)
    else:
        print("WARNING: PUBLIC_URL environment variable not set. Agent will not be registered.")
    
    print(f"Starting Modular Agent {agent_id} bridge on port {port}")
    print(f"Message improvement feature is {'ENABLED' if IMPROVE_MESSAGES else 'DISABLED'}")
    print(f"Logging conversations to {get_log_directory()}")
    
    # Start the server
    run_server(ModularAgentBridge(), host="0.0.0.0", port=port)


if __name__ == "__main__":
    start_modular_agent_bridge()