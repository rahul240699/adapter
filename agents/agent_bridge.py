# agent_bridge.py
import os
import uuid
import traceback
import json
import threading
import requests
from typing import Optional
from datetime import datetime
from anthropic import Anthropic, APIStatusError
from python_a2a import (
    A2AServer, A2AClient, run_server,
    Message, TextContent, MessageRole, ErrorContent
)
# MongoDB
from pymongo import MongoClient
import asyncio
from mcp_utils import MCPClient
import base64

import sys
sys.stdout.reconfigure(line_buffering=True)

# Set API key through environment variable or directly in the code
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or "your key"

# Toggle for message improvement feature
IMPROVE_MESSAGES = os.getenv("IMPROVE_MESSAGES", "true").lower() in ("true", "1", "yes", "y")

# Create Anthropic client with explicit API key
anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

# Get agent configuration from environment variables
AGENT_ID = os.getenv("AGENT_ID", "default")  # Default to 'default' if not specified
PORT = int(os.getenv("PORT", "6000"))
TERMINAL_PORT = int(os.getenv("TERMINAL_PORT", "6010"))

# Local terminal URL
LOCAL_TERMINAL_URL = f"http://localhost:{TERMINAL_PORT}/a2a"

# UI client support
UI_MODE = os.getenv("UI_MODE", "false").lower() in ("true", "1", "yes", "y")
UI_CLIENT_URL = os.getenv("UI_CLIENT_URL", "")
registered_ui_clients = set()

