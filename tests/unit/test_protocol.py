"""
Unit tests for A2A Protocol module.

Tests message formatting, parsing, validation, and round-trip operations
for the Agent-to-Agent communication protocol.
"""

import pytest
from nanda_adapter.core.protocol import (
    A2AMessage,
    format_a2a_message,
    parse_a2a_message,
    is_a2a_message
)


class TestA2AMessage:
    """Tests for A2AMessage dataclass validation."""

    def test_create_valid_message(self):
        """Test creating a valid A2A message."""
        msg = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Hello",
            conversation_id="conv_001"
        )
        assert msg.from_agent == "agent_a"
        assert msg.to_agent == "agent_b"
        assert msg.message == "Hello"
        assert msg.conversation_id == "conv_001"
        assert msg.depth == 0  # Default
        assert msg.max_depth == 1  # Default
        assert msg.message_type == "query"  # Default

    def test_create_with_custom_depth(self):
        """Test creating message with custom depth values."""
        msg = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Response",
            conversation_id="conv_001",
            depth=1,
            max_depth=2,
            message_type="response"
        )
        assert msg.depth == 1
        assert msg.max_depth == 2
        assert msg.message_type == "response"

    def test_empty_from_agent_raises_error(self):
        """Test that empty from_agent raises ValueError."""
        with pytest.raises(ValueError, match="from_agent cannot be empty"):
            A2AMessage(
                from_agent="",
                to_agent="agent_b",
                message="Hello",
                conversation_id="conv_001"
            )

    def test_empty_to_agent_raises_error(self):
        """Test that empty to_agent raises ValueError."""
        with pytest.raises(ValueError, match="to_agent cannot be empty"):
            A2AMessage(
                from_agent="agent_a",
                to_agent="",
                message="Hello",
                conversation_id="conv_001"
            )

    def test_empty_message_raises_error(self):
        """Test that empty message raises ValueError."""
        with pytest.raises(ValueError, match="message cannot be empty"):
            A2AMessage(
                from_agent="agent_a",
                to_agent="agent_b",
                message="",
                conversation_id="conv_001"
            )

    def test_empty_conversation_id_allowed(self):
        """Test that empty conversation_id is allowed (set by caller later)."""
        msg = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Hello",
            conversation_id=""
        )
        assert msg.conversation_id == ""

    def test_negative_depth_raises_error(self):
        """Test that negative depth raises ValueError."""
        with pytest.raises(ValueError, match="depth must be non-negative"):
            A2AMessage(
                from_agent="agent_a",
                to_agent="agent_b",
                message="Hello",
                conversation_id="conv_001",
                depth=-1
            )

    def test_negative_max_depth_raises_error(self):
        """Test that negative max_depth raises ValueError."""
        with pytest.raises(ValueError, match="max_depth must be non-negative"):
            A2AMessage(
                from_agent="agent_a",
                to_agent="agent_b",
                message="Hello",
                conversation_id="conv_001",
                max_depth=-1
            )

    def test_invalid_message_type_raises_error(self):
        """Test that invalid message_type raises ValueError."""
        with pytest.raises(ValueError, match="message_type must be"):
            A2AMessage(
                from_agent="agent_a",
                to_agent="agent_b",
                message="Hello",
                conversation_id="conv_001",
                message_type="invalid"
            )


class TestFormatA2AMessage:
    """Tests for format_a2a_message function."""

    def test_format_basic_message(self):
        """Test formatting a basic message."""
        msg = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Hello",
            conversation_id="conv_001"
        )
        formatted = format_a2a_message(msg)

        assert "__EXTERNAL_MESSAGE__" in formatted
        assert "__FROM_AGENT__agent_a" in formatted
        assert "__TO_AGENT__agent_b" in formatted
        assert "__MESSAGE_TYPE__query" in formatted
        assert "__DEPTH__0" in formatted
        assert "__MAX_DEPTH__1" in formatted
        assert "__MESSAGE_START__" in formatted
        assert "Hello" in formatted
        assert "__MESSAGE_END__" in formatted

    def test_format_with_custom_depth(self):
        """Test formatting message with custom depth values."""
        msg = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Response",
            conversation_id="conv_001",
            depth=2,
            max_depth=5,
            message_type="response"
        )
        formatted = format_a2a_message(msg)

        assert "__DEPTH__2" in formatted
        assert "__MAX_DEPTH__5" in formatted
        assert "__MESSAGE_TYPE__response" in formatted

    def test_format_multiline_message(self):
        """Test formatting message with multiple lines."""
        msg = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Line 1\nLine 2\nLine 3",
            conversation_id="conv_001"
        )
        formatted = format_a2a_message(msg)

        assert "Line 1" in formatted
        assert "Line 2" in formatted
        assert "Line 3" in formatted


