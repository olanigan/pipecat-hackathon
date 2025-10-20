#!/usr/bin/env python3
"""Test script for MCP client initialization and tool registration."""

import os
import asyncio
import logging
from dotenv import load_dotenv
from langfuse import Langfuse
from pipecat.services.mcp_service import MCPClient
from mcp.client.session_group import StreamableHttpParameters

# Enable debug logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("langfuse").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

async def test_mcp_tools():
    """Test MCP client initialization and tool registration."""
    load_dotenv(override=True)

    # Initialize Langfuse if enabled
    if os.getenv("ENABLE_TRACING", "false").lower() == "true":
        logger.info("Langfuse tracing enabled")
        langfuse = Langfuse(
            public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", "pk-lf-local"),
            secret_key=os.environ.get("LANGFUSE_SECRET_KEY", "sk-lf-local-secret-key"),
            host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
        )
        logger.info("Langfuse client initialized")
    else:
        logger.info("Langfuse tracing disabled")
        langfuse = None

    # Initialize MCP client
    logger.info("🔧 Initializing MCP client...")
    try:
        mcp_client = MCPClient(
            server_params=StreamableHttpParameters(
                url="https://langfuse.com/api/mcp",
                headers={},
            )
        )
        logger.info("✅ MCP client initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP client: {e}")
        return False

    # Mock LLM service for testing
    class MockLLM:
        pass

    llm = MockLLM()

    # Register tools
    try:
        logger.info("🔗 Registering MCP tools with LLM...")
        tools = await mcp_client.register_tools(llm)
        tool_count = len(tools.standard_tools)
        tool_names = [tool.name for tool in tools.standard_tools]
        logger.info(f"✅ Successfully registered {tool_count} MCP tools")
        logger.info(f"📋 Registered MCP Tools: {', '.join(tool_names)}")

        # Create span for tracking
        if langfuse:
            span = langfuse.start_span(
                name="mcp_tools_registered",
                metadata={
                    "service": "langfuse_mcp",
                    "conversation_id": "test-conversation",
                    "tools_count": tool_count,
                }
            )
            span.end()

    except Exception as e:
        logger.error(f"❌ Error registering MCP tools: {e}")
        if langfuse:
            span = langfuse.start_span(
                name="mcp_error",
                metadata={
                    "service": "langfuse_mcp",
                    "conversation_id": "test-conversation",
                    "error_type": type(e).__name__,
                    "operation": "register_tools",
                }
            )
            span.set_attribute("error.message", str(e))
            span.end()
        return False

    # Flush Langfuse data
    if langfuse:
        logger.info("🔄 Flushing Langfuse data...")
        langfuse.flush()
        import time
        time.sleep(5)

    logger.info("✅ MCP test completed successfully!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_mcp_tools())
    exit(0 if success else 1)