"""
Communication utilities for NANDA Agent Bridge.
Handles terminal and UI client communication.
"""
import os
import threading
import requests
from datetime import datetime
from typing import Optional
from python_a2a import A2AClient, Message, TextContent, MessageRole, Metadata


# Configuration
UI_MODE = os.getenv("UI_MODE", "true").lower() in ("true", "1", "yes", "y")
TERMINAL_PORT = int(os.getenv("TERMINAL_PORT", "6010"))
LOCAL_TERMINAL_URL = f"http://localhost:{TERMINAL_PORT}/a2a"


# Add the threaded method to the A2AClient class if it doesn't exist
if not hasattr(A2AClient, 'send_message_threaded'):
    def send_message_threaded(self, message: Message):
        """Send a message in a separate thread without waiting for a response"""
        thread = threading.Thread(target=self.send_message, args=(message,))
        thread.daemon = True
        thread.start()
        return thread
    
    # Add the method to the class
    A2AClient.send_message_threaded = send_message_threaded


def send_to_terminal(text: str, terminal_url: str, conversation_id: str, metadata: dict = None) -> bool:
    """Send a message to a terminal"""
    try:
        print(f"Sending message to {terminal_url}: {text[:50]}...")
        terminal = A2AClient(terminal_url, timeout=30)
        terminal.send_message_threaded(
            Message(
                role=MessageRole.USER,
                content=TextContent(text=text),
                conversation_id=conversation_id,
                metadata=Metadata(custom_fields=metadata or {})
            )
        )
        return True
    except Exception as e:
        print(f"Error sending to terminal {terminal_url}: {e}")
        return False


def send_to_ui_client(message_text: str, from_agent: str, conversation_id: str) -> bool:
    """Send a message to UI client via HTTP POST"""
    # Read UI_CLIENT_URL dynamically to get the latest value
    ui_client_url = os.getenv("UI_CLIENT_URL", "")
    print(f"🔍 Dynamic UI_CLIENT_URL: '{ui_client_url}'")
    
    if not ui_client_url:
        print(f"No UI client URL configured. Cannot send message to UI client")
        return False

    try:
        print(f"Sending message to UI client: {message_text[:50]}...")
        response = requests.post(
            ui_client_url,
            json={
                "message": message_text,
                "from_agent": from_agent,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            },
            timeout=10,
            verify=False  # disable SSL verification for development
        )
        
        if response.status_code == 200:
            print(f"Successfully sent message to UI client")
            return True
        else:
            print(f"Failed to send message to UI client: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"Error sending to UI client: {e}")
        return False


def get_local_terminal_url() -> str:
    """Get the local terminal URL"""
    return LOCAL_TERMINAL_URL


def is_ui_mode() -> bool:
    """Check if UI mode is enabled"""
    return UI_MODE