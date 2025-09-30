"""
Unit tests for ConversationLogger.

Tests JSONL logging functionality including writing, reading,
and managing conversation logs.
"""

import pytest
import json
from pathlib import Path
from nanda_adapter.core.logger import ConversationLogger


@pytest.fixture
def temp_log_dir(tmp_path):
    """Provide a temporary log directory"""
    return str(tmp_path / "test_logs")


@pytest.fixture
def logger(temp_log_dir):
    """Provide a fresh ConversationLogger instance"""
    return ConversationLogger("agent_test", temp_log_dir)


class TestConversationLoggerInit:
    """Tests for logger initialization."""

    def test_create_logger(self, temp_log_dir):
        """Test creating a logger creates directory structure."""
        logger = ConversationLogger("agent_a", temp_log_dir)
        assert logger.agent_id == "agent_a"
        assert logger.agent_log_dir.exists()
        assert logger.agent_log_dir.name == "agent_agent_a"

    def test_empty_agent_id_raises_error(self, temp_log_dir):
        """Test that empty agent_id raises ValueError."""
        with pytest.raises(ValueError, match="agent_id cannot be empty"):
            ConversationLogger("", temp_log_dir)

    def test_multiple_loggers_same_directory(self, temp_log_dir):
        """Test multiple loggers can share base directory."""
        logger_a = ConversationLogger("agent_a", temp_log_dir)
        logger_b = ConversationLogger("agent_b", temp_log_dir)

        assert logger_a.agent_log_dir != logger_b.agent_log_dir
        assert logger_a.agent_log_dir.exists()
        assert logger_b.agent_log_dir.exists()


class TestLogging:
    """Tests for logging messages."""

    def test_log_simple_message(self, logger):
        """Test logging a simple message."""
        logger.log("conv_001", "incoming", "Hello world")

        log_file = logger.get_conversation_log_path("conv_001")
        assert log_file.exists()

        with open(log_file, 'r') as f:
            entry = json.loads(f.readline())

        assert entry["agent_id"] == "agent_test"
        assert entry["conversation_id"] == "conv_001"
        assert entry["source"] == "incoming"
        assert entry["message"] == "Hello world"
        assert "timestamp" in entry

    def test_log_with_metadata(self, logger):
        """Test logging with additional metadata."""
        logger.log(
            "conv_001",
            "incoming",
            "Hello",
            metadata={"depth": 0, "from_agent": "agent_b"}
        )

        entries = logger.read_conversation("conv_001")
        assert len(entries) == 1
        assert "metadata" in entries[0]
        assert entries[0]["metadata"]["depth"] == 0
        assert entries[0]["metadata"]["from_agent"] == "agent_b"

    def test_log_multiple_messages(self, logger):
        """Test logging multiple messages to same conversation."""
        logger.log("conv_001", "incoming", "Message 1")
        logger.log("conv_001", "outgoing", "Message 2")
        logger.log("conv_001", "incoming", "Message 3")

        entries = logger.read_conversation("conv_001")
        assert len(entries) == 3
        assert entries[0]["message"] == "Message 1"
        assert entries[1]["message"] == "Message 2"
        assert entries[2]["message"] == "Message 3"

    def test_log_multiline_message(self, logger):
        """Test logging message with newlines."""
        multiline = "Line 1\nLine 2\nLine 3"
        logger.log("conv_001", "incoming", multiline)

        entries = logger.read_conversation("conv_001")
        assert entries[0]["message"] == multiline

    def test_log_unicode_message(self, logger):
        """Test logging message with unicode characters."""
        unicode_msg = "Hello 你好 🎉 café"
        logger.log("conv_001", "incoming", unicode_msg)

        entries = logger.read_conversation("conv_001")
        assert entries[0]["message"] == unicode_msg

    def test_log_different_conversations(self, logger):
        """Test logging to different conversations."""
        logger.log("conv_001", "incoming", "Conversation 1")
        logger.log("conv_002", "incoming", "Conversation 2")

        entries_1 = logger.read_conversation("conv_001")
        entries_2 = logger.read_conversation("conv_002")

        assert len(entries_1) == 1
        assert len(entries_2) == 1
        assert entries_1[0]["message"] == "Conversation 1"
        assert entries_2[0]["message"] == "Conversation 2"


