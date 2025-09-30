"""
Message routing for NANDA agents.

This module handles routing of messages between agents, including:
- @agent_id routing (send to specific agent)
- /command handling (/query, /help)
- Integration with registry for agent lookup
- Message improvement via pluggable logic
- Loop prevention through depth tracking

Example:
    >>> from nanda_adapter.core.router import MessageRouter
    >>> from nanda_adapter.core.registry import LocalRegistry
    >>>
    >>> registry = LocalRegistry()
    >>> router = MessageRouter("agent_a", registry)
    >>> response = router.route("@agent_b Hello!", "conv_001")
"""

from typing import Optional, Callable
from .registry import LocalRegistry
from .protocol import A2AMessage, format_a2a_message

# Optional dependency - only needed if actually sending messages
try:
    import requests
    from python_a2a import A2AClient, Message, MessageRole, TextContent
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class MessageRouter:
    """
    Routes messages to appropriate handlers.

    The router is responsible for:
    1. Parsing message format (@agent, /command, plain text)
    2. Applying message improvement logic
    3. Looking up agents in the registry
    4. Sending messages via A2A protocol
    5. Preventing infinite loops via depth tracking

    Attributes:
        agent_id: ID of the agent using this router
        registry: Registry for agent lookup
        improver: Optional function to improve/transform messages
        claude_handler: Optional function to query Claude directly
    """

    def __init__(
        self,
        agent_id: str,
        registry: LocalRegistry,
        improver: Optional[Callable[[str], str]] = None,
        claude_handler: Optional[Callable[[str], str]] = None
    ):
        """
        Initialize message router.

        Args:
            agent_id: Unique identifier for this agent
            registry: Registry instance for agent lookup
            improver: Optional function to transform messages before sending
            claude_handler: Optional function to query Claude API

        Raises:
            ValueError: If agent_id is empty or registry is None
        """
        if not agent_id:
            raise ValueError("agent_id cannot be empty")
        if registry is None:
            raise ValueError("registry cannot be None")

        self.agent_id = agent_id
        self.registry = registry
        self.improver = improver
        self.claude_handler = claude_handler

    def route(
        self,
        message: str,
        conversation_id: str,
        depth: int = 0
    ) -> str:
        """
        Route a message to the appropriate handler.

        Determines message type and delegates to the correct handler:
        - @agent_id → _handle_agent_message (send to another agent)
        - /command → _handle_command (execute command)
        - plain text → _handle_default (query Claude or echo)

        Args:
            message: The message to route
            conversation_id: Unique conversation identifier
            depth: Current message depth (for loop prevention)

        Returns:
            Response string from the handler

        Example:
            >>> router.route("@agent_b Hello!", "conv_001")
            '[agent_a] Message sent to agent_b'
            >>> router.route("/help", "conv_001")
            '[agent_a] Available commands: ...'
            >>> router.route("What is 2+2?", "conv_001")
            '[agent_a] 2+2 equals 4'
        """
        message = message.strip()

        if message.startswith('@'):
            return self._handle_agent_message(message, conversation_id, depth)
        elif message.startswith('/'):
            return self._handle_command(message, conversation_id)
        else:
            return self._handle_default(message, conversation_id)

    def _handle_agent_message(
        self,
        message: str,
        conversation_id: str,
        depth: int
    ) -> str:
        """
        Handle @agent_id messages (send to another agent).

        Parses the target agent ID, applies message improvement, looks up
        the agent in the registry, and sends via A2A protocol with depth
        tracking for loop prevention.

        Args:
            message: Message in format "@agent_id message text"
            conversation_id: Unique conversation identifier
            depth: Current depth (incremented for response)

        Returns:
            Status message indicating success or error

        Loop Prevention:
            - Default max_depth is 1 (request-response only)
            - If depth >= max_depth, message is not sent
            - This prevents infinite agent-to-agent loops
        """
        # Check depth limit
        if depth >= 1:  # MVP: Only allow request-response (max_depth=1)
            return f"[{self.agent_id}] Maximum depth reached (depth={depth})"

        # Parse @agent_id from message
        parts = message.split(' ', 1)
        if len(parts) < 2:
            return f"[{self.agent_id}] Invalid format. Use '@agent_id message'"

        target_agent = parts[0][1:]  # Remove @
        message_text = parts[1]

        # Apply improvement if configured
        if self.improver:
            try:
                message_text = self.improver(message_text)
            except Exception as e:
                # Don't fail the whole message if improvement fails
                print(f"Warning: Message improvement failed: {e}")

        # Lookup target agent
        target_url = self.registry.lookup(target_agent)
        if not target_url:
            return f"[{self.agent_id}] Agent '{target_agent}' not found in registry"

        # Create A2A message
        a2a_msg = A2AMessage(
            from_agent=self.agent_id,
            to_agent=target_agent,
            message=message_text,
            conversation_id=conversation_id,
            depth=depth,
            max_depth=1,  # MVP: Only request-response
            message_type="query"
        )

        formatted = format_a2a_message(a2a_msg)

        # Send via HTTP POST (python-a2a client)
        try:
            if not REQUESTS_AVAILABLE:
                return f"[{self.agent_id}] Error: requests library not available"

            # Ensure URL has /a2a path
            if not target_url.endswith('/a2a'):
                target_url = f"{target_url}/a2a"

            client = A2AClient(target_url, timeout=30)
            response = client.send_message(
                Message(
                    role=MessageRole.USER,
                    content=TextContent(text=formatted),
                    conversation_id=conversation_id
                )
            )

            return f"[{self.agent_id}] Message sent to {target_agent}"

        except Exception as e:
            return f"[{self.agent_id}] Error sending to {target_agent}: {str(e)}"

    def _handle_command(self, message: str, conversation_id: str) -> str:
        """
        Handle /command messages.

        Supported commands:
        - /help: Show available commands
        - /query <text>: Query Claude directly (no A2A routing)

        Args:
            message: Message starting with /
            conversation_id: Unique conversation identifier

        Returns:
            Command response or error message
        """
        parts = message.split(' ', 1)
        command = parts[0][1:]  # Remove /

        if command == 'help':
            return self._get_help_text()
        elif command == 'query':
            if len(parts) < 2:
                return f"[{self.agent_id}] Usage: /query <question>"
            return self._query_claude(parts[1])
        else:
            return f"[{self.agent_id}] Unknown command '{command}'. Try /help"

    def _handle_default(self, message: str, conversation_id: str) -> str:
        """
        Handle plain text messages (no @ or /).

        Default behavior is to query Claude if handler is configured,
        otherwise echo the message back.

        Args:
            message: Plain text message
            conversation_id: Unique conversation identifier

        Returns:
            Claude's response or echo
        """
        return self._query_claude(message)

    def _query_claude(self, query: str) -> str:
        """
        Query Claude API directly (no A2A routing).

        Uses the claude_handler function if provided, otherwise returns
        a message indicating Claude is not configured.

        Args:
            query: Question or prompt for Claude

        Returns:
            Claude's response or error message
        """
        if not self.claude_handler:
            return f"[{self.agent_id}] Claude handler not configured"

        try:
            response = self.claude_handler(query)
            return f"[{self.agent_id}] {response}"
        except Exception as e:
            return f"[{self.agent_id}] Error querying Claude: {str(e)}"

    def _get_help_text(self) -> str:
        """
        Generate help text listing available commands.

        Returns:
            Formatted help text
        """
        return f"""[{self.agent_id}] Available commands:
  /help - Show this message
  /query <question> - Ask Claude directly (no agent routing)
  @<agent_id> <message> - Send message to another agent

Examples:
  @agent_b What is the capital of France?
  /query Explain the A2A protocol
  /help"""