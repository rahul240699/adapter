"""
Command handling module for NANDA Agent Bridge.
Processes different types of user commands (/, @, #, regular messages).
"""
from typing import Tuple, Optional
from python_a2a import Message, TextContent, MessageRole
from .claude_integration import call_claude, get_agent_id
from .mcp_integration import handle_mcp_command
from .a2a_messaging import A2AMessageHandler
from .logging_utils import log_message


class CommandHandler:
    """Handles different types of user commands and message routing"""
    
    def __init__(self):
        self.agent_id = get_agent_id()
        self.a2a_handler = A2AMessageHandler()
    
    def process_command(self, user_text: str, conversation_id: str, current_path: str, 
                       additional_context: str, msg: Message) -> Message:
        """Process user input and route to appropriate handler"""
        
        # Check if this is a message to another agent (starts with @)
        if user_text.startswith("@"):
            return self._handle_agent_message(user_text, conversation_id, current_path, msg)
        
        # Check if this is an MCP command (starts with #)
        elif user_text.startswith("#"):
            return self._handle_mcp_command(user_text, conversation_id, msg)
        
        # Check if this is a slash command (starts with /)
        elif user_text.startswith("/"):
            return self._handle_slash_command(user_text, conversation_id, current_path, additional_context, msg)
        
        # Regular message - process locally with Claude
        else:
            return self._handle_regular_message(user_text, conversation_id, current_path, additional_context, msg)
    
    def _handle_agent_message(self, user_text: str, conversation_id: str, current_path: str, msg: Message) -> Message:
        """Handle @ messages to other agents"""
        is_agent_msg, target_agent, message_text = self.a2a_handler.parse_user_message(user_text)
        
        if not is_agent_msg or not target_agent or not message_text:
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=f"[AGENT {self.agent_id}] Invalid format. Use '@agent_id message' to send a message."),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )
        
        # TODO: Add message improvement here if enabled
        # if IMPROVE_MESSAGES:
        #     message_text = self.improve_message_direct(message_text)
        #     log_message(conversation_id, current_path, f"Claude {self.agent_id}", message_text)

        print(f"Target agent: {target_agent}")
        print(f"Message text: {message_text}")
        
        # Send to the target agent's bridge
        result = self.a2a_handler.send_to_agent(target_agent, message_text, conversation_id, {
            'path': current_path,
            'source_agent': self.agent_id
        })
        
        # Return result to user
        return Message(
            role=MessageRole.AGENT,
            content=TextContent(text=f"[AGENT {self.agent_id}]: {message_text}"),
            parent_message_id=msg.message_id,
            conversation_id=conversation_id
        )
    
    def _handle_mcp_command(self, user_text: str, conversation_id: str, current_path: str, additional_context: str, msg: Message) -> Message:
        """Handle MCP server queries (#registry:server query)"""
        agent_id = get_agent_id()
        
        # Parse the command
        parts = user_text.split(" ", 1)
        
        if len(parts) > 1 and len(parts[0][1:].split(":", 1)) == 2:
            requested_registry, mcp_server_to_call = parts[0][1:].split(":", 1)
            query = parts[1]
            
            print(f"Requested registry: {requested_registry}, MCP server: {mcp_server_to_call}, query: {query}")
            
            # Use MCP integration
            result = handle_mcp_command(requested_registry, mcp_server_to_call, query)
            
            if result is None:
                return Message(
                    role=MessageRole.AGENT,
                    content=TextContent(text=f"[AGENT {agent_id}] MCP server '{mcp_server_to_call}' not found in registry."),
                    parent_message_id=msg.message_id,
                    conversation_id=conversation_id
                )
            elif result.startswith("Ensure the required API key"):
                return Message(
                    role=MessageRole.AGENT,
                    content=TextContent(text=f"[AGENT {agent_id}] {result}"),
                    parent_message_id=msg.message_id,
                    conversation_id=conversation_id
                )
            
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=result),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )
        else:
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=f"[AGENT {agent_id}] Invalid format. Use '#registry_provider:mcp_server_name query'."),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )
    
    def _handle_slash_command(self, user_text: str, conversation_id: str, current_path: str, 
                             additional_context: str, msg: Message) -> Message:
        """Handle / commands"""
        parts = user_text.split(" ", 1)
        command = parts[0][1:] if len(parts) > 0 else ""
        
        if command == "quit":
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=f"[AGENT {self.agent_id}] Exiting session..."),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )
        
        elif command == "help":
            help_text = """Available commands:
                /help - Show this help message
                /quit - Exit the terminal
                /query [message] - Get a response from the agent privately
                @<agent_id> [message] - Send a message to a specific agent
                #<registry>:<mcp_server> [query] - Query an MCP server"""
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=f"[AGENT {self.agent_id}] {help_text}"),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )
        
        elif command == "query":
            if len(parts) > 1:
                query_text = parts[1].strip()
                print(f"[COMMAND_HANDLER] Processing query command: '{query_text}'")
                
                # Check for empty query
                if not query_text:
                    return Message(
                        role=MessageRole.AGENT,
                        content=TextContent(text=f"[AGENT {self.agent_id}] Error: Empty query provided"),
                        parent_message_id=msg.message_id,
                        conversation_id=conversation_id
                    )

                # Call Claude with the query
                claude_response = call_claude(
                    query_text, 
                    additional_context, 
                    conversation_id, 
                    current_path,
                    "You are Claude, an AI assistant. Provide a direct, helpful response to the user's question. Treat it as a private request for guidance and respond only to the user."
                )
                
                if not claude_response:
                    print("Warning: Claude returned empty response")
                    claude_response = "Sorry, I couldn't process your query. Please try again."
                else:
                    print(f"Claude response received ({len(claude_response)} chars)")
                    print(f"Response preview: {claude_response[:50]}...")

                formatted_response = f"[AGENT {self.agent_id}] {claude_response}"
                
                return Message(
                    role=MessageRole.AGENT,
                    content=TextContent(text=formatted_response),
                    parent_message_id=msg.message_id,
                    conversation_id=conversation_id
                )
            else:
                return Message(
                    role=MessageRole.AGENT,
                    content=TextContent(text=f"[AGENT {self.agent_id}] Please provide a query after the /query command."),
                    parent_message_id=msg.message_id,
                    conversation_id=conversation_id
                )
        else:
            help_text = """Unknown command. Available commands:
                /help - Show this help message
                /quit - Exit the terminal
                /query [message] - Get a response from the agent privately
                @<agent_id> [message] - Send a message to a specific agent
                #<registry>:<mcp_server> [query] - Query an MCP server"""
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=f"[AGENT {self.agent_id}] {help_text}"),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )
    
    def _handle_regular_message(self, user_text: str, conversation_id: str, current_path: str,
                               additional_context: str, msg: Message) -> Message:
        """Handle regular messages with Claude"""
        print(f"[COMMAND_HANDLER] _handle_regular_message() called with user_text: '{user_text}'")
        
        # Check for empty user text
        if not user_text or not user_text.strip():
            print(f"[COMMAND_HANDLER] WARNING: Empty user_text detected")
            formatted_response = f"[AGENT {self.agent_id}] Error: Empty message received"
        else:
            claude_response = call_claude(user_text, additional_context, conversation_id, current_path) or user_text
            formatted_response = f"[AGENT {self.agent_id}] {claude_response}"
        
        return Message(
            role=MessageRole.AGENT,
            content=TextContent(text=formatted_response),
            parent_message_id=msg.message_id,
            conversation_id=conversation_id
        )