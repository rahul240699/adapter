"""
Conversation logging for NANDA agents.

This module provides simple JSONL (JSON Lines) logging for agent conversations,
allowing easy debugging and analysis of agent interactions.

Each log entry is a single JSON object on its own line, making it easy to
process with standard Unix tools (grep, jq, etc.) or load into analytics tools.

Example:
    >>> from nanda_adapter.core.logger import ConversationLogger
    >>> logger = ConversationLogger("agent_a")
    >>> logger.log("conv_001", "incoming", "Hello from agent_b")
    >>> logger.log("conv_001", "outgoing", "Hello back!")

    # Logs are written to: ./logs/agent_a/conversation_conv_001.jsonl
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class ConversationLogger:
    """
    Simple JSONL conversation logger for agents.

    Logs are organized by agent and conversation ID, with one JSON object
    per line. This format is ideal for streaming, debugging, and analysis.

    Attributes:
        agent_id: Unique identifier for the agent
        log_dir: Base directory for all logs (default: ./logs)
        agent_log_dir: Specific directory for this agent's logs

    Directory structure:
        ./logs/
        └── agent_{agent_id}/
            ├── conversation_{conv_id_1}.jsonl
            ├── conversation_{conv_id_2}.jsonl
            └── ...
    """

    def __init__(self, agent_id: str, log_dir: str = "./logs") -> None:
        """
        Initialize conversation logger.

        Args:
            agent_id: Unique identifier for the agent
            log_dir: Base directory for logs (default: ./logs)

        Raises:
            ValueError: If agent_id is empty
        """
        if not agent_id:
            raise ValueError("agent_id cannot be empty")

        self.agent_id = agent_id
        self.log_dir = Path(log_dir)
        self.agent_log_dir = self.log_dir / f"agent_{agent_id}"

        # Create agent log directory if it doesn't exist
        self.agent_log_dir.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        conversation_id: str,
        source: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a message for a conversation.

        Appends a JSON object (one per line) to the conversation's JSONL file.
        Each entry includes timestamp, agent ID, conversation ID, source,
        message content, and optional metadata.

        Args:
            conversation_id: Unique identifier for the conversation
            source: Origin of the message (e.g., "incoming", "outgoing", "claude")
            message: The message content to log
            metadata: Optional additional data to include in log entry

        Example:
            >>> logger = ConversationLogger("agent_a")
            >>> logger.log("conv_001", "incoming", "Hello", {"depth": 0})
            >>> logger.log("conv_001", "outgoing", "Hi there!", {"depth": 1})
        """
        log_file = self.agent_log_dir / f"conversation_{conversation_id}.jsonl"

        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": self.agent_id,
            "conversation_id": conversation_id,
            "source": source,
            "message": message
        }

        # Include optional metadata
        if metadata:
            entry["metadata"] = metadata

        # Append to JSONL file (one JSON object per line)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def get_conversation_log_path(self, conversation_id: str) -> Path:
        """
        Get the file path for a conversation's log.

        Args:
            conversation_id: Unique identifier for the conversation

        Returns:
            Path to the conversation's JSONL log file

        Example:
            >>> logger = ConversationLogger("agent_a")
            >>> path = logger.get_conversation_log_path("conv_001")
            >>> print(path)
            logs/agent_a/conversation_conv_001.jsonl
        """
        return self.agent_log_dir / f"conversation_{conversation_id}.jsonl"

    def read_conversation(self, conversation_id: str) -> list[Dict[str, Any]]:
        """
        Read all log entries for a conversation.

        Parses the JSONL file and returns a list of log entry dictionaries.
        Returns empty list if log file doesn't exist.

        Args:
            conversation_id: Unique identifier for the conversation

        Returns:
            List of log entry dictionaries, in chronological order

        Example:
            >>> logger = ConversationLogger("agent_a")
            >>> logger.log("conv_001", "incoming", "Hello")
            >>> entries = logger.read_conversation("conv_001")
            >>> len(entries)
            1
            >>> entries[0]["message"]
            'Hello'
        """
        log_file = self.get_conversation_log_path(conversation_id)

        if not log_file.exists():
            return []

        entries = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Skip malformed lines (shouldn't happen, but be defensive)
                        continue

        return entries

    def list_conversations(self) -> list[str]:
        """
        List all conversation IDs that have been logged.

        Returns:
            List of conversation IDs (without file extensions)

        Example:
            >>> logger = ConversationLogger("agent_a")
            >>> logger.log("conv_001", "incoming", "Hello")
            >>> logger.log("conv_002", "incoming", "Hi")
            >>> conversations = logger.list_conversations()
            >>> "conv_001" in conversations
            True
            >>> "conv_002" in conversations
            True
        """
        if not self.agent_log_dir.exists():
            return []

        conversations = []
        for log_file in self.agent_log_dir.glob("conversation_*.jsonl"):
            # Extract conversation ID from filename
            # Format: conversation_{conv_id}.jsonl
            conv_id = log_file.stem.replace("conversation_", "")
            conversations.append(conv_id)

        return sorted(conversations)

    def clear_conversation(self, conversation_id: str) -> bool:
        """
        Delete all log entries for a conversation.

        Args:
            conversation_id: Unique identifier for the conversation

        Returns:
            True if log file was deleted, False if it didn't exist

        Example:
            >>> logger = ConversationLogger("agent_a")
            >>> logger.log("conv_001", "incoming", "Hello")
            >>> logger.clear_conversation("conv_001")
            True
            >>> logger.read_conversation("conv_001")
            []
        """
        log_file = self.get_conversation_log_path(conversation_id)

        if log_file.exists():
            log_file.unlink()
            return True
        return False