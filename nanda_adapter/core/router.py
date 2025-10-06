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

import asyncio
from typing import Optional, Callable
from .registry import LocalRegistry, RegistryInterface
from .protocol import A2AMessage, format_a2a_message

# Optional dependency - only needed if actually sending messages
try:
    import requests
    from python_a2a import A2AClient, Message, MessageRole, TextContent
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# MCP support imports
try:
    from .mcp_registry import create_mcp_registry, MCPRegistry
    from .mcp_client import MCPClient
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    create_mcp_registry = None
    MCPRegistry = None

# Payment middleware imports
try:
    from .payment_middleware import create_payment_middleware, PaymentStatus
    PAYMENT_AVAILABLE = True
except ImportError:
    PAYMENT_AVAILABLE = False


def form_mcp_server_url(endpoint: str, config: dict, registry_provider: str) -> str:
    """
    Form complete MCP server URL from endpoint and configuration.
    
    Args:
        endpoint: Base MCP server endpoint 
        config: Additional configuration (API keys, etc.)
        registry_provider: The registry provider name
        
    Returns:
        Complete MCP server URL or None if missing requirements
    """
    try:
        # Handle different endpoint formats
        if endpoint.startswith('http'):
            # Already a complete URL
            base_url = endpoint
        elif endpoint.startswith('/'):
            # Relative path - need to form full URL
            # This would depend on your MCP server hosting setup
            base_url = f"http://localhost:3000{endpoint}"
        else:
            # Assume it's a service name that needs full URL construction
            base_url = f"http://{endpoint}"

        # Add API keys or other config parameters as needed
        # This is where you'd handle provider-specific URL formation
        if 'api_key' in config:
            # Some MCP servers may need API keys in URL or headers
            pass

        return base_url
        
    except Exception as e:
        print(f"Error forming MCP server URL: {e}")
        return None


