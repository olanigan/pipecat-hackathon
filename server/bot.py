"""AI Copilot with MCP integration for AI news and research.

Features:
- Real-time audio via Daily
- Text-to-speech via Cartesia
- AI news and research MCP connections
- Access to latest AI developments and papers
"""

import asyncio
import os
import signal
import uuid
import datetime
from typing import cast, List, Any

from dotenv import load_dotenv
from loguru import logger
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from langfuse import Langfuse  # type: ignore
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    LLMRunFrame,
    TextFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext, LLMContextMessage
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.mcp_service import MCPClient
from pipecat.transports.services.daily import DailyParams, DailyTransport
from mcp.client.session_group import StreamableHttpParameters
from mcp.client.stdio import StdioServerParameters

# System prompt for the AI Copilot
SYSTEM_PROMPT = """
You are an AI Copilot specializing in AI news, research, and latest developments. You help users stay informed about cutting-edge AI advancements, research papers, model releases, and industry trends.

## Core Capabilities
- Access to AI news sources, research papers, and model repositories
- Real-time information about AI developments and breakthroughs
- Analysis of research papers and technical documentation
- Guidance on AI tools, models, and implementations

## Response Rules
- Search AI news sources and research databases before answering
- Provide current, factual information about AI developments
- Be informative yet concise - focus on key insights and actionable information
- Use available tools extensively to gather comprehensive AI information
- If information is incomplete, search additional sources or state limitations
- Help users understand AI research and its practical applications
- Stay current with the latest AI developments and trends

## Communication Style
- Professional but approachable tone
- Clear explanations of complex AI concepts
- Focus on practical value and real-world applications
- Encourage exploration and learning in AI
"""

load_dotenv(override=True)

# Initialize Langfuse tracing if enabled
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


# Global variables for cleanup
shutdown_event = asyncio.Event()
transport = None
mcp_clients = []

# Initialize MCP clients at startup
logger.info("🔧 Initializing MCP clients at startup...")

# MCP Labs for AI news (currently not available - website, not MCP server)
# try:
#     mcplabs_client = MCPClient(
#         server_params=StreamableHttpParameters(  # type: ignore
#             url="https://mcplabs.dev/mcp",
#             headers={},
#         )
#     )
#     mcp_clients.append(("mcplabs", mcplabs_client))
#     logger.info("✅ MCP Labs client initialized successfully")
# except Exception as e:
#     logger.error(f"❌ Failed to initialize MCP Labs client: {e}")
logger.info("⚠️ MCP Labs skipped (website, not MCP server)")

# ArXiv MCP Server for research papers
try:
    import sys
    arxiv_client = MCPClient(
        server_params=StdioServerParameters(  # type: ignore
            command=sys.executable,
            args=["-m", "arxiv_mcp_server"],
        )
    )
    mcp_clients.append(("arxiv", arxiv_client))
    logger.info("✅ ArXiv MCP client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize ArXiv MCP client: {e}")

# HuggingFace MCP Server for model access
try:
    import sys
    hf_client = MCPClient(
        server_params=StdioServerParameters(  # type: ignore
            command=sys.executable,
            args=["-c", "import huggingface; huggingface.main()"],
        )
    )
    mcp_clients.append(("huggingface", hf_client))
    logger.info("✅ HuggingFace MCP client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize HuggingFace MCP client: {e}")