# Set up logging directory
LOG_DIR = os.getenv("LOG_DIR", "conversation_logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Configure system prompts based on agent ID (examples from the original code)
SYSTEM_PROMPTS = {
    "default": "You are Claude assisting a user (Agent). Assume the messages you get are part of a conversation with other agents. Help the user communicate effectively with other agents."
}

# Configure message improvement prompts
IMPROVE_MESSAGE_PROMPTS = {    
    "default": "Improve the following message to make it more clear, compelling, and professional without changing the core content or adding fictional information. Keep the same overall meaning but enhance the phrasing and structure. Don't make it too verbose - keep it concise but impactful. Return only the improved message without explanations or introductions."
}

# --- MongoDB configuration (shared with registry) ---
MONGO_URI = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or "mongodb+srv://mihirsheth2911:wx1mxUn2788jLdnl@cluster0.fvevtjx.mongodb.net/?retryWrites=true&w=majority"

# Allow custom DB name via env
MONGO_DBNAME = os.getenv("MONGODB_DB", "iot_agents_db")
MCP_REGISTRY = "mcp_registry"

SMITHERY_API_KEY = os.getenv("SMITHERY_API_KEY") or "bfcb8cec-9d56-4957-8156-bced0bfca532"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.admin.command("ping")
    mongo_db = mongo_client[MONGO_DBNAME]
    mcp_registry_col = mongo_db[MCP_REGISTRY]
    messages_col = mongo_db["messages"]
    USE_MONGO = True
    print("[agent_bridge] Connected to MongoDB, message logs will be persisted.")
except Exception as e:
    print(f"[agent_bridge] WARNING: Could not connect to MongoDB ({e}). Falling back to file-only logging.")
    USE_MONGO = False

def get_registry_url():
    """Get the registry URL from file or use default"""
    try:
        if os.path.exists("registry_url.txt"):
            with open("registry_url.txt", "r") as f:
                registry_url = f.read().strip()
                print(f"Using registry URL from file: {registry_url}")
                return registry_url
    except Exception as e:
        print(f"Error reading registry URL from file: {e}")
    
    # Default if file doesn't exist
    default_url = "http://localhost:6900"
    print(f"Using default registry URL: {default_url}")
    return default_url

def register_with_registry(agent_id, agent_url, api_url):
    """Register this agent with the registry"""
    registry_url = get_registry_url()
    try:
        # Add /a2a to the URL during registration
        if not agent_url.endswith('/a2a'):
            agent_url = f"{agent_url}"

        data = {
            "agent_id": agent_id,
            "agent_url": agent_url,
            "api_url": api_url
        }
        print(f"Registering agent {agent_id} with URL {agent_url} at registry {registry_url}...")
        response = requests.post(f"{registry_url}/register", json=data)
        if response.status_code == 200:
            print(f"Agent {agent_id} registered successfully")
            return True
        else:
            print(f"Failed to register agent: {response.text}")
            return False
    except Exception as e:
        print(f"Error registering agent: {e}")
        return False

def lookup_agent(agent_id):
    """Look up an agent's URL in the registry"""
    registry_url = get_registry_url()
    try:
        print(f"Looking up agent {agent_id} in registry {registry_url}...")
        response = requests.get(f"{registry_url}/lookup/{agent_id}")
        if response.status_code == 200:
            agent_url = response.json().get("agent_url")
            print(f"Found agent {agent_id} at URL: {agent_url}")
            return agent_url
        print(f"Agent {agent_id} not found in registry")
        return None
    except Exception as e:
        print(f"Error looking up agent {agent_id}: {e}")
        return None

def list_registered_agents():
    """Get a list of all registered agents from the registry"""
    registry_url = get_registry_url()
    try:
        print(f"Requesting list of agents from registry {registry_url}...")
        response = requests.get(f"{registry_url}/list")
        if response.status_code == 200:
            agents = response.json()
            return agents
        print(f"Failed to get list of agents from registry")
        return None
    except Exception as e:
        print(f"Error getting list of agents: {e}")
        return None

def log_message(conversation_id, path, source, message_text):
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
    
    # Append the log entry to local file (legacy behaviour)
    with open(log_filename, "a") as log_file:
        log_file.write(json.dumps(log_entry) + "\n")

    # Also insert into MongoDB if available
    if USE_MONGO:
        try:
            messages_col.insert_one(log_entry)
        except Exception as e:
            print(f"[agent_bridge] Error writing log to MongoDB: {e}")
    
    print(f"Logged message from {source} in conversation {conversation_id}")

def call_claude(prompt: str, additional_context: str, conversation_id: str, current_path: str, system_prompt: str = None) -> Optional[str]:
    """Wrapper that never raises: returns text or None on failure."""
    try:
        # Use the specified system prompt or default to the agent's system prompt
        if system_prompt:
            system = system_prompt
        else:
            # Use the agent's specific prompt if available, otherwise use default
            system = SYSTEM_PROMPTS["default"]
        
        # Combine the prompt with additional context if provided
        full_prompt = prompt
        if additional_context and additional_context.strip():
            full_prompt = f"ADDITIONAL CONTEXT FRseOM USER: {additional_context}\n\nMESSAGE: {prompt}"
        
        print(f"Agent {AGENT_ID}: Calling Claude with prompt: {full_prompt[:50]}...")
        resp = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=512,
            messages=[{"role":"user","content":full_prompt}],
            system=system
        )
        response_text = resp.content[0].text
        
        # Log the Claude response
        log_message(conversation_id, current_path, f"Claude {AGENT_ID}", response_text)
        
        return response_text
    except APIStatusError as e:
        print(f"Agent {AGENT_ID}: Anthropic API error:", e.status_code, e.message, flush=True)
        # If we hit a credit limit error, return a fallback message
        if "credit balance is too low" in str(e):
            return f"Agent {AGENT_ID} processed (API credit limit reached): {prompt}"
    except Exception as e:
        print(f"Agent {AGENT_ID}: Anthropic SDK error:", e, flush=True)
        traceback.print_exc()
    return None

def improve_message(message_text: str, conversation_id: str, current_path: str, additional_prompt: str=None) -> str:
    """Improve a message using Claude before forwarding it to the other party."""
    if not IMPROVE_MESSAGES:
        return message_text
    
    try:
        if additional_prompt:
            system_prompt = additional_prompt + IMPROVE_MESSAGE_PROMPTS["default"]
        else:
            # Use the appropriate improvement prompt based on agent ID
            system_prompt = IMPROVE_MESSAGE_PROMPTS["default"]
        
        # Call Claude to improve the message
        improved_message = call_claude(message_text, "", conversation_id, current_path, system_prompt)
        
        # If Claude successfully improved the message, use that; otherwise, use the original
        return improved_message if improved_message else message_text
    except Exception as e:
        print(f"Error improving message: {e}")
        return message_text

