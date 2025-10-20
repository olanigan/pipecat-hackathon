#!/usr/bin/env python3
"""Test script for AI Copilot MCP integrations."""

import asyncio
from pipecat.services.mcp_service import MCPClient
from mcp.client.session_group import StreamableHttpParameters
from mcp.client.stdio import StdioServerParameters

async def test_ai_copilot_mcps():
    """Test all AI Copilot MCP integrations."""
    print("🤖 Testing AI Copilot MCP integrations...")

    mcp_clients = []

    # MCP Labs for AI news (currently not available - website, not MCP server)
    # try:
    #     mcplabs_client = MCPClient(
    #         server_params=StreamableHttpParameters(  # type: ignore
    #             url="https://mcplabs.dev/mcp",
    #             headers={},
    #         )
    #     )
    #     mcp_clients.append(("MCP Labs", mcplabs_client))
    #     print("✅ MCP Labs client initialized successfully")
    # except Exception as e:
    #     print(f"⚠️  MCP Labs not available (website, not MCP server): {e}")
    print("⚠️  MCP Labs skipped (website, not MCP server)")

    # ArXiv MCP Server for research papers
    try:
        import sys
        arxiv_client = MCPClient(
            server_params=StdioServerParameters(  # type: ignore
                command=sys.executable,
                args=["-m", "arxiv_mcp_server"],
            )
        )
        mcp_clients.append(("ArXiv", arxiv_client))
        print("✅ ArXiv MCP client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ArXiv MCP client: {e}")

    # HuggingFace MCP Server for model access
    try:
        import sys
        hf_client = MCPClient(
            server_params=StdioServerParameters(  # type: ignore
                command=sys.executable,
                args=["-c", "import huggingface; huggingface.main()"],
            )
        )
        mcp_clients.append(("HuggingFace", hf_client))
        print("✅ HuggingFace MCP client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize HuggingFace MCP client: {e}")

    # Mock LLM for testing
    class MockLLM:
        def __init__(self):
            self._functions = {}
        
        def needs_mcp_alternate_schema(self):
            return False
        
        def register_function(self, name, func):
            """Register a function with the mock LLM."""
            self._functions[name] = func
            print(f"   📝 Registered function: {name}")

    llm = MockLLM()
    total_tools = 0

    # Test tool registration for each client
    for client_name, mcp_client in mcp_clients:
        try:
            print(f"🔗 Testing {client_name} tool registration...")
            tools = await mcp_client.register_tools(llm)
            tool_count = len(tools.standard_tools)
            tool_names = [tool.name for tool in tools.standard_tools]
            total_tools += tool_count
            print(f"✅ {client_name}: {tool_count} tools registered")
            if tool_names:
                print(f"   📋 Tools: {', '.join(tool_names[:5])}{'...' if len(tool_names) > 5 else ''}")
        except Exception as e:
            print(f"❌ {client_name} tool registration failed: {e}")

    print(f"\n🎉 AI Copilot MCP Integration Test Complete!")
    print(f"📊 Total MCP sources: {len(mcp_clients)}")
    print(f"🛠️  Total tools available: {total_tools}")

    if total_tools > 0:
        print("✅ AI Copilot is ready with MCP integrations!")
        return True
    else:
        print("⚠️  No tools available - check MCP server configurations")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ai_copilot_mcps())
    exit(0 if success else 1)