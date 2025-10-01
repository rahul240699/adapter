"""
SimpleNANDA - Minimal entry point for local agent development.

This module provides a streamlined interface for creating NANDA agents
without requiring external registries, SSL certificates, or complex configuration.

Perfect for:
- Local development and testing
- Multi-agent experimentation
- Learning the A2A protocol
- Rapid prototyping

Example:
    >>> from nanda_adapter.simple import SimpleNANDA
    >>>
    >>> # Create agent with Claude
    >>> agent = SimpleNANDA('my_agent', 'localhost:6000')
    >>> agent.start()
    >>>
    >>> # Create agent with custom logic (no Claude needed)
    >>> def uppercase(text): return text.upper()
    >>> agent = SimpleNANDA(
    ...     'simple_agent',
    ...     'localhost:6002',
    ...     improvement_logic=uppercase,
    ...     require_anthropic=False
    ... )
    >>> agent.start()
"""

import os
from typing import Optional, Callable

from .core.registry import LocalRegistry, create_registry, RegistryInterface
from .core.router import MessageRouter
from .core.protocol import parse_a2a_message, is_a2a_message
from .core.logger import ConversationLogger
from .core.network_utils import get_public_url, print_network_debug_info
from .core.env_loader import load_env_vars
# A2A messaging imports removed - using standard protocol
from .core.claude_integration import call_claude

# Optional dependencies
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from python_a2a import A2AServer, Message, MessageRole, TextContent, run_server
    A2A_AVAILABLE = True
except ImportError:
    A2A_AVAILABLE = False