def send_to_terminal(text, terminal_url, conversation_id, metadata=None):
    """Send a message to a terminal"""
    try:
        print(f"Sending message to {terminal_url}: {text[:50]}...")
        terminal = A2AClient(terminal_url, timeout=30)
        terminal.send_message_async(
            Message(
                role=MessageRole.USER,
                content=TextContent(text=text),
                conversation_id=conversation_id,
                metadata=metadata or {}
            )
        )
        return True
    except Exception as e:
        print(f"Error sending to terminal {terminal_url}: {e}")
        return False


def send_to_ui_client(message_text, from_agent, conversation_id):
    if not UI_CLIENT_URL:
        print(f"No UI client URL configured. Cannot send message to UI client")
        return False

    try:
        print(f"Sending message to UI client: {message_text[:50]}...")
        response = requests.post(
            UI_CLIENT_URL,
            json={
                "message": message_text,
                "from_agent": from_agent,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            },
            timeout=10,
            verify=False # add this line to disable SSL verification
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


def send_to_agent(target_agent_id, message_text, conversation_id, metadata=None):
    """Send a message to another agent via their bridge"""
    # Look up the agent in the registry
    agent_url = lookup_agent(target_agent_id)
    if not agent_url:
        return f"Agent {target_agent_id} not found in registry"
    
    try:
        if not agent_url.endswith('/a2a'):
            target_bridge_url = f"{agent_url}/a2a"
            print(f"Adding /a2a to URL: {target_bridge_url}")
        else:
            target_bridge_url = agent_url
            print(f"URL already includes /a2a: {target_bridge_url}")

        # Use the URL directly (it already includes /a2a from registration)
        print(f"Sending message to {target_agent_id} at {target_bridge_url}")

        formatted_message = f"__EXTERNAL_MESSAGE__\n__FROM_AGENT__{AGENT_ID}\n__TO_AGENT__{target_agent_id}\n__MESSAGE_START__\n{message_text}\n__MESSAGE_END__"
        
        # Create simplified metadata
        try:
            # For python_a2a library compatibility, still try to set some metadata
            send_metadata = {
                'is_external': True,
                'from_agent_id': AGENT_ID,
                'to_agent_id': target_agent_id
            }
            if metadata:
                for key, value in metadata.items():
                    send_metadata[key] = value
                
            print(f"Custom Fields being sent: {send_metadata}")
        except:
            # If metadata handling fails, continue anyway since we've included the info in the message
            send_metadata = None
            print("Warning: Could not set metadata, but continuing with message format")

        # Send message to the target agent's bridge
        # target_bridge_url = target_bridge_url.rstrip("/a2a")
        # print(f"Target bridge URL: {target_bridge_url}")
        bridge_client = A2AClient(target_bridge_url, timeout=30)
        response = bridge_client.send_message(
            Message(
                role=MessageRole.USER,
                content=TextContent(text=formatted_message),
                conversation_id=conversation_id,
                metadata=send_metadata
            )
        )
        
        return f"Message sent to {target_agent_id}"
    except Exception as e:
        print(f"Error sending message to {target_agent_id}: {e}")
        return f"Error sending message to {target_agent_id}: {e}"


def get_mcp_server_url(requested_registry: str,qualified_name: str) -> Optional[str]:
    """
    Query MongoDB to find MCP server URL based on qualifiedName.
    
    Args:
        qualified_name (str): The qualifiedName to search for (e.g. "@opgginc/opgg-mcp")
        
    Returns:
        Optional[tuple]: Tuple of (endpoint, config_json, registry_name) if found, None otherwise
    """
    try:
        if not USE_MONGO:
            print("MongoDB not available")
            return None
        
        print(f"Querying MCP registry DB:{mcp_registry_col} for {qualified_name}")

        result = mcp_registry_col.find_one({"qualified_name": qualified_name,"registry_provider":{"$regex": f"^{requested_registry}$", "$options": "i"}})
        
        if result:
            endpoint = result.get("endpoint")
            config = result.get("config")
            config_json = json.loads(config)
            registry_name = result.get("registry_provider")
            print(f"Found MCP server URL for {qualified_name}: {endpoint} && {config_json}")
            return endpoint, config_json, registry_name
        else:
            print(f"No MCP server found for qualified_name: {qualified_name}")
            return None
            
    except Exception as e:
        print(f"Error querying MCP server URL: {e}")
        return None

def form_mcp_server_url(url: str, config: dict, registry_name: str) -> Optional[str]:
    """
    Form the MCP server URL based on the URL and config.
    
    Args:
        url (str): The URL of the MCP server
        config (dict): The config of the MCP server
        registry_name (str): The name of the registry provider
        
    Returns:
        Optional[str]: The mcp server URL if smithery api key is available, otherwise None
    """
    try:
        if registry_name == "smithery":
            print("🔑 Using SMITHERY_API_KEY: ", SMITHERY_API_KEY)
            smithery_api_key = SMITHERY_API_KEY
            if not smithery_api_key:
                print("❌ SMITHERY_API_KEY not found in environment.")
                return None
            config_b64 = base64.b64encode(json.dumps(config).encode())            
            mcp_server_url = f"{url}?api_key={smithery_api_key}&config={config_b64}"
        else:
            mcp_server_url = url
        return mcp_server_url

    except Exception as e:
        print(f"Issues with form_mcp_server_url: {e}")
        return None

async def run_mcp_query(query: str, updated_url: str) -> str:
    try:
        print(f"In run_mcp_query: MCP query: {query} on {updated_url}")

        async with MCPClient() as client:
            result = await client.process_query(query, updated_url)
            return result
    except Exception as e:
        error_msg = f"Error processing MCP query: {str(e)}"
        return error_msg

# Add the async method to the A2AClient class if it doesn't exist
if not hasattr(A2AClient, 'send_message_async'):
    def send_message_async(self, message: Message):
        """Send a message asynchronously without waiting for a response"""
        thread = threading.Thread(target=self.send_message, args=(message,))
        thread.daemon = True
        thread.start()
        return thread
    
    # Add the method to the class
    A2AClient.send_message_async = send_message_async


# Update handle_message to detect this special format
def handle_external_message(msg_text, conversation_id, msg):
    """Handle specially formatted external messages"""
    try:
        # Parse the special message format
        lines = msg_text.split('\n')
        
        # Check if this is our special format
        if lines[0] != '__EXTERNAL_MESSAGE__':
            return None
        
        # Extract metadata from the message
        from_agent = None
        to_agent = None
        message_content = ""
        
        # Parse the header fields
        in_message = False
        for line in lines[1:]:
            if line.startswith('__FROM_AGENT__'):
                from_agent = line[len('__FROM_AGENT__'):]
            elif line.startswith('__TO_AGENT__'):
                to_agent = line[len('__TO_AGENT__'):]
            elif line == '__MESSAGE_START__':
                in_message = True
            elif line == '__MESSAGE_END__':
                in_message = False
            elif in_message:
                message_content += line + '\n'
        
        # Trim trailing newline
        message_content = message_content.rstrip()
        
        print(f"Received external message from {from_agent} to {to_agent}")
        
        # Format the message for display in terminal
        formatted_text = f"FROM {from_agent}: {message_content}"
        
        print("Message Text: ", message_content)
        print("UI MODE: ", UI_MODE)

        # If in UI mode, forward to all registered UI clients
        if UI_MODE:
            print(f"Forwarding message to UI client")
            send_to_ui_client(formatted_text, from_agent, conversation_id)
            
            # Acknowledge receipt to sender
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=f"Message received by Agent {AGENT_ID}"),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )
        # Otherwise, forward to local terminal (original behavior
        else:
            try:
                terminal_client = A2AClient(LOCAL_TERMINAL_URL, timeout=10)
                terminal_client.send_message_async(
                    Message(
                        role=MessageRole.USER,
                        content=TextContent(text=formatted_text),
                        conversation_id=conversation_id,
                        metadata={
                            'is_from_peer': True,
                            'is_user_message': True,
                            'source_agent': from_agent,
                            'forwarded_by_bridge': True
                        }
                    )
                )
                
                # Acknowledge receipt to sender
                return Message(
                    role=MessageRole.AGENT,
                    content=TextContent(text=f"Message received by Agent {AGENT_ID}"),
                    parent_message_id=msg.message_id,
                    conversation_id=conversation_id
                )
            except Exception as e:
                print(f"Error forwarding to local terminal: {e}")
                return Message(
                    role=MessageRole.AGENT,
                    content=ErrorContent(message=f"Failed to deliver message: {str(e)}"),
                    parent_message_id=msg.message_id,
                    conversation_id=conversation_id
                )
            
    except Exception as e:
        print(f"Error parsing external message: {e}")
        return None  # Not our special format or parsing failed