class TestParseA2AMessage:
    """Tests for parse_a2a_message function."""

    def test_parse_formatted_message(self):
        """Test parsing a properly formatted message."""
        original = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Hello",
            conversation_id="conv_001"
        )
        formatted = format_a2a_message(original)
        parsed = parse_a2a_message(formatted)

        assert parsed is not None
        assert parsed.from_agent == "agent_a"
        assert parsed.to_agent == "agent_b"
        assert parsed.message == "Hello"
        assert parsed.depth == 0
        assert parsed.max_depth == 1
        assert parsed.message_type == "query"

    def test_parse_with_custom_depth(self):
        """Test parsing message with custom depth values."""
        original = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Response",
            conversation_id="conv_001",
            depth=3,
            max_depth=10,
            message_type="response"
        )
        formatted = format_a2a_message(original)
        parsed = parse_a2a_message(formatted)

        assert parsed.depth == 3
        assert parsed.max_depth == 10
        assert parsed.message_type == "response"

    def test_parse_multiline_message(self):
        """Test parsing message with multiple lines."""
        original = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Line 1\nLine 2\nLine 3",
            conversation_id="conv_001"
        )
        formatted = format_a2a_message(original)
        parsed = parse_a2a_message(formatted)

        assert parsed.message == "Line 1\nLine 2\nLine 3"

    def test_parse_non_a2a_message_returns_none(self):
        """Test that non-A2A messages return None."""
        result = parse_a2a_message("Hello world")
        assert result is None

    def test_parse_empty_string_returns_none(self):
        """Test that empty string returns None."""
        result = parse_a2a_message("")
        assert result is None

    def test_parse_missing_from_agent_returns_none(self):
        """Test that message missing from_agent returns None."""
        incomplete = """__EXTERNAL_MESSAGE__
__TO_AGENT__agent_b
__MESSAGE_START__
Hello
__MESSAGE_END__"""
        result = parse_a2a_message(incomplete)
        assert result is None

    def test_parse_missing_to_agent_returns_none(self):
        """Test that message missing to_agent returns None."""
        incomplete = """__EXTERNAL_MESSAGE__
__FROM_AGENT__agent_a
__MESSAGE_START__
Hello
__MESSAGE_END__"""
        result = parse_a2a_message(incomplete)
        assert result is None

    def test_parse_missing_message_content_returns_none(self):
        """Test that message without content returns None."""
        incomplete = """__EXTERNAL_MESSAGE__
__FROM_AGENT__agent_a
__TO_AGENT__agent_b
__MESSAGE_START__
__MESSAGE_END__"""
        result = parse_a2a_message(incomplete)
        assert result is None

    def test_parse_invalid_depth_uses_default(self):
        """Test that invalid depth value falls back to default."""
        malformed = """__EXTERNAL_MESSAGE__
__FROM_AGENT__agent_a
__TO_AGENT__agent_b
__DEPTH__invalid
__MESSAGE_START__
Hello
__MESSAGE_END__"""
        parsed = parse_a2a_message(malformed)
        assert parsed is not None
        assert parsed.depth == 0  # Default

    def test_parse_invalid_max_depth_uses_default(self):
        """Test that invalid max_depth value falls back to default."""
        malformed = """__EXTERNAL_MESSAGE__
__FROM_AGENT__agent_a
__TO_AGENT__agent_b
__MAX_DEPTH__invalid
__MESSAGE_START__
Hello
__MESSAGE_END__"""
        parsed = parse_a2a_message(malformed)
        assert parsed is not None
        assert parsed.max_depth == 1  # Default


class TestIsA2AMessage:
    """Tests for is_a2a_message function."""

    def test_valid_a2a_message(self):
        """Test that valid A2A message is detected."""
        msg = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Hello",
            conversation_id="conv_001"
        )
        formatted = format_a2a_message(msg)
        assert is_a2a_message(formatted) is True

    def test_non_a2a_message(self):
        """Test that non-A2A message is rejected."""
        assert is_a2a_message("Hello world") is False

    def test_empty_string(self):
        """Test that empty string is rejected."""
        assert is_a2a_message("") is False

    def test_whitespace_only(self):
        """Test that whitespace-only string is rejected."""
        assert is_a2a_message("   \n  \t  ") is False

    def test_marker_with_leading_whitespace(self):
        """Test that marker with leading whitespace is detected."""
        assert is_a2a_message("  \n  __EXTERNAL_MESSAGE__\n...") is True


class TestRoundTrip:
    """Tests for format → parse round-trip operations."""

    def test_round_trip_basic(self):
        """Test that format → parse preserves all fields."""
        original = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Test message",
            conversation_id="conv_001",
            depth=2,
            max_depth=5,
            message_type="response"
        )

        formatted = format_a2a_message(original)
        parsed = parse_a2a_message(formatted)

        assert parsed.from_agent == original.from_agent
        assert parsed.to_agent == original.to_agent
        assert parsed.message == original.message
        assert parsed.depth == original.depth
        assert parsed.max_depth == original.max_depth
        assert parsed.message_type == original.message_type

    def test_round_trip_with_special_characters(self):
        """Test round-trip with special characters in message."""
        original = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Special chars: @#$%^&*() \"quotes\" 'apostrophes'",
            conversation_id="conv_001"
        )

        formatted = format_a2a_message(original)
        parsed = parse_a2a_message(formatted)

        assert parsed.message == original.message

    def test_round_trip_with_unicode(self):
        """Test round-trip with unicode characters."""
        original = A2AMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            message="Unicode: 你好 🎉 café",
            conversation_id="conv_001"
        )

        formatted = format_a2a_message(original)
        parsed = parse_a2a_message(formatted)

        assert parsed.message == original.message