"""
Agent-to-Agent (A2A) communication module for NANDA Agent Bridge.
Handles structured agent messaging, external message parsing, and agent communication protocols.
"""
import uuid
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from python_a2a import A2AClient, Message, TextContent, MessageRole, Metadata
from .registry import lookup_agent
from .communication import send_to_ui_client, send_to_terminal, get_local_terminal_url, is_ui_mode
from .claude_integration import get_agent_id, call_claude


class MessageDirection(Enum):
    """Direction of message flow"""
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class MessageType(Enum):
    """Types of messages in A2A communication"""
    USER_TO_AGENT = "user_to_agent"
    AGENT_TO_AGENT = "agent_to_agent"
    AGENT_REPLY = "agent_reply"
    SYSTEM_MESSAGE = "system_message"


@dataclass
class A2AMessage:
    """Structured representation of an A2A message"""
    from_agent: str
    to_agent: str
    content: str
    message_type: MessageType
    conversation_id: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass 
class A2AMessageEnvelope:
    """External message envelope format"""
    from_agent: str
    to_agent: str
    message_start: str
    message_end: str
    content: str
    
    @classmethod
    def parse(cls, message_text: str) -> Optional['A2AMessageEnvelope']:
        """Parse external message format into structured envelope"""
        try:
            print(f"[A2A_ENVELOPE] parse() called with message_text length: {len(message_text)}")
            print(f"[A2A_ENVELOPE] parse() message_text: '{message_text}'")
            
            lines = message_text.split('\n')
            print(f"[A2A_ENVELOPE] parse() split into {len(lines)} lines")
            
            # Check if this is our special format
            if not lines or lines[0] != '__EXTERNAL_MESSAGE__':
                print(f"[A2A_ENVELOPE] parse() ERROR: Not our special format. First line: '{lines[0] if lines else 'NO LINES'}'")
                return None
            
            from_agent = None
            to_agent = None
            message_content = ""
            
            # Parse the header fields
            in_message = False
            for i, line in enumerate(lines[1:], 1):
                print(f"[A2A_ENVELOPE] parse() Line {i}: '{line}' (in_message: {in_message})")
                if line.startswith('__FROM_AGENT__'):
                    from_agent = line[len('__FROM_AGENT__'):]
                    print(f"[A2A_ENVELOPE] parse() Found from_agent: '{from_agent}'")
                elif line.startswith('__TO_AGENT__'):
                    to_agent = line[len('__TO_AGENT__'):]
                    print(f"[A2A_ENVELOPE] parse() Found to_agent: '{to_agent}'")
                elif line == '__MESSAGE_START__':
                    in_message = True
                    print(f"[A2A_ENVELOPE] parse() MESSAGE_START found, in_message=True")
                elif line == '__MESSAGE_END__':
                    in_message = False
                    print(f"[A2A_ENVELOPE] parse() MESSAGE_END found, in_message=False")
                elif in_message:
                    message_content += line + '\n'
                    print(f"[A2A_ENVELOPE] parse() Added to message_content: '{line}'")
            
            # Trim trailing newline
            message_content = message_content.rstrip()
            print(f"[A2A_ENVELOPE] parse() Final message_content: '{message_content}'")
            print(f"[A2A_ENVELOPE] parse() Final message_content length: {len(message_content)}")
            
            if from_agent and to_agent:
                print(f"[A2A_ENVELOPE] parse() SUCCESS: Creating envelope with from={from_agent}, to={to_agent}, content='{message_content}'")
                return cls(
                    from_agent=from_agent,
                    to_agent=to_agent,
                    message_start='__MESSAGE_START__',
                    message_end='__MESSAGE_END__',
                    content=message_content
                )
            print(f"[A2A_ENVELOPE] parse() ERROR: Missing agents. from_agent={from_agent}, to_agent={to_agent}")
            return None
            
        except Exception as e:
            print(f"Error parsing A2A message envelope: {e}")
            return None
    
    def format(self) -> str:
        """Format envelope back to external message format"""
        return f"__EXTERNAL_MESSAGE__\n__FROM_AGENT__{self.from_agent}\n__TO_AGENT__{self.to_agent}\n{self.message_start}\n{self.content}\n{self.message_end}"