class SimpleNANDA:
    """
    Minimal NANDA adapter for local development.

    SimpleNANDA provides a streamlined interface for creating agents that
    communicate via the A2A protocol, with file-based registry and optional
    Claude integration.

    Attributes:
        agent_id: Unique identifier for this agent
        host: Host string in format "hostname:port" (e.g., "localhost:6000")
        hostname: Extracted hostname from host parameter
        port: Extracted port number from host parameter
        registry: Registry instance for agent discovery (LocalRegistry or MongoRegistry)
        router: MessageRouter for handling messages
        logger: ConversationLogger for JSONL logging
        improvement_logic: Optional function to transform outgoing messages

    Loop Prevention:
        - Messages include depth tracking
        - Default max_depth=1 (request-response only)
        - Prevents infinite agent-to-agent loops

    Example:
        >>> agent = SimpleNANDA('agent_a', 'localhost:6000')
        >>> agent.start()  # Starts server, blocks until interrupted
    """

    def __init__(
        self,
        agent_id: str,
        host: str = "localhost:6000",
        improvement_logic: Optional[Callable[[str], str]] = None,
        anthropic_api_key: Optional[str] = None,
        require_anthropic: bool = True,
        registry: Optional[RegistryInterface] = None,
        log_dir: str = "./logs"
    ):
        """
        Initialize SimpleNANDA agent.

        Args:
            agent_id: Unique identifier for this agent
            host: Host in "hostname:port" format (default: "localhost:6000")
                  Supports: "localhost:6000", "192.168.1.100:6002", etc.
            improvement_logic: Optional function to transform messages
            anthropic_api_key: Claude API key (or set ANTHROPIC_API_KEY env var)
            require_anthropic: Whether Claude is required (default: True)
            registry: Custom registry instance (default: auto-detected from .env)
            log_dir: Base directory for conversation logs (default: "./logs")

        Raises:
            ValueError: If agent_id is empty
            ValueError: If require_anthropic=True but no API key provided
            ValueError: If host format is invalid
            ImportError: If required dependencies are missing

        Example:
            >>> # With Claude (requires ANTHROPIC_API_KEY)
            >>> agent = SimpleNANDA('agent_a', 'localhost:6000')
            >>>
            >>> # Without Claude (custom logic only)
            >>> def my_logic(text): return text.upper()
            >>> agent = SimpleNANDA(
            ...     'agent_a',
            ...     'localhost:6000',
            ...     improvement_logic=my_logic,
            ...     require_anthropic=False
            ... )
            >>>
            >>> # On specific host/IP
            >>> agent = SimpleNANDA('agent_a', '192.168.1.100:6000')
        """
        if not agent_id:
            raise ValueError("agent_id cannot be empty")

        if not A2A_AVAILABLE:
            raise ImportError(
                "python-a2a library is required. Install with: pip install python-a2a"
            )

        self.agent_id = agent_id
        self.improvement_logic = improvement_logic

        # Load environment configuration for EC2 support
        env_vars = load_env_vars()
        
        # Network configuration with EC2 auto-detection
        self._setup_networking(host, env_vars)

        # Initialize registry (use provided or create based on .env config)
        self.registry = registry or create_registry()

        # Lazy-initialize Anthropic client (Bug fix - see docs/BUGS_AND_ISSUES.md)
        self._anthropic_client = None
        if require_anthropic:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError(
                    "anthropic library is required for Claude integration. "
                    "Install with: pip install anthropic\n"
                    "Or set require_anthropic=False to disable Claude."
                )

            self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.anthropic_api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY required for Claude integration.\n"
                    "Set via environment or pass anthropic_api_key parameter.\n"
                    "To disable Claude: SimpleNANDA(..., require_anthropic=False)"
                )
        else:
            self.anthropic_api_key = None

        # Initialize logger
        self.logger = ConversationLogger(agent_id, log_dir)

        # Initialize router
        self.router = MessageRouter(
            agent_id=agent_id,
            registry=self.registry,
            improver=improvement_logic,
            claude_handler=self._call_claude if require_anthropic else None
        )

        # A2A message handler removed - using standard protocol

        # Register with registry using public URL for EC2 compatibility
        self.registry.register(agent_id, self.public_url)

        print(f"✓ Agent '{agent_id}' initialized")
        print(f"✓ Public URL: {self.public_url}")
        print(f"✓ Internal bind: {self.internal_host}:{self.port}")
        
        # Show registry type and info
        if hasattr(self.registry, 'registry_file'):
            print(f"✓ Registry: LocalRegistry ({self.registry.registry_file})")
        elif hasattr(self.registry, 'database_name'):
            print(f"✓ Registry: MongoRegistry ({self.registry.database_name}.{self.registry.collection_name})")
        else:
            print(f"✓ Registry: {type(self.registry).__name__}")
            
        print(f"✓ Logs: {self.logger.agent_log_dir}")

    def _setup_networking(self, host: str, env_vars: dict) -> None:
        """
        Setup networking configuration with EC2 auto-detection support.
        
        Args:
            host: Host parameter from constructor (for backward compatibility)
            env_vars: Environment variables loaded from .env
        """
        # Determine port - environment variable takes precedence
        env_port = env_vars.get("PORT")
        if env_port:
            try:
                self.port = int(env_port)
            except ValueError:
                print(f"⚠️  Invalid PORT in environment: {env_port}, using default 6000")
                self.port = 6000
        else:
            # Parse from host parameter (backward compatibility)
            if ':' in host:
                try:
                    _, port_str = host.rsplit(':', 1)
                    self.port = int(port_str)
                except ValueError:
                    print(f"⚠️  Invalid port in host '{host}', using default 6000")
                    self.port = 6000
            else:
                self.port = 6000
        
        # Internal host binding (for server)
        self.internal_host = env_vars.get("INTERNAL_HOST", "0.0.0.0")
        
        # Determine public URL for registration
        preferred_url = env_vars.get("PUBLIC_URL", "auto")
        self.public_url = get_public_url(self.port, preferred_url)
        
        # For backward compatibility, set hostname (used by server binding)
        if ':' in host:
            self.hostname = host.split(':')[0]
        else:
            self.hostname = "localhost"
        
        # Override hostname for EC2
        if self.internal_host == "0.0.0.0":
            self.hostname = "0.0.0.0"
        
        # Debug info if requested
        if env_vars.get("DEBUG", "false").lower() == "true":
            print_network_debug_info()

    def _parse_host(self, host: str) -> None:
        """
        Parse host:port string.

        Args:
            host: String in format "hostname:port"

        Raises:
            ValueError: If format is invalid or port is not a number

        Example:
            >>> agent._parse_host("localhost:6000")
            >>> agent.hostname
            'localhost'
            >>> agent.port
            6000
        """
        if ':' not in host:
            raise ValueError(
                f"Invalid host format '{host}'. Expected 'hostname:port' "
                f"(e.g., 'localhost:6000' or '192.168.1.100:6002')"
            )

        hostname, port_str = host.rsplit(':', 1)

        if not hostname:
            raise ValueError(f"Hostname cannot be empty in '{host}'")

        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port '{port_str}' in '{host}'. Must be a number.")

        if port < 1 or port > 65535:
            raise ValueError(f"Port {port} out of range (1-65535)")

        self.hostname = hostname
        self.port = port

    @property
    def agent_url(self) -> str:
        """
        Get the agent's public URL for registration and display.
        
        Returns:
            Public URL where this agent can be reached
        """
        return self.public_url

    @property
    def anthropic(self) -> Optional[Anthropic]:
        """
        Lazy-load Anthropic client (Bug fix).

        Returns:
            Anthropic client instance or None if not configured

        Note:
            Client is only created when first accessed, not at initialization.
            This allows agents to work without an API key if they don't use Claude.
        """
        if self._anthropic_client is None and self.anthropic_api_key:
            self._anthropic_client = Anthropic(api_key=self.anthropic_api_key)
        return self._anthropic_client

    def _call_claude(self, prompt: str) -> str:
        """
        Call Claude API.

        Args:
            prompt: Question or prompt for Claude

        Returns:
            Claude's response text

        Raises:
            Exception: If API call fails (caught by router)
        """
        if not self.anthropic:
            return f"Claude not configured (require_anthropic=False)"

        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def start(self) -> None:
        """
        Start the A2A server.

        Starts the agent server and blocks until interrupted (Ctrl+C).
        The server listens on the configured host:port and handles
        incoming A2A messages.

        Loop Prevention:
            - Incoming messages with depth >= max_depth are logged but not responded to
            - This prevents infinite agent-to-agent loops
            - Default max_depth=1 allows only request-response pattern

        Raises:
            KeyboardInterrupt: When server is stopped with Ctrl+C

        Example:
            >>> agent = SimpleNANDA('agent_a', 'localhost:6000')
            >>> agent.start()  # Blocks until Ctrl+C
            🚀 Agent 'agent_a' starting on localhost:6000
            📍 Registered at http://localhost:6000
            ^C
            Shutting down...
        """
        class AgentServer(A2AServer):
            def __init__(self, parent):
                # Use the public URL for A2AServer (for EC2 compatibility)
                super().__init__(url=parent.public_url)
                self.parent = parent

            def handle_message(self, msg: Message) -> Message:
                conversation_id = msg.conversation_id or "default"
                user_text = msg.content.text

                # print(f"[SIMPLE_NANDA] {self.parent.agent_id} received: '{user_text[:100]}...'")
                
                # Log incoming
                self.parent.logger.log(conversation_id, "incoming", user_text)

                # Check if standard A2A external message
                if is_a2a_message(user_text):
                    print(f"[SIMPLE_NANDA] Detected standard A2A message format")
                    a2a_msg = parse_a2a_message(user_text)
                    if a2a_msg:
                        # Set conversation_id from context
                        a2a_msg.conversation_id = conversation_id

                        # Check if we should respond (depth limit)
                        if a2a_msg.depth >= a2a_msg.max_depth:
                            # Just log, don't respond (loop prevention)
                            response_text = (
                                f"[{self.parent.agent_id}] Response logged "
                                f"(max depth {a2a_msg.max_depth} reached)"
                            )
                            self.parent.logger.log(
                                conversation_id,
                                "response_logged",
                                a2a_msg.message,
                                metadata={
                                    "from_agent": a2a_msg.from_agent,
                                    "depth": a2a_msg.depth,
                                    "max_depth": a2a_msg.max_depth
                                }
                            )
                        else:
                            # Generate response via Claude
                            if self.parent.router.claude_handler:
                                try:
                                    claude_response = self.parent._call_claude(a2a_msg.message)
                                    response_text = f"[{self.parent.agent_id}] {claude_response}"
                                except Exception as e:
                                    response_text = f"[{self.parent.agent_id}] Error: {str(e)}"
                            else:
                                response_text = (
                                    f"[{self.parent.agent_id}] Received from "
                                    f"{a2a_msg.from_agent}: {a2a_msg.message}"
                                )
                    else:
                        response_text = "Invalid A2A message format"
                else:
                    # Regular message or @agent routing - use the router
                    print(f"[SIMPLE_NANDA] Processing message through router")
                    if user_text.strip().startswith('@'):
                        print(f"[SIMPLE_NANDA] Detected @agent routing request")
                    response_text = self.parent.router.route(user_text, conversation_id)

                print(f"[SIMPLE_NANDA] {self.parent.agent_id} responding with: '{response_text[:100]}...'")
                
                # Log outgoing
                self.parent.logger.log(conversation_id, "outgoing", response_text)

                return Message(
                    role=MessageRole.AGENT,
                    content=TextContent(text=response_text),
                    parent_message_id=msg.message_id,
                    conversation_id=conversation_id
                )

        server = AgentServer(self)
        print(f"\n🚀 Agent '{self.agent_id}' starting")
        print(f"🔗 Public URL: {self.public_url}")
        print(f"🌐 Internal bind: {self.internal_host}:{self.port}")
        print(f"📝 Logs: {self.logger.agent_log_dir}")
        print(f"\nPress Ctrl+C to stop\n")

        try:
            run_server(server, host=self.internal_host, port=self.port)
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            print(f"✓ Agent '{self.agent_id}' stopped")