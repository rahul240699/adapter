#!/usr/bin/env python3
"""
MCP Client utilities for NANDA agents

This module provides MCP (Model Context Protocol) client functionality
for connecting to and querying MCP servers from NANDA agents.
"""

import os
import json
import asyncio
import base64
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
import logging

# MCP imports
try:
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamablehttp_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# Anthropic import
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)

def parse_jsonrpc_response(response) -> str:
    """
    Helper function to parse JSON-RPC responses from MCP server.
    
    Args:
        response: Raw response from MCP server
        
    Returns:
        Parsed text content
    """
    if isinstance(response, str):
        try:
            response_json = json.loads(response)
            if isinstance(response_json, dict) and "result" in response_json:
                # Extract text from JSON-RPC structure
                artifacts = response_json["result"].get("artifacts", [])
                if artifacts and len(artifacts) > 0:
                    parts = artifacts[0].get("parts", [])
                    if parts and len(parts) > 0:
                        return parts[0].get("text", str(response))
        except json.JSONDecodeError:
            pass
    return str(response)


class MCPClient:
    """
    MCP client for connecting to and querying MCP servers.
    
    Handles both HTTP and SSE transport protocols and integrates
    with Claude for intelligent tool usage.
    """
    
    def __init__(self, anthropic_client=None):
        """
        Initialize MCP client.
        
        Args:
            anthropic_client: Optional existing Anthropic client to reuse
        """
        if not MCP_AVAILABLE:
            raise ImportError("MCP library not available. Install with: pip install mcp")
            
        self.session = None
        self.exit_stack = AsyncExitStack()
        
        # Use provided client or create new one
        if anthropic_client:
            self.anthropic = anthropic_client
            logger.info("✅ MCP client initialized with provided Anthropic client")
        else:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("Anthropic library not available. Install with: pip install anthropic")
            
            # Initialize Anthropic client from environment
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable required")
                
            self.anthropic = Anthropic(api_key=anthropic_api_key)
            logger.info("✅ MCP client initialized with new Anthropic client")
    
    async def connect_to_mcp_and_get_tools(self, mcp_server_url: str, transport_type: str = "http") -> Optional[List]:
        """
        Connect to MCP server and return available tools.
        
        Args:
            mcp_server_url: URL of the MCP server
            transport_type: Either 'http' or 'sse' for transport protocol
            
        Returns:
            List of available tools or None if connection failed
        """
        try:
            logger.info(f"🔗 Connecting to MCP server: {mcp_server_url} ({transport_type})")
            
            # Create new connection based on transport type
            if transport_type.lower() == "sse":
                transport = await self.exit_stack.enter_async_context(sse_client(mcp_server_url))
                # SSE client returns only 2 values: read_stream, write_stream
                read_stream, write_stream = transport
            else:
                transport = await self.exit_stack.enter_async_context(streamablehttp_client(mcp_server_url))
                # HTTP client returns 3 values: read_stream, write_stream, session
                read_stream, write_stream, _ = transport
            
            # Create new session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self.session.initialize()
            
            # Get tools
            tools_result = await self.session.list_tools()
            logger.info(f"✅ Connected to MCP server, found {len(tools_result.tools)} tools")
            return tools_result.tools
            
        except Exception as e:
            logger.error(f"❌ Error connecting to MCP server: {e}")
            return None
    
    async def process_query(self, query: str, mcp_server_url: str, transport_type: str = "http") -> str:
        """
        Process a query against an MCP server using Claude integration.
        
        Args:
            query: User query to process
            mcp_server_url: URL of the MCP server
            transport_type: Either 'http' or 'sse' for transport protocol
            
        Returns:
            Response text from the MCP server via Claude
        """
        try:
            logger.info(f"🧠 Processing MCP query: '{query[:50]}...' on {mcp_server_url} using {transport_type}")
            
            # Connect and get tools
            tools = await self.connect_to_mcp_and_get_tools(mcp_server_url, transport_type)
            if not tools:
                return "❌ Failed to connect to MCP server or no tools available"

            # Prepare tools for Claude
            available_tools = [{
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in tools]

            logger.info(f"🔧 Available tools: {[tool['name'] for tool in available_tools]}")

            # Initialize message history
            messages = [{"role": "user", "content": query}]
            
            # Call Claude API with tools
            message = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=messages,
                tools=available_tools
            )
            
            # Process tool calls iteratively
            max_iterations = 5
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                has_tool_calls = False
                
                logger.info(f"🔄 Processing Claude response (iteration {iteration})")
                
                # Process each block in the response
                for block in message.content:
                    logger.debug(f"Processing block type: {block.type}")
                    
                    if block.type == "tool_use":
                        has_tool_calls = True
                        # Extract tool name and arguments
                        tool_name = block.name
                        tool_args = block.input
                        
                        logger.info(f"🔧 Calling tool: {tool_name} with args: {tool_args}")
                        
                        # Call the tool via MCP
                        result = await self.session.call_tool(tool_name, tool_args)
                        logger.debug(f"Raw tool result: {str(result)[:200]}...")
                        
                        # Parse the result
                        processed_result = parse_jsonrpc_response(result)
                        logger.info(f"✅ Tool result: {str(processed_result)[:100]}...")
                        
                        # Add the assistant's message with tool use
                        messages.append({
                            "role": "assistant",
                            "content": [{
                                "type": "tool_use",
                                "id": block.id,
                                "name": tool_name,
                                "input": tool_args
                            }]
                        })
                        
                        # Add the tool result
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(processed_result)
                            }]
                        })
                
                # If no tool calls were made, we have our final response
                if not has_tool_calls:
                    break
                    
                logger.info("🔄 Getting next response from Claude...")
                # Get next response from Claude
                message = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    messages=messages,
                    tools=available_tools
                )
            
            # Extract final response text
            final_response = ""
            for block in message.content:
                if block.type == "text":
                    final_response += block.text + "\n"
                    
            result_text = parse_jsonrpc_response(final_response.strip()) if final_response else "No response generated"
            logger.info(f"✅ MCP query completed: {len(result_text)} characters")
            return result_text
            
        except Exception as e:
            error_msg = f"❌ Error processing MCP query: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.exit_stack.aclose()
        self.session = None