async def shutdown_handler():
    """Clean shutdown of all async resources."""
    logger.info("🛑 Initiating graceful shutdown...")

    # Signal shutdown event
    shutdown_event.set()

    # Cancel all pending tasks except current
    current_task = asyncio.current_task()
    tasks = [t for t in asyncio.all_tasks() if t is not current_task and not t.done()]
    if tasks:
        logger.info(f"🧹 Cancelling {len(tasks)} pending tasks...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("✅ All pending tasks cancelled")

    # Close transport connections
    global transport
    if transport:
        try:
            logger.info("🔌 Closing transport connections...")
            # Set transport to None to prevent further callbacks
            # DailyTransport will be cleaned up by PipelineRunner
            transport = None
            logger.info("✅ Transport cleanup completed")
        except Exception as e:
            logger.error(f"❌ Error during transport cleanup: {e}")

    # Close MCP clients
    global mcp_clients
    for client_name, mcp_client in mcp_clients:
        try:
            logger.info(f"🔌 Closing {client_name} connections...")
            # MCP client cleanup if needed
            logger.info(f"✅ {client_name} cleanup completed")
        except Exception as e:
            logger.error(f"❌ Error during {client_name} cleanup: {e}")

    # Flush Langfuse data
    if langfuse:
        try:
            logger.info("🔄 Flushing Langfuse data...")
            langfuse.flush()
            logger.info("✅ Langfuse data flushed")
        except Exception as e:
            logger.error(f"❌ Error flushing Langfuse data: {e}")

    logger.info("✅ Graceful shutdown completed")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    logger.info(f"📡 Received {signal_name}, initiating shutdown...")
    asyncio.create_task(shutdown_handler())


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def is_event_loop_closed():
    """Check if the current event loop is closed."""
    try:
        loop = asyncio.get_running_loop()
        return loop.is_closed()
    except RuntimeError:
        # No running loop
        return True


async def safe_event_handler(handler_func):
    """Wrapper to safely execute event handlers."""
    if is_event_loop_closed():
        logger.warning("⚠️ Skipping event handler - event loop is closed")
        return

    if shutdown_event.is_set():
        logger.warning("⚠️ Skipping event handler - shutdown in progress")
        return

    try:
        await handler_func()
    except asyncio.CancelledError:
        logger.info("📋 Event handler cancelled during shutdown")
        raise
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            logger.warning("⚠️ Event handler attempted to run on closed loop")
        else:
            logger.error(f"❌ RuntimeError in event handler: {e}")
    except Exception as e:
        logger.error(f"❌ Error in event handler: {e}")


async def bot(runner_args: RunnerArguments):
    """Main bot execution function."""
    logger.info("🤖 Bot function called - starting initialization")

    room_url = getattr(runner_args, "room_url", None)
    token = getattr(runner_args, "token", None)
    logger.info(f"📍 Room URL: {room_url}")
    logger.info(f"🔑 Token: {'***' if token else 'None'}")

    global transport
    transport = DailyTransport(
        room_url=str(room_url or ""),
        token=token,
        bot_name="AI Copilot",
        params=DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            video_out_enabled=False,
            vad_analyzer=SileroVADAnalyzer(),
            transcription_enabled=True,
        ),
    )
    tts = CartesiaTTSService(
        api_key=os.environ["CARTESIA_API_KEY"],
        voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22",  # Friendly female voice
    )

    llm = GoogleLLMService(api_key=os.environ["GOOGLE_API_KEY"])

    # Combine tools from all MCP clients
    all_tools = []
    for client_name, mcp_client in mcp_clients:
        try:
            logger.info(f"🔗 Registering {client_name} tools with LLM...")
            tools = await mcp_client.register_tools(llm)
            tool_count = len(tools.standard_tools)
            tool_names = [tool.name for tool in tools.standard_tools]
            all_tools.extend(tools.standard_tools)
            logger.info(f"✅ Successfully registered {tool_count} tools from {client_name}")
            logger.info(f"📋 {client_name} Tools: {', '.join(tool_names)}")
        except Exception as e:
            logger.error(f"❌ Error registering {client_name} tools: {e}")

    if all_tools:
        tools = ToolsSchema(standard_tools=all_tools)
        logger.info(f"🤖 Combined {len(all_tools)} MCP tools from {len(mcp_clients)} sources")
    else:
        logger.warning("⚠️ No MCP tools available, proceeding without AI tools")
        tools = ToolsSchema(standard_tools=[])

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
    ]

    context = LLMContext(cast(List[LLMContextMessage], messages), tools)
    tool_count = len(tools.standard_tools) if hasattr(tools, 'standard_tools') else 0
    logger.info(f"🤖 LLM context created with {tool_count} MCP tools available")
    context_aggregator = LLMContextAggregatorPair(context)

    #
    # RTVI events for Pipecat client UI
    #
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    conversation_id = str(uuid.uuid4())

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
        enable_tracing=os.getenv("ENABLE_TRACING", "false").lower() == "true",
        conversation_id=conversation_id,
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        await rtvi.set_bot_ready()
        # Kick off the conversation
        await task.queue_frames([LLMRunFrame()])







    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, participant):
        if shutdown_event.is_set():
            logger.warning("⚠️ Skipping client connected handler - shutdown in progress")
            return

        if is_event_loop_closed():
            logger.warning("⚠️ Skipping client connected handler - event loop closed")
            return

        try:
            logger.info("Client connected")
            await transport.capture_participant_transcription(participant["id"])

            # Track connection event
            if langfuse:
                span = langfuse.start_span(
                    name="client_connected",
                    metadata={
                        "service": "voice_session",
                        "participant_id": participant["id"],
                        "conversation_id": conversation_id,
                    }
                )
                span.end()
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                logger.warning("⚠️ Client connected handler failed - event loop closed")
            else:
                raise
        except Exception as e:
            logger.error(f"❌ Error in client connected handler: {e}")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        if shutdown_event.is_set():
            logger.warning("⚠️ Skipping client disconnected handler - shutdown in progress")
            return

        if is_event_loop_closed():
            logger.warning("⚠️ Skipping client disconnected handler - event loop closed")
            return

        try:
            logger.info("Client disconnected")
            await task.cancel()
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                logger.warning("⚠️ Client disconnected handler failed - event loop closed")
            else:
                raise
        except Exception as e:
            logger.error(f"❌ Error in client disconnected handler: {e}")

    # Enhanced telemetry capture
    @transport.event_handler("on_transcription_message")
    async def on_transcription_message(transport, message):
        """Capture STT (speech-to-text) input for conversation analysis."""
        if shutdown_event.is_set():
            return

        if is_event_loop_closed():
            return

        try:
            if langfuse and message.get("text"):
                # Create or update a span with STT data
                span = langfuse.start_span(
                    name="speech_to_text",
                    metadata={
                        "service": "daily_transport",
                        "participant_id": message.get("participant_id"),
                        "conversation_id": conversation_id,
                        "audio_duration": message.get("duration", 0),
                        "transcription_confidence": message.get("confidence", 0),
                    }
                )
                span.update(
                    data={"stt.text": message["text"], "stt.timestamp": message.get("timestamp")}
                )
                span.end()
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                logger.warning("⚠️ Transcription handler failed - event loop closed")
            else:
                raise
        except Exception as e:
            logger.error(f"❌ Error in transcription handler: {e}")

    # LLM input/output capture
    @llm.event_handler("on_llm_start")
    async def on_llm_start(llm, messages):
        """Capture LLM input for debugging."""
        if shutdown_event.is_set():
            return

        if langfuse and messages:
            # Extract user message from context
            user_message = None
            for msg in messages:
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break

            if user_message:
                span = langfuse.start_span(
                    name="llm_input_capture",
                    metadata={
                        "service": "google_llm",
                        "conversation_id": conversation_id,
                        "message_length": len(user_message),
                    }
                )
                span.update(data={"llm.user_input": user_message})
                span.end()

    @llm.event_handler("on_llm_error")
    async def on_llm_error(llm, error):
        """Capture LLM errors for reliability monitoring."""
        if shutdown_event.is_set():
            return

        if langfuse:
            span = langfuse.start_span(
                name="llm_error",
                metadata={
                    "service": "google_llm",
                    "conversation_id": conversation_id,
                    "error_type": type(error).__name__,
                }
            )
            span.update(
                data={"error.message": str(error), "error.timestamp": str(datetime.datetime.now())}
            )
            span.end()

    # TODO: Add MCP error tracking for multiple clients
    # For now, skipping error tracking to focus on core functionality

    # Tool usage tracking
    @llm.event_handler("on_tool_call")
    async def on_tool_call(llm, tool_call):
        """Capture tool calls for observability."""
        if shutdown_event.is_set():
            return

        if langfuse:
            span = langfuse.start_span(
                name="ai_copilot_tool_call",
                metadata={
                    "service": "ai_copilot_mcp",
                    "conversation_id": conversation_id,
                    "tool_name": tool_call.get("name", "unknown"),
                    "tool_id": tool_call.get("id", "unknown"),
                }
            )
            span.update(data={"tool.arguments": str(tool_call.get("arguments", {}))})
            span.end()

    @llm.event_handler("on_tool_response")
    async def on_tool_response(llm, tool_response):
        """Capture tool responses for observability."""
        if shutdown_event.is_set():
            return

        if langfuse:
            span = langfuse.start_span(
                name="ai_copilot_tool_response",
                metadata={
                    "service": "ai_copilot_mcp",
                    "conversation_id": conversation_id,
                    "tool_name": tool_response.get("name", "unknown"),
                    "tool_id": tool_response.get("id", "unknown"),
                }
            )
            span.update(data={"tool.result": str(tool_response.get("result", ""))})
            span.end()

    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main

    # Run with the standard Pipecat runner
    # Our custom signal handlers will handle graceful shutdown
    main()
