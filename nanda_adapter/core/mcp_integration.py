"""
MCP (Model Context Protocol) integration module for NANDA Agent Bridge.
Handles MCP server discovery, URL formation, and query execution.
"""
import os
import json
import base64
import asyncio
import requests
from typing import Optional, Tuple
from urllib.parse import urlparse
from .registry import get_registry_url
from .mcp_utils import MCPClient


SMITHERY_API_KEY = os.getenv("SMITHERY_API_KEY") or "bfcb8cec-9d56-4957-8156-bced0bfca532"


def get_mcp_server_url(requested_registry: str, qualified_name: str) -> Optional[Tuple[str, dict, str]]:
    """
    Query registry endpoint to find MCP server URL based on qualifiedName.
    
    Args:
        requested_registry (str): The registry provider to search in
        qualified_name (str): The qualifiedName to search for (e.g. "@opgginc/opgg-mcp")
        
    Returns:
        Optional[tuple]: Tuple of (endpoint, config_json, registry_name) if found, None otherwise
    """
    try:
        registry_url = get_registry_url()
        endpoint_url = f"{registry_url}/get_mcp_registry"
        
        print(f"Querying MCP registry endpoint: {endpoint_url} for {qualified_name}")
        
        # Make request to the registry endpoint
        response = requests.get(endpoint_url, params={
            'registry_provider': requested_registry,
            'qualified_name': qualified_name
        })
        
        if response.status_code == 200:
            result = response.json()
            endpoint = result.get("endpoint")
            config = result.get("config")
            config_json = json.loads(config) if isinstance(config, str) else config
            registry_name = result.get("registry_provider")
            print(f"Found MCP server URL for {qualified_name}: {endpoint} && {config_json}")
            return endpoint, config_json, registry_name
        else:
            print(f"No MCP server found for qualified_name: {qualified_name} (Status: {response.status_code})")
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
    """
    Execute an MCP query against the specified server URL.
    
    Args:
        query (str): The query to execute
        updated_url (str): The complete MCP server URL
        
    Returns:
        str: Query result or error message
    """
    try:
        print(f"In run_mcp_query: MCP query: {query} on {updated_url}")
        
        # Determine transport type based on URL path (before query parameters)
        parsed_url = urlparse(updated_url)
        transport_type = "sse" if parsed_url.path.endswith("/sse") else "http"
        print(f"Using transport type: {transport_type} for path: {parsed_url.path}")

        async with MCPClient() as client:
            result = await client.process_query(query, updated_url, transport_type)
            return result
    except Exception as e:
        error_msg = f"Error processing MCP query: {str(e)}"
        return error_msg


def handle_mcp_command(user_text: str, agent_id: str) -> Tuple[bool, str]:
    """
    Handle MCP command parsing and execution.
    
    Args:
        user_text (str): The user input starting with #
        agent_id (str): The current agent ID
        
    Returns:
        Tuple[bool, str]: (success, result_message)
    """
    try:
        # Parse the command
        print(f"Detected natural language command: {user_text}")
        parts = user_text.split(" ", 1)
        
        if len(parts) > 1 and len(parts[0][1:].split(":", 1)) == 2:
            requested_registry, mcp_server_to_call = parts[0][1:].split(":", 1)
            query = parts[1]
            print(f"Requested registry: {requested_registry}, MCP server to call: {mcp_server_to_call}, query: {query}")
            
            # Get the MCP server URL and config details
            response = get_mcp_server_url(requested_registry, mcp_server_to_call)
            print("Response from get_mcp_server_url: ", response)
            
            if response is None:    
                return False, f"[AGENT {agent_id}] MCP server '{mcp_server_to_call}' not found in registry. Please check the server name and try again."
            else:
                mcp_server_url, config_details, registry_name = response
                
            print(f"Received details from DB: {mcp_server_url}, {config_details}, {registry_name}")
            
            # Form the MCP server URL
            mcp_server_final_url = form_mcp_server_url(mcp_server_url, config_details, registry_name)
            print(f"MCP server final URL: {mcp_server_final_url}")
            
            if mcp_server_final_url is None:
                return False, f"[AGENT {agent_id}] Ensure the required API key for registry is in env file"
                
            print(f"Running MCP query: {query} on {mcp_server_final_url}")
            result = asyncio.run(run_mcp_query(query, mcp_server_final_url))    

            print(f"# Result from MCP query: {result}")
            return True, result
        else:
            return False, f"[AGENT {agent_id}] Invalid format. Use '#registry_provider:mcp_server_name query' to send a query to an MCP server."
            
    except Exception as e:
        print(f"Error handling MCP command: {e}")
        return False, f"[AGENT {agent_id}] Error processing MCP command: {str(e)}"