def form_mcp_server_url(base_url: str, config: Dict[str, Any], registry_provider: str) -> Optional[str]:
    """
    Form the complete MCP server URL based on the base URL, config, and registry provider.
    
    Args:
        base_url: Base URL of the MCP server
        config: Server configuration dictionary
        registry_provider: Registry provider name
        
    Returns:
        Complete MCP server URL or None if requirements not met
    """
    try:
        if registry_provider == "smithery":
            # Smithery requires API key and config
            smithery_api_key = os.getenv("SMITHERY_API_KEY")
            if not smithery_api_key:
                logger.error("❌ SMITHERY_API_KEY not found in environment")
                return None
                
            # Encode config as base64
            config_b64 = base64.b64encode(json.dumps(config).encode()).decode()
            mcp_server_url = f"{base_url}?api_key={smithery_api_key}&config={config_b64}"
            
            logger.info(f"🔑 Formed Smithery MCP URL with API key")
            return mcp_server_url
            
        else:
            # For other providers, use URL as-is
            logger.info(f"🔗 Using direct MCP URL for provider: {registry_provider}")
            return base_url
            
    except Exception as e:
        logger.error(f"❌ Error forming MCP server URL: {e}")
        return None


async def run_mcp_query(query: str, mcp_server_url: str) -> str:
    """
    Convenience function to run an MCP query.
    
    Args:
        query: User query to process
        mcp_server_url: Complete MCP server URL
        
    Returns:
        Response text from the MCP server
    """
    try:
        logger.info(f"🚀 Running MCP query: '{query[:50]}...' on {mcp_server_url}")
        
        # Determine transport type based on URL path
        from urllib.parse import urlparse
        parsed_url = urlparse(mcp_server_url)
        transport_type = "sse" if parsed_url.path.endswith("/sse") else "http"
        
        logger.info(f"🔧 Using transport type: {transport_type}")

        async with MCPClient() as client:
            result = await client.process_query(query, mcp_server_url, transport_type)
            return result
            
    except Exception as e:
        error_msg = f"❌ Error running MCP query: {str(e)}"
        logger.error(error_msg)
        return error_msg


# Example usage
if __name__ == "__main__":
    import asyncio
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    async def test_mcp_client():
        """Test MCP client functionality."""
        # This would require a real MCP server URL
        test_url = "http://localhost:3000"
        test_query = "What tools are available?"
        
        try:
            result = await run_mcp_query(test_query, test_url)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Run test
    # asyncio.run(test_mcp_client())