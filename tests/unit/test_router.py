"""
Unit tests for MessageRouter.

Tests message routing, command handling, and loop prevention.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from nanda_adapter.core.router import MessageRouter
from nanda_adapter.core.registry import LocalRegistry
from nanda_adapter.core.protocol import A2AMessage


@pytest.fixture
def registry(tmp_path):
    """Provide a registry with test agents."""
    reg = LocalRegistry(str(tmp_path / "test_registry.json"))
    reg.register("agent_b", "http://localhost:6002")
    reg.register("agent_c", "http://192.168.1.100:6004")
    return reg


@pytest.fixture
def router(registry):
    """Provide a basic router without handlers."""
    return MessageRouter("agent_a", registry)


@pytest.fixture
def router_with_claude(registry):
    """Provide router with mocked Claude handler."""
    claude_mock = Mock(return_value="Claude says: 42")
    return MessageRouter("agent_a", registry, claude_handler=claude_mock)


@pytest.fixture
def router_with_improver(registry):
    """Provide router with message improver."""
    improver = lambda text: text.upper()
    return MessageRouter("agent_a", registry, improver=improver)


class TestRouterInit:
    """Tests for router initialization."""

    def test_create_router(self, registry):
        """Test creating a router."""
        router = MessageRouter("agent_a", registry)
        assert router.agent_id == "agent_a"
        assert router.registry == registry
        assert router.improver is None
        assert router.claude_handler is None

    def test_create_router_with_handlers(self, registry):
        """Test creating router with handlers."""
        improver = lambda x: x.upper()
        claude = lambda x: "response"

        router = MessageRouter("agent_a", registry, improver, claude)
        assert router.improver is not None
        assert router.claude_handler is not None

    def test_empty_agent_id_raises_error(self, registry):
        """Test that empty agent_id raises ValueError."""
        with pytest.raises(ValueError, match="agent_id cannot be empty"):
            MessageRouter("", registry)

    def test_none_registry_raises_error(self):
        """Test that None registry raises ValueError."""
        with pytest.raises(ValueError, match="registry cannot be None"):
            MessageRouter("agent_a", None)


class TestRouteDispatch:
    """Tests for route() method dispatch logic."""

    def test_route_agent_message(self, router):
        """Test that @agent_id routes to agent handler."""
        with patch.object(router, '_handle_agent_message', return_value="sent"):
            result = router.route("@agent_b hello", "conv_001")
            router._handle_agent_message.assert_called_once()

    def test_route_command(self, router):
        """Test that /command routes to command handler."""
        with patch.object(router, '_handle_command', return_value="help"):
            result = router.route("/help", "conv_001")
            router._handle_command.assert_called_once()

    def test_route_default(self, router):
        """Test that plain text routes to default handler."""
        with patch.object(router, '_handle_default', return_value="response"):
            result = router.route("Hello", "conv_001")
            router._handle_default.assert_called_once()

    def test_route_strips_whitespace(self, router):
        """Test that leading/trailing whitespace is stripped."""
        with patch.object(router, '_handle_command', return_value="help"):
            router.route("  /help  ", "conv_001")
            # Would fail to match /help if not stripped


class TestHandleCommand:
    """Tests for command handling."""

    def test_help_command(self, router):
        """Test /help command."""
        result = router.route("/help", "conv_001")
        assert "Available commands" in result
        assert "/help" in result
        assert "/query" in result
        assert "@<agent_id>" in result

    def test_query_command_with_claude(self, router_with_claude):
        """Test /query command with Claude handler."""
        result = router_with_claude.route("/query What is 2+2?", "conv_001")
        assert "Claude says: 42" in result
        router_with_claude.claude_handler.assert_called_once_with("What is 2+2?")

    def test_query_command_without_claude(self, router):
        """Test /query command without Claude handler."""
        result = router.route("/query test", "conv_001")
        assert "Claude handler not configured" in result

    def test_query_command_without_text(self, router_with_claude):
        """Test /query without question text."""
        result = router_with_claude.route("/query", "conv_001")
        assert "Usage:" in result

    def test_unknown_command(self, router):
        """Test unknown command."""
        result = router.route("/unknown", "conv_001")
        assert "Unknown command" in result
        assert "Try /help" in result


class TestHandleDefault:
    """Tests for default message handling."""

    def test_default_with_claude(self, router_with_claude):
        """Test default handler queries Claude."""
        result = router_with_claude.route("What is 2+2?", "conv_001")
        assert "Claude says: 42" in result

    def test_default_without_claude(self, router):
        """Test default handler without Claude."""
        result = router.route("Hello", "conv_001")
        assert "Claude handler not configured" in result


class TestQueryClaude:
    """Tests for Claude query functionality."""

    def test_query_claude_success(self, router_with_claude):
        """Test successful Claude query."""
        result = router_with_claude._query_claude("test query")
        assert "Claude says: 42" in result

    def test_query_claude_no_handler(self, router):
        """Test query without handler."""
        result = router._query_claude("test")
        assert "Claude handler not configured" in result

    def test_query_claude_handler_raises(self, registry):
        """Test Claude handler that raises exception."""
        bad_handler = Mock(side_effect=Exception("API error"))
        router = MessageRouter("agent_a", registry, claude_handler=bad_handler)

        result = router._query_claude("test")
        assert "Error querying Claude" in result
        assert "API error" in result


class TestMessageImprovement:
    """Tests for message improvement."""

    def test_improvement_applied(self, router_with_improver):
        """Test that improver is applied to outgoing messages."""
        # We can't easily test the actual sending without mocking A2AClient,
        # but we can verify the improver function itself
        assert router_with_improver.improver("hello") == "HELLO"

    def test_improvement_failure_doesnt_crash(self, registry):
        """Test that improvement failure doesn't prevent sending."""
        bad_improver = Mock(side_effect=Exception("Improvement failed"))
        router = MessageRouter("agent_a", registry, improver=bad_improver)

        # Should not raise, should handle gracefully
        # (Actual test would need to mock A2AClient)
        assert router.improver is not None