class A2AMessageHandler:
    """Handles A2A message processing and routing"""
    
    def __init__(self):
        self.agent_id = get_agent_id()
    
    def send_to_agent(self, target_agent_id: str, message_text: str, conversation_id: str, metadata: Dict[str, Any] = None) -> str:
        """Send a message to another agent via their bridge"""
        # Look up the agent in the registry
        agent_url = lookup_agent(target_agent_id)
        if not agent_url:
            return f"Agent {target_agent_id} not found in registry"
        
        try:
            if not agent_url.endswith('/a2a'):
                target_bridge_url = f"{agent_url}/a2a"
                print(f"Adding /a2a to URL: {target_bridge_url}")
            else:
                target_bridge_url = agent_url
                print(f"URL already includes /a2a: {target_bridge_url}")

            # Use source_agent from metadata if provided, otherwise fall back to self.agent_id
            sending_agent_id = metadata.get('source_agent', self.agent_id) if metadata else self.agent_id
            
            print(f"🚀 Sending message from agent '{sending_agent_id}' to '{target_agent_id}' at {target_bridge_url}")
            print(f"📝 Message content: {message_text[:100]}...")

            # Create A2A message envelope with correct sending agent ID
            envelope = A2AMessageEnvelope(
                from_agent=sending_agent_id,
                to_agent=target_agent_id,
                message_start='__MESSAGE_START__',
                message_end='__MESSAGE_END__',
                content=message_text
            )
            
            print(f"📋 A2A Envelope: FROM={envelope.from_agent} TO={envelope.to_agent}")
            formatted_message = envelope.format()
            print(f"📨 Formatted message preview: {formatted_message[:200]}...")
            
            # Create simplified metadata with correct agent IDs
            send_metadata = {
                'is_external': True,
                'from_agent_id': sending_agent_id,
                'to_agent_id': target_agent_id,
                'message_type': MessageType.AGENT_TO_AGENT.value
            }
            
            if metadata:
                send_metadata.update(metadata)
                
            print(f"Custom Fields being sent: {send_metadata}")

            # Send message to the target agent's bridge
            bridge_client = A2AClient(target_bridge_url, timeout=30)
            response = bridge_client.send_message(
                Message(
                    role=MessageRole.USER,
                    content=TextContent(text=formatted_message),
                    conversation_id=conversation_id,
                    metadata=Metadata(custom_fields=send_metadata)
                )
            )
            
            return f"Message sent to {target_agent_id}"
        except Exception as e:
            print(f"Error sending message to {target_agent_id}: {e}")
            return f"Error sending message to {target_agent_id}: {e}"
    
    def handle_external_message(self, msg_text: str, conversation_id: str, msg: Message) -> Optional[Message]:
        """Handle specially formatted external messages - CURRENT SIMPLE VERSION"""
        try:
            # Parse the message envelope
            envelope = A2AMessageEnvelope.parse(msg_text)
            if not envelope:
                return None
            
            print(f"Received external message from {envelope.from_agent} to {envelope.to_agent}")
            
            # Format the message for display
            formatted_text = f"FROM {envelope.from_agent}: {envelope.content}"
            
            print("Message Text: ", envelope.content)
            print("UI MODE: ", is_ui_mode())

            # Forward to UI or terminal based on mode
            if is_ui_mode():
                print(f"Forwarding message to UI client")
                send_to_ui_client(formatted_text, envelope.from_agent, conversation_id)
            else:
                # Forward to local terminal
                try:
                    send_to_terminal(
                        formatted_text,
                        get_local_terminal_url(), 
                        conversation_id,
                        {
                            'is_from_peer': True,
                            'is_user_message': True,
                            'source_agent': envelope.from_agent,
                            'forwarded_by_bridge': True
                        }
                    )
                except Exception as e:
                    print(f"Error forwarding to local terminal: {e}")
                    return Message(
                        role=MessageRole.AGENT,
                        content=TextContent(text=f"Failed to deliver message: {str(e)}"),
                        parent_message_id=msg.message_id,
                        conversation_id=conversation_id
                    )
            
            # Return simple acknowledgment using the actual receiving agent ID
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=f"Message received by Agent {envelope.to_agent}"),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )
            
        except Exception as e:
            print(f"Error parsing external message: {e}")
            return None
    
    def handle_external_message_with_reply(self, msg_text: str, conversation_id: str, msg: Message) -> Optional[Message]:
        """Handle external messages with automatic reply generation - ENHANCED VERSION"""
        try:
            print(f"[A2A_MESSAGING] handle_external_message_with_reply() called")
            print(f"[A2A_MESSAGING] Input msg_text length: {len(msg_text)}")
            print(f"[A2A_MESSAGING] Input msg_text preview: '{msg_text[:200]}...'")
            
            # 1. Message parsing and validation
            envelope = A2AMessageEnvelope.parse(msg_text)
            if not envelope:
                print("[A2A_MESSAGING] ERROR: Failed to parse external message envelope")
                return None
            
            from_agent = envelope.from_agent
            to_agent = envelope.to_agent  
            message_content = envelope.content
            
            print(f"[A2A_MESSAGING] Enhanced A2A: Received message from {from_agent} to {to_agent}")
            print(f"[A2A_MESSAGING] Parsed envelope.content: '{message_content}'")
            
            # 2. Context building for reply generation  
            from .claude_integration import call_claude
            
            # Use the actual receiving agent ID from the message envelope, not environment
            receiving_agent_id = to_agent
            print(f"[A2A_MESSAGING] Enhanced handler: Using receiving agent ID from message: {receiving_agent_id}")
            print(f"[A2A_MESSAGING] Enhanced handler: Message content length: {len(message_content)}")
            print(f"[A2A_MESSAGING] Enhanced handler: Message content: '{message_content}'")
            
            reply_context = f"""
You have received a message from agent '{from_agent}' that says: "{message_content}"

As agent '{receiving_agent_id}', provide an intelligent, helpful response. Consider:
- The content and intent of their message
- How you can be most helpful to them  
- Your role and capabilities as agent '{receiving_agent_id}'
- Keep your response concise but meaningful

Respond directly to their message content - do not explain that you're generating a response.
"""
            
            print(f"[A2A_MESSAGING] Enhanced handler: Reply context length: {len(reply_context)}")
            print(f"[A2A_MESSAGING] Enhanced handler: Reply context preview: '{reply_context[:200]}...'")
            
            # 3. Claude integration for intelligent replies
            print(f"[A2A_MESSAGING] Enhanced handler: Calling Claude with receiving_agent_id: {receiving_agent_id}")
            intelligent_reply = call_claude(
                reply_context, 
                "", 
                conversation_id, 
                f"{from_agent}>{receiving_agent_id}",
                f"You are {receiving_agent_id}, an AI assistant agent. Respond thoughtfully and helpfully to messages from other agents in the network.",
                agent_id=receiving_agent_id  # Pass the correct agent ID
            )
            
            print(f"[A2A_MESSAGING] Enhanced handler: Claude returned: '{intelligent_reply}'")
            
            if not intelligent_reply:
                # Fallback to contextual acknowledgment
                intelligent_reply = f"Hello {from_agent}, I received your message about: {message_content[:50]}... How can I help you with this?"
            
            # Forward incoming message to UI/terminal (same as simple version)
            formatted_text = f"FROM {from_agent}: {message_content}"
            
            if is_ui_mode():
                print(f"Forwarding incoming message to UI client")
                send_to_ui_client(formatted_text, from_agent, conversation_id)
            else:
                try:
                    send_to_terminal(
                        formatted_text,
                        get_local_terminal_url(), 
                        conversation_id,
                        {
                            'is_from_peer': True,
                            'is_user_message': True,
                            'source_agent': from_agent,
                            'forwarded_by_bridge': True
                        }
                    )
                except Exception as e:
                    print(f"Error forwarding to local terminal: {e}")
            
            # 4. Reply routing back to sender (for future implementation)
            # TODO: Implement automatic reply routing back to sender agent
            # This would involve:
            # - Looking up sender agent URL in registry
            # - Formatting reply as external message
            # - Sending reply back to sender's bridge
            
            # 5. Return intelligent reply to current conversation
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=f"[AGENT {receiving_agent_id}] {intelligent_reply}"),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )
            
        except Exception as e:
            # 6. Proper error handling and fallbacks
            print(f"Error in enhanced external message handling: {e}")
            # Fall back to simple handling
            return self.handle_external_message(msg_text, conversation_id, msg)
    
    def parse_user_message(self, user_text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Parse user input to determine if it's an agent-targeted message"""
        if user_text.startswith("@"):
            parts = user_text.split(" ", 1)
            if len(parts) > 1:
                target_agent = parts[0][1:]  # Remove the @ symbol
                message_text = parts[1]
                return True, target_agent, message_text
            else:
                return True, None, None  # Invalid format
        return False, None, None
    
    def create_a2a_message(self, from_agent: str, to_agent: str, content: str, 
                          message_type: MessageType, conversation_id: str, 
                          metadata: Dict[str, Any] = None) -> A2AMessage:
        """Create a structured A2A message"""
        return A2AMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            conversation_id=conversation_id,
            metadata=metadata or {}
        )