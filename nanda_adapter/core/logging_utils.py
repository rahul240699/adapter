"""
Logging utilities for NANDA Agent Bridge.
Handles conversation logging and message tracking.
"""
import os
import json
from datetime import datetime


# Set up logging directory
LOG_DIR = os.getenv("LOG_DIR", "conversation_logs")
os.makedirs(LOG_DIR, exist_ok=True)


def log_message(conversation_id: str, path: str, source: str, message_text: str) -> None:
    """Log each message to a JSON file"""
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "conversation_id": conversation_id,
        "path": path,
        "source": source,
        "message": message_text
    }
    
    # Create a log file for this conversation if it doesn't exist
    log_filename = os.path.join(LOG_DIR, f"conversation_{conversation_id}.jsonl")
    
    # Append the log entry to local file
    with open(log_filename, "a") as log_file:
        log_file.write(json.dumps(log_entry) + "\n")
    
    print(f"Logged message from {source} in conversation {conversation_id}")


def get_log_directory() -> str:
    """Get the current logging directory"""
    return os.path.abspath(LOG_DIR)