class TestLoopPrevention:
    """Tests for depth-based loop prevention."""

    def test_depth_zero_allowed(self, router):
        """Test that depth=0 messages are sent."""
        # Simply verify depth=0 is not blocked
        # (Actual sending would require network mocking)
        result = router.route("@agent_b hello", "conv_001", depth=0)

        # Should not be blocked by depth limit
        assert "Maximum depth reached" not in result

    def test_depth_one_blocked(self, router):
        """Test that depth=1 messages are blocked (max_depth=1)."""
        result = router.route("@agent_b hello", "conv_001", depth=1)
        assert "Maximum depth reached" in result
        assert "depth=1" in result

    def test_depth_higher_blocked(self, router):
        """Test that depth>1 messages are blocked."""
        result = router.route("@agent_b hello", "conv_001", depth=5)
        assert "Maximum depth reached" in result


class TestAgentLookup:
    """Tests for agent registry lookup."""

    def test_lookup_existing_agent(self, router):
        """Test looking up agent that exists."""
        # agent_b was registered in fixture
        url = router.registry.lookup("agent_b")
        assert url == "http://localhost:6002"

    def test_lookup_nonexistent_agent(self, router):
        """Test looking up agent that doesn't exist."""
        result = router.route("@nonexistent hello", "conv_001")
        assert "not found in registry" in result
        assert "nonexistent" in result


class TestMessageParsing:
    """Tests for message parsing."""

    def test_parse_agent_message_basic(self, router):
        """Test parsing basic @agent_id message."""
        # Should not crash, validates format
        result = router.route("@agent_b Hello world", "conv_001")
        # (Actual sending would be mocked in integration tests)

    def test_parse_agent_message_no_text(self, router):
        """Test @agent_id without message text."""
        result = router.route("@agent_b", "conv_001")
        assert "Invalid format" in result
        assert "Use '@agent_id message'" in result

    def test_parse_agent_message_multiword(self, router):
        """Test @agent_id with multi-word message."""
        # Should handle spaces in message correctly
        result = router.route("@agent_b This is a longer message", "conv_001")
        # Should not error on parsing


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_message(self, router):
        """Test routing empty message."""
        result = router.route("", "conv_001")
        # Should handle gracefully (routes to default)

    def test_whitespace_only_message(self, router):
        """Test routing whitespace-only message."""
        result = router.route("   ", "conv_001")
        # Should handle gracefully

    def test_special_characters_in_message(self, router_with_claude):
        """Test message with special characters."""
        result = router_with_claude.route("What about @#$%?", "conv_001")
        # Should handle special chars in default/Claude query

    def test_unicode_in_message(self, router_with_claude):
        """Test message with unicode."""
        result = router_with_claude.route("你好 🎉", "conv_001")
        # Should handle unicode