"""
A2A Protocol Message Format with Loop Prevention.

This module implements the Agent-to-Agent (A2A) message protocol format
used for communication between NANDA agents. It includes depth tracking
to prevent infinite message loops.

The protocol uses a structured text format with marker tokens to encode
message metadata (sender, receiver, depth, etc.) alongside the message content.

Example:
    >>> from nanda_adapter.core.protocol import A2AMessage, format_a2a_message
    >>> msg = A2AMessage(
    ...     from_agent="agent_a",
    ...     to_agent="agent_b",
    ...     message="Hello!",
    ...     conversation_id="conv_001"
    ... )
    >>> formatted = format_a2a_message(msg)
    >>> print(formatted)
    __EXTERNAL_MESSAGE__
    __FROM_AGENT__agent_a
    __TO_AGENT__agent_b
    ...
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class A2AMessage:
    """
    Agent-to-Agent message structure.

    Attributes:
        from_agent: ID of the sending agent
        to_agent: ID of the receiving agent
        message: The actual message content
        conversation_id: Unique identifier for the conversation thread
        depth: Current message depth (0 = initial request, 1 = response, etc.)
        max_depth: Maximum allowed depth to prevent infinite loops
        message_type: Type of message - "query" (request) or "response" (reply)
        receipt_id: Optional payment receipt ID for paid requests

    The depth tracking mechanism prevents infinite loops:
        - Initial messages have depth=0
        - Responses increment depth by 1
        - When depth >= max_depth, no further responses are sent
        - Default max_depth=1 allows only request-response pattern
    """

    from_agent: str
    to_agent: str
    message: str
    conversation_id: str
    depth: int = 0
    max_depth: int = 1
    message_type: str = "query"  # "query" or "response"
    receipt_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate message fields after initialization."""
        if not self.from_agent:
            raise ValueError("from_agent cannot be empty")
        if not self.to_agent:
            raise ValueError("to_agent cannot be empty")
        if not self.message:
            raise ValueError("message cannot be empty")
        # Note: conversation_id can be empty during parsing (set by caller later)
        if self.depth < 0:
            raise ValueError(f"depth must be non-negative, got {self.depth}")
        if self.max_depth < 0:
            raise ValueError(f"max_depth must be non-negative, got {self.max_depth}")
        if self.message_type not in ("query", "response"):
            raise ValueError(f"message_type must be 'query' or 'response', got {self.message_type}")


def format_a2a_message(msg: A2AMessage) -> str:
    """
    Format an A2A message for transmission.

    Converts an A2AMessage object into the structured text format used
    for agent-to-agent communication. The format uses marker tokens to
    delimit metadata fields.

    Args:
        msg: The A2AMessage object to format

    Returns:
        Formatted string representation of the message

    Example:
        >>> msg = A2AMessage(
        ...     from_agent="agent_a",
        ...     to_agent="agent_b",
        ...     message="What is 2+2?",
        ...     conversation_id="math_001"
        ... )
        >>> formatted = format_a2a_message(msg)
        >>> "__EXTERNAL_MESSAGE__" in formatted
        True
    """
    receipt_field = f"__RECEIPT_ID__{msg.receipt_id}\n" if msg.receipt_id else ""
    return f"""__EXTERNAL_MESSAGE__
__FROM_AGENT__{msg.from_agent}
__TO_AGENT__{msg.to_agent}
__MESSAGE_TYPE__{msg.message_type}
__DEPTH__{msg.depth}
__MAX_DEPTH__{msg.max_depth}
{receipt_field}__MESSAGE_START__
{msg.message}
__MESSAGE_END__"""


def parse_a2a_message(raw: str) -> Optional[A2AMessage]:
    """
    Parse a raw A2A message string.

    Extracts message metadata and content from the structured text format.
    Returns None if the message is not in valid A2A format.

    Args:
        raw: Raw message string to parse

    Returns:
        A2AMessage object if valid, None otherwise

    Example:
        >>> formatted = format_a2a_message(A2AMessage(
        ...     from_agent="agent_a",
        ...     to_agent="agent_b",
        ...     message="Hello",
        ...     conversation_id="conv_001"
        ... ))
        >>> parsed = parse_a2a_message(formatted)
        >>> parsed.from_agent
        'agent_a'
        >>> parsed.message
        'Hello'

    Note:
        This function is tolerant of missing optional fields and will use
        sensible defaults (depth=0, max_depth=1, message_type="query").
    """
    if not raw or not raw.strip().startswith("__EXTERNAL_MESSAGE__"):
        return None

    lines = raw.split('\n')
    from_agent = None
    to_agent = None
    message_type = "query"  # Default
    depth = 0  # Default
    max_depth = 1  # Default
    receipt_id = None  # Default
    message_lines = []
    in_message = False

    for line in lines[1:]:  # Skip first line (__EXTERNAL_MESSAGE__)
        if line.startswith("__FROM_AGENT__"):
            from_agent = line[len("__FROM_AGENT__"):]
        elif line.startswith("__TO_AGENT__"):
            to_agent = line[len("__TO_AGENT__"):]
        elif line.startswith("__MESSAGE_TYPE__"):
            message_type = line[len("__MESSAGE_TYPE__"):]
        elif line.startswith("__DEPTH__"):
            try:
                depth = int(line[len("__DEPTH__"):])
            except ValueError:
                depth = 0  # Fallback to default
        elif line.startswith("__MAX_DEPTH__"):
            try:
                max_depth = int(line[len("__MAX_DEPTH__"):])
            except ValueError:
                max_depth = 1  # Fallback to default
        elif line.startswith("__RECEIPT_ID__"):
            receipt_id = line[len("__RECEIPT_ID__"):]
        elif line == "__MESSAGE_START__":
            in_message = True
        elif line == "__MESSAGE_END__":
            break
        elif in_message:
            message_lines.append(line)

    # Validate required fields
    if not from_agent or not to_agent:
        return None

    message_content = '\n'.join(message_lines)
    if not message_content:
        return None

    try:
        return A2AMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message=message_content,
            conversation_id="",  # Will be set by caller from context
            depth=depth,
            max_depth=max_depth,
            message_type=message_type,
            receipt_id=receipt_id
        )
    except ValueError:
        # Invalid field values, return None
        return None


def is_a2a_message(raw: str) -> bool:
    """
    Check if a string is in A2A message format.

    This is a lightweight check that only looks for the opening marker.
    Use parse_a2a_message() for full validation and parsing.

    Args:
        raw: String to check

    Returns:
        True if string starts with A2A message marker, False otherwise

    Example:
        >>> is_a2a_message("__EXTERNAL_MESSAGE__\\n...")
        True
        >>> is_a2a_message("Hello world")
        False
    """
    return bool(raw and raw.strip().startswith("__EXTERNAL_MESSAGE__"))