#!/usr/bin/env python3
"""Test script for MCP Labs client initialization and tool registration."""

import asyncio
from pipecat.services.mcp_service import MCPClient
from mcp.client.session_group import StreamableHttpParameters

async def test_mcplabs():
    """Test MCP Labs client initialization and tool registration."""
    print("🔧 Testing MCP Labs client initialization...")

    try:
        mcp_client = MCPClient(
            server_params=StreamableHttpParameters(
                url="https://mcplabs.dev/mcp",
                headers={},
            )
        )
        print("✅ MCP Labs client initialized successfully")

        # Mock LLM for testing
        class MockLLM:
            def needs_mcp_alternate_schema(self):
                return False

        llm = MockLLM()

        print("🔗 Testing tool registration...")
        tools = await mcp_client.register_tools(llm)
        tool_count = len(tools.standard_tools)
        tool_names = [tool.name for tool in tools.standard_tools]
        print(f"✅ Successfully registered {tool_count} MCP tools")
        print(f"📋 Available tools: {', '.join(tool_names)}")

        return True
    except Exception as e:
        print(f"❌ Failed MCP Labs test: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcplabs())
    exit(0 if success else 1)