class TestReadConversation:
    """Tests for reading conversation logs."""

    def test_read_nonexistent_conversation(self, logger):
        """Test reading conversation that doesn't exist."""
        entries = logger.read_conversation("nonexistent")
        assert entries == []

    def test_read_empty_conversation(self, logger, temp_log_dir):
        """Test reading conversation with empty log file."""
        # Create empty file
        log_file = logger.get_conversation_log_path("conv_001")
        log_file.touch()

        entries = logger.read_conversation("conv_001")
        assert entries == []

    def test_read_preserves_order(self, logger):
        """Test that reading preserves chronological order."""
        for i in range(10):
            logger.log("conv_001", "test", f"Message {i}")

        entries = logger.read_conversation("conv_001")
        assert len(entries) == 10
        for i, entry in enumerate(entries):
            assert entry["message"] == f"Message {i}"


class TestGetConversationLogPath:
    """Tests for getting log file paths."""

    def test_get_log_path(self, logger):
        """Test getting conversation log path."""
        path = logger.get_conversation_log_path("conv_001")
        assert path.name == "conversation_conv_001.jsonl"
        assert "agent_test" in str(path)

    def test_get_log_path_different_conversations(self, logger):
        """Test that different conversations have different paths."""
        path_1 = logger.get_conversation_log_path("conv_001")
        path_2 = logger.get_conversation_log_path("conv_002")
        assert path_1 != path_2


class TestListConversations:
    """Tests for listing conversations."""

    def test_list_no_conversations(self, logger):
        """Test listing when no conversations exist."""
        conversations = logger.list_conversations()
        assert conversations == []

    def test_list_single_conversation(self, logger):
        """Test listing single conversation."""
        logger.log("conv_001", "incoming", "Hello")
        conversations = logger.list_conversations()
        assert conversations == ["conv_001"]

    def test_list_multiple_conversations(self, logger):
        """Test listing multiple conversations."""
        logger.log("conv_001", "incoming", "Hello")
        logger.log("conv_002", "incoming", "Hi")
        logger.log("conv_003", "incoming", "Hey")

        conversations = logger.list_conversations()
        assert len(conversations) == 3
        assert "conv_001" in conversations
        assert "conv_002" in conversations
        assert "conv_003" in conversations

    def test_list_conversations_sorted(self, logger):
        """Test that conversations are returned sorted."""
        logger.log("conv_003", "incoming", "C")
        logger.log("conv_001", "incoming", "A")
        logger.log("conv_002", "incoming", "B")

        conversations = logger.list_conversations()
        assert conversations == ["conv_001", "conv_002", "conv_003"]


class TestClearConversation:
    """Tests for clearing conversation logs."""

    def test_clear_existing_conversation(self, logger):
        """Test clearing a conversation that exists."""
        logger.log("conv_001", "incoming", "Hello")
        assert logger.get_conversation_log_path("conv_001").exists()

        result = logger.clear_conversation("conv_001")
        assert result is True
        assert not logger.get_conversation_log_path("conv_001").exists()

    def test_clear_nonexistent_conversation(self, logger):
        """Test clearing conversation that doesn't exist."""
        result = logger.clear_conversation("nonexistent")
        assert result is False

    def test_clear_removes_from_list(self, logger):
        """Test that cleared conversation is removed from list."""
        logger.log("conv_001", "incoming", "Hello")
        logger.log("conv_002", "incoming", "Hi")

        assert "conv_001" in logger.list_conversations()

        logger.clear_conversation("conv_001")
        conversations = logger.list_conversations()

        assert "conv_001" not in conversations
        assert "conv_002" in conversations


class TestJSONLFormat:
    """Tests for JSONL format compliance."""

    def test_one_json_per_line(self, logger):
        """Test that each log entry is on its own line."""
        logger.log("conv_001", "incoming", "Message 1")
        logger.log("conv_001", "incoming", "Message 2")
        logger.log("conv_001", "incoming", "Message 3")

        log_file = logger.get_conversation_log_path("conv_001")
        with open(log_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 3
        for line in lines:
            # Each line should be valid JSON
            entry = json.loads(line)
            assert "message" in entry

    def test_jsonl_parseable_with_standard_tools(self, logger):
        """Test that JSONL can be parsed line by line."""
        logger.log("conv_001", "incoming", "Message 1")
        logger.log("conv_001", "outgoing", "Message 2")

        log_file = logger.get_conversation_log_path("conv_001")

        # Simulate reading with standard tools (line by line)
        messages = []
        with open(log_file, 'r') as f:
            for line in f:
                entry = json.loads(line)
                messages.append(entry["message"])

        assert messages == ["Message 1", "Message 2"]