async def run_mcp_query(query: str, mcp_server_url: str) -> str:
    """
    Execute an async MCP query against the specified server.
    
    Args:
        query: The query string to send to MCP server
        mcp_server_url: Complete URL of the MCP server
        
    Returns:
        Response from MCP server or error message
    """
    try:
        # Use the MCP client to execute the query
        async with MCPClient() as client:
            result = await client.process_query(query, mcp_server_url)
            return result
            
    except Exception as e:
        return f"MCP query error: {str(e)}"


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
        registry: RegistryInterface,
        improver: Optional[Callable[[str], str]] = None,
        claude_handler: Optional[Callable[[str], str]] = None,
        mcp_registry = None
    ):
        """
        Initialize message router.

        Args:
            agent_id: Unique identifier for this agent
            registry: Registry instance for agent lookup
            improver: Optional function to transform messages before sending
            claude_handler: Optional function to query Claude API
            mcp_registry: Optional MCP registry for MCP server lookup

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
        
        # Initialize MCP registry
        self.mcp_registry = mcp_registry or (create_mcp_registry() if MCP_AVAILABLE else None)
        if self.mcp_registry:
            print(f"✅ MCP support enabled for {agent_id}")
        else:
            print(f"⚠️  MCP support disabled for {agent_id} (registry not available)")
        
        # Initialize payment middleware
        self.payment_middleware = create_payment_middleware(registry, self.mcp_registry) if PAYMENT_AVAILABLE else None
        if self.payment_middleware:
            print(f"💰 Payment middleware enabled for {agent_id}")
        else:
            print(f"⚠️  Payment middleware disabled for {agent_id}")

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
        - #registry:server → _handle_mcp_message (query MCP server)
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
            >>> router.route("#nanda:payments-server get invoice 123", "conv_001")
            '[MCP] Invoice details: ...'
            >>> router.route("/help", "conv_001")
            '[agent_a] Available commands: ...'
            >>> router.route("What is 2+2?", "conv_001")
            '[agent_a] 2+2 equals 4'
        """
        message = message.strip()

        if message.startswith('@'):
            return self._handle_agent_message(message, conversation_id, depth)
        elif message.startswith('#'):
            return self._handle_mcp_message(message, conversation_id)
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
        if depth >= 2:  # Allow request-response (depth 0->1), block deeper (max_depth=2)
            return f"[{self.agent_id}] Maximum depth reached (depth={depth})"

        # Parse @agent_id from message
        parts = message.split(' ', 1)
        if len(parts) < 2:
            return f"[{self.agent_id}] Invalid format. Use '@agent_id message'"

        target_agent = parts[0][1:]  # Remove @
        message_text = parts[1]

        # Apply message improvement if available
        if self.improver:
            message_text = self.improver(message_text)

        # Look up target agent
        target_url = self.registry.lookup(target_agent)
        if not target_url:
            return f"[{self.agent_id}] Agent '{target_agent}' not found in registry"

        # Payment processing
        if self.payment_middleware:
            # Check if message contains receipt (for paid requests)
            receipt_id = self.payment_middleware.extract_receipt_from_message(message_text)
            
            if receipt_id:
                # Validate receipt before processing
                import asyncio
                validation_result = asyncio.run(self.payment_middleware.validate_receipt(receipt_id))
                
                if validation_result.status != PaymentStatus.PAID:
                    return f"[{self.agent_id}] Invalid receipt: {validation_result.message}"
                
                print(f"💰 Payment validated: {validation_result.message}")
                # Continue with message processing...
            else:
                # Check if target requires payment
                payment_check = self.payment_middleware.check_payment_requirement(target_agent)
                
                if payment_check.status == PaymentStatus.REQUIRED:
                    # Return 402 Payment Required
                    return self.payment_middleware.format_payment_required_response(payment_check, target_agent)

        # Create A2A message with depth tracking
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

            # Return the actual response from the target agent
            if response and hasattr(response, 'content') and response.content:
                response_text = response.content.text if hasattr(response.content, 'text') else str(response.content)
                
                # Check if response is a payment request (402)
                if self.payment_middleware and "402-PAYMENT-REQUIRED" in response_text:
                    # Extract amount from payment request
                    import re
                    amount_match = re.search(r'(\d+)\s*NP', response_text)
                    if amount_match:
                        amount = int(amount_match.group(1))
                        print(f"💰 Payment required: {amount} NP for {target_agent}")
                        
                        # Automatically process payment
                        payment_result = asyncio.run(
                            self.payment_middleware.process_payment(
                                self.agent_id, 
                                target_agent, 
                                amount
                            )
                        )
                        
                        if payment_result.status == PaymentStatus.PAID:
                            # Payment successful - retry request with receipt
                            print(f"✅ Payment processed: {payment_result.receipt_id}")
                            
                            # Add receipt to original message and retry
                            message_with_receipt = f"{message_text} #receipt:{payment_result.receipt_id}"
                            
                            # Create new A2A message with receipt
                            a2a_msg_retry = A2AMessage(
                                from_agent=self.agent_id,
                                to_agent=target_agent,
                                message=message_with_receipt,
                                conversation_id=conversation_id,
                                depth=depth,
                                max_depth=1,
                                message_type="query"
                            )
                            
                            formatted_retry = format_a2a_message(a2a_msg_retry)
                            
                            # Retry the request
                            retry_response = client.send_message(
                                Message(
                                    role=MessageRole.USER,
                                    content=TextContent(text=formatted_retry),
                                    conversation_id=conversation_id
                                )
                            )
                            
                            if retry_response and hasattr(retry_response, 'content') and retry_response.content:
                                retry_text = retry_response.content.text if hasattr(retry_response.content, 'text') else str(retry_response.content)
                                return f"[{target_agent} → {self.agent_id}] {retry_text}"
                            else:
                                return f"[{self.agent_id}] Payment processed, message sent to {target_agent}"
                        else:
                            # Payment failed
                            return f"[{self.agent_id}] Payment failed: {payment_result.message}"
                    else:
                        return f"[{target_agent} → {self.agent_id}] {response_text}"
                else:
                    return f"[{target_agent} → {self.agent_id}] {response_text}"
            else:
                return f"[{self.agent_id}] Message sent to {target_agent} (no response)"

        except Exception as e:
            return f"[{self.agent_id}] Error sending to {target_agent}: {str(e)}"

    def _handle_mcp_message(self, message: str, conversation_id: str) -> str:
        """
        Handle #registry:server messages (query MCP server).

        Parses the registry provider and server name, looks up the server
        in the MCP registry, and executes the query via MCP client.

        Args:
            message: Message in format "#registry:server query text"
            conversation_id: Unique conversation identifier

        Returns:
            MCP server response or error message

        Examples:
            #nanda:payments get invoice 123
            #smithery:weather what's the weather in NYC?
        """
        if not MCP_AVAILABLE:
            return f"[{self.agent_id}] MCP support not available (missing dependencies)"
            
        if not self.mcp_registry:
            return f"[{self.agent_id}] MCP registry not configured"

        # Parse the command format: #registry:server query
        parts = message.split(' ', 1)
        if len(parts) < 2:
            return f"[{self.agent_id}] Invalid MCP format. Use '#registry:server query'"

        # Parse registry and server from first part
        mcp_part = parts[0][1:]  # Remove #
        query = parts[1]

        if ':' not in mcp_part:
            return f"[{self.agent_id}] Invalid MCP format. Use '#registry:server query'"

        registry_provider, server_name = mcp_part.split(':', 1)

        try:
            print(f"🔍 Looking up MCP server: {server_name} in {registry_provider}")
            
            # Look up server in MCP registry
            server_config = self.mcp_registry.lookup_server(registry_provider, server_name)
            
            if not server_config:
                # Try lookup by simple name as fallback
                server_config = self.mcp_registry.lookup_server_by_name(server_name)
                
            if not server_config:
                return f"[{self.agent_id}] MCP server '{server_name}' not found in registry '{registry_provider}'"

            # Extract server details
            endpoint = server_config.get("endpoint")
            config = server_config.get("config", {})
            actual_provider = server_config.get("registry_provider", registry_provider)

            if not endpoint:
                return f"[{self.agent_id}] Invalid MCP server configuration (missing endpoint)"

            print(f"✅ Found MCP server: {endpoint}")

            # Form complete MCP server URL
            mcp_server_url = form_mcp_server_url(endpoint, config, actual_provider)
            
            if not mcp_server_url:
                return f"[{self.agent_id}] Could not form MCP server URL (check API keys)"

            print(f"🚀 Querying MCP server: {query}")

            # Run MCP query asynchronously
            result = asyncio.run(run_mcp_query(query, mcp_server_url))
            
            return f"[MCP:{server_name}] {result}"

        except Exception as e:
            return f"[{self.agent_id}] Error querying MCP server '{server_name}': {str(e)}"

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