class AgentBridge(A2AServer):
    """Global Agent Bridge - Can be used for any agent in the network."""

    def handle_message(self, msg: Message) -> Message:
        # Ensure we have a conversation ID
        conversation_id = msg.conversation_id or str(uuid.uuid4())
        print(f"Agent {AGENT_ID}: Received message with ID: {msg.message_id}")
        print(f"[DEBUG] Message type: {type(msg.content)}")
        print(f"[DEBUG] Message ID: {msg.message_id}")
        print(f"Agent {AGENT_ID}: Message metadata: {msg.metadata}")

        user_text = msg.content.text
        print(f"Agent {AGENT_ID}: Received text: {user_text[:50]}...")
        
        # Extract metadata
        if hasattr(msg.metadata, 'custom_fields'):
            # Handle Metadata object format
            metadata = msg.metadata.custom_fields or {}
            print(f"Using custom_fields: {metadata}")
        else:
            # Handle dictionary format
            metadata = msg.metadata or {}
            print(f"Using direct metadata: {metadata}")

        path = metadata.get('path', '')
        source_agent = metadata.get('source_agent', '')
        is_from_peer = metadata.get('is_from_peer', False)
        is_external = metadata.get('is_external', False)  # Check if this is an external message
        from_agent = metadata.get('from_agent_id', 'unknown')
        additional_context = metadata.get('additional_context', '')
        
        # Add current agent ID to the path
        current_path = path + ('>' if path else '') + AGENT_ID
        print(f"Agent {AGENT_ID}: Current path: {current_path}")
        
        # Handle non-text content
        if not isinstance(msg.content, TextContent):
            print(f"Agent {AGENT_ID}: Received non-text content. Returning error.")
            return Message(
                role = MessageRole.AGENT,
                content = ErrorContent(message="Only text payloads supported."),
                parent_message_id = msg.message_id,
                conversation_id = conversation_id
            )
        
        if user_text.startswith('__EXTERNAL_MESSAGE__'):
            print("--- External Message Detected ---")
            external_response = handle_external_message(user_text, conversation_id, msg)
            if external_response:
                return external_response
        
        # Regular processing for messages from the local terminal or peer
        # Handle regular processing for messages from the local terminal or peer
        if is_from_peer:
            # Handle messages from peer agents - already processed by our terminal
            # Just return acknowledgment
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=f"Message from peer received"),
                parent_message_id=msg.message_id,
                conversation_id=conversation_id
            )
        else:
            # Message from local terminal user
            log_message(conversation_id, current_path, f"Local user to Agent {AGENT_ID}", user_text)
            print(f"#jinu - User text: {user_text}")
            # Check if this is a message to another agent (starts with @)
            if user_text.startswith("@"):
                # Parse the recipient
                parts = user_text.split(" ", 1)
                if len(parts) > 1:
                    target_agent = parts[0][1:]  # Remove the @ symbol
                    message_text = parts[1]

                    # Improve message if feature is enabled
                    if IMPROVE_MESSAGES:
                        message_text = improve_message(message_text, conversation_id, current_path,
                            "Do not respond to the content of the message - it's intended for another agent. You are helping an agent communicate better with other agennts.")
                    
                    print(f"#jinu - Target agent: {target_agent}")
                    print(f"#jinu - Imoproved message text: {message_text}")
                    # Send to the target agent's bridge
                    result = send_to_agent(target_agent, message_text, conversation_id, {
                        'path': current_path,
                        'source_agent': AGENT_ID
                    })
                    
                    # Return result to user
                    return Message(
                        role=MessageRole.AGENT,
                        content=TextContent(text=f"[AGENT {AGENT_ID}]: {message_text}"),
                        parent_message_id=msg.message_id,
                        conversation_id=conversation_id
                    )
                else:
                    # Invalid @ command format
                    return Message(
                        role=MessageRole.AGENT,
                        content=TextContent(text=f"[AGENT {AGENT_ID}] Invalid format. Use '@agent_id message' to send a message."),
                        parent_message_id=msg.message_id,
                        conversation_id=conversation_id
                    )
            
            elif user_text.startswith("#"):
                # Parse the command
                print((f"Detected natural language command: {user_text}"))
                parts = user_text.split(" ", 1)
                
                if len(parts)>1 and len(parts[0][1:].split(":",1))==2:
                    requested_registry,mcp_server_to_call = parts[0][1:].split(":",1)
                    query = parts[1]
                    print(f"Requested registry: {requested_registry}, MCP server to call: {mcp_server_to_call}, query: {query}")
                    # Get the MCP server URL and config details
                    response = get_mcp_server_url(requested_registry,mcp_server_to_call)
                    print("Response from get_mcp_server_url: ", response)
                    if response is None:    
                        return Message(
                            role=MessageRole.AGENT,
                            content=TextContent(text=f"[AGENT {AGENT_ID}] MCP server '{mcp_server_to_call}' not found in registry. Please check the server name and try again."),
                            parent_message_id=msg.message_id,
                            conversation_id=conversation_id
                        )
                    else:
                        mcp_server_url, config_details, registry_name = response
                    print(f"Recieved details from DB: {mcp_server_url}, {config_details}, {registry_name}")
                    # Form the MCP server URL
                    mcp_server_final_url = form_mcp_server_url(mcp_server_url, config_details, registry_name)
                    print(f"MCP server final URL: {mcp_server_final_url}")
                    if mcp_server_final_url is None:
                        return Message(
                            role=MessageRole.AGENT,
                            content=TextContent(text=f"[AGENT {AGENT_ID}] Ensure the required API key for registery is in env file"),
                            parent_message_id=msg.message_id,
                            conversation_id=conversation_id
                        )
                    print(f"Running MCP query: {query} on {mcp_server_final_url}")
                    result = asyncio.run(run_mcp_query(query, mcp_server_final_url))    

                    print(f"# Result from MCP query: {result}")
                    return Message( 
                        role=MessageRole.AGENT,
                        content=TextContent(text=f"{result}"),
                        parent_message_id=msg.message_id,
                        conversation_id=conversation_id
                    )
                    
                else:
                    # Invalid # command format
                    return Message(
                        role=MessageRole.AGENT,
                        content=TextContent(text=f"[AGENT {AGENT_ID}] Invalid format. Use '#registry_provider:mcp_server_name query' to send a query to an MCP server."),
                        parent_message_id=msg.message_id,
                        conversation_id=conversation_id
                    )
            
            # Check if this is a command (starts with /)
            elif user_text.startswith("/"):
                # Parse the command
                parts = user_text.split(" ", 1)
                command = parts[0][1:] if len(parts) > 0 else ""
                
                # Handle special commands
                if command == "quit":
                    # Quit command - acknowledge but let terminal handle the actual quitting
                    return Message(
                        role = MessageRole.AGENT,
                        content = TextContent(text=f"[AGENT {AGENT_ID}] Exiting session..."),
                        parent_message_id = msg.message_id,
                        conversation_id = conversation_id
                    )
                
                elif command == "help":
                    # Help command - show only valid commands
                    help_text = """Available commands:
                        /help - Show this help message
                        /quit - Exit the terminal
                        /query [message] - Get a response from the agent privately
                        @<agent_id> [message] - Send a message to a specific agent"""
                    return Message(
                        role = MessageRole.AGENT,
                        content = TextContent(text=f"[AGENT {AGENT_ID}] {help_text}"),
                        parent_message_id = msg.message_id,
                        conversation_id = conversation_id
                    )
                
                elif command == "query":
                    # Process query command - this is for local assistance
                    if len(parts) > 1:
                        query_text = parts[1]
                        print(f"Processing query command: '{query_text}'")

                        # Call Claude with the query
                        claude_response = call_claude(query_text, additional_context, conversation_id, current_path,
                            "You are Claude, an AI assistant. Provide a direct, helpful response to the user's question. Treat it as a private request for guidance and respond only to the user.")
                        
                        # Make sure we have a valid response
                        if not claude_response:
                            print("Warning: Claude returned empty response")
                            claude_response = "Sorry, I couldn't process your query. Please try again."
                        else:
                            print(f"Claude response received ({len(claude_response)} chars)")
                            print(f"Response preview: {claude_response[:50]}...")

                        # Format and return the response
                        formatted_response = f"[AGENT {AGENT_ID}] {claude_response}"
                        
                        # Return to local terminal
                        response_message = Message(
                            role = MessageRole.AGENT,
                            content = TextContent(text=formatted_response),
                            parent_message_id = msg.message_id,
                            conversation_id = conversation_id
                        )

                        return response_message
                    else:
                        # No query text provided
                        return Message(
                            role = MessageRole.AGENT,
                            content = TextContent(text=f"[AGENT {AGENT_ID}] Please provide a query after the /query command."),
                            parent_message_id = msg.message_id,
                            conversation_id = conversation_id
                        )
                else:
                    # Invalid command
                    help_text = """Unknown command. Available commands:
                        /help - Show this help message
                        /quit - Exit the terminal
                        /query [message] - Get a response from the agent privately
                        @<agent_id> [message] - Send a message to a specific agent"""
                    return Message(
                            role = MessageRole.AGENT,
                            content = TextContent(text=f"[AGENT {AGENT_ID}] {help_text}"),
                            parent_message_id = msg.message_id,
                            conversation_id = conversation_id
                        )
                            
            else:
                # Regular message - process locally 
                claude_response = call_claude(user_text, additional_context, conversation_id, current_path) or user_text
                formatted_response = f"[AGENT {AGENT_ID}] {claude_response}"
                
                # Return Claude's response to local terminal
                return Message(
                    role = MessageRole.AGENT,
                    content = TextContent(text=formatted_response),
                    parent_message_id = msg.message_id,
                    conversation_id = conversation_id
                )

if __name__ == "__main__":
    # Register with the registry if PUBLIC_URL is set
    public_url = os.getenv("PUBLIC_URL")
    api_url = os.getenv("API_URL")
    if public_url:
        register_with_registry(AGENT_ID, public_url, api_url)
    else:
        print("WARNING: PUBLIC_URL environment variable not set. Agent will not be registered.")
    
    IMPROVE_MESSAGES = os.getenv("IMPROVE_MESSAGES", "true").lower() in ("true", "1", "yes", "y")

    print(f"Starting Agent {AGENT_ID} bridge on port {PORT}")
    print(f"Agent terminal port: {TERMINAL_PORT}")
    print(f"Message improvement feature is {'ENABLED' if IMPROVE_MESSAGES else 'DISABLED'}")
    print(f"Logging conversations to {os.path.abspath(LOG_DIR)}")
    run_server(AgentBridge(), host="0.0.0.0", port=PORT)
