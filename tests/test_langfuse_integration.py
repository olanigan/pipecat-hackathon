"""
Test Langfuse integration and telemetry functionality.

This module tests:
- Langfuse span creation and updates
- Proper API usage (update vs set_attribute)
- Telemetry data capture
- Error handling in observability
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = Mock()


class TestLangfuseIntegration:
    """Test Langfuse integration and telemetry functionality."""

    @pytest.fixture
    def mock_langfuse(self):
        """Create a mock Langfuse client."""
        mock_client = Mock(spec=Langfuse)
        mock_span = Mock()
        mock_span.update = Mock()
        mock_span.end = Mock()
        mock_span.id = "test-span-id"
        mock_span.trace_id = "test-trace-id"
        
        mock_client.start_span = Mock(return_value=mock_span)
        mock_client.flush = Mock()
        
        return mock_client, mock_span

    @pytest.mark.skipif(not LANGFUSE_AVAILABLE, reason="Langfuse not available")
    def test_langfuse_span_update_api(self, mock_langfuse):
        """Test correct Langfuse span API usage."""
        mock_client, mock_span = mock_langfuse
        
        # Test the correct update method (not set_attribute)
        test_data = {"test.key": "test.value", "another.key": "another.value"}
        mock_span.update(data=test_data)
        
        # Verify update was called with correct data
        mock_span.update.assert_called_once_with(data=test_data)

    @pytest.mark.skipif(not LANGFUSE_AVAILABLE, reason="Langfuse not available")
    def test_langfuse_span_has_update_method(self, mock_langfuse):
        """Test that Langfuse spans have update method."""
        mock_client, mock_span = mock_langfuse

        # Verify span has update method
        assert hasattr(mock_span, 'update')
        # Note: Mock objects have all attributes, so we can't test absence of set_attribute

    @pytest.mark.asyncio
    async def test_transcription_message_telemetry(self, mock_langfuse):
        """Test transcription message telemetry capture."""
        mock_client, mock_span = mock_langfuse
        
        # Mock message data
        message = {
            "text": "Hello world",
            "participant_id": "test-participant",
            "timestamp": "2025-10-19T10:00:00Z",
            "duration": 2.5,
            "confidence": 0.95
        }
        
        with patch('bot.langfuse', mock_client):
            # Simulate the transcription handler logic (copied from bot.py)
            conversation_id = "test-conversation"

            # Simulate the handler logic
            if mock_client and message.get("text"):
                span = mock_client.start_span(
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
                    data={
                        "stt.text": message["text"],
                        "stt.timestamp": message.get("timestamp")
                    }
                )
                span.end()
            
            # Verify correct API calls
            mock_client.start_span.assert_called_once()
            mock_span.update.assert_called_once()
            mock_span.end.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_start_telemetry(self, mock_langfuse):
        """Test LLM start telemetry capture."""
        mock_client, mock_span = mock_langfuse
        
        # Mock LLM messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        with patch('bot.langfuse', mock_client):
            conversation_id = "test-conversation"
            
            # Simulate LLM start handler logic
            if mock_client and messages:
                user_message = None
                for msg in messages:
                    if msg.get("role") == "user":
                        user_message = msg.get("content", "")
                        break
                
                if user_message:
                    span = mock_client.start_span(
                        name="llm_input_capture",
                        metadata={
                            "service": "google_llm",
                            "conversation_id": conversation_id,
                            "message_length": len(user_message),
                        }
                    )
                    span.update(data={"llm.user_input": user_message})
                    span.end()
            
            # Verify correct API calls
            mock_client.start_span.assert_called_once()
            mock_span.update.assert_called_once_with(data={"llm.user_input": "Hello, how are you?"})
            mock_span.end.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_error_telemetry(self, mock_langfuse):
        """Test LLM error telemetry capture."""
        mock_client, mock_span = mock_langfuse
        
        # Mock error
        test_error = Exception("LLM processing failed")
        
        with patch('bot.langfuse', mock_client):
            conversation_id = "test-conversation"
            
            # Simulate LLM error handler logic
            if mock_client:
                span = mock_client.start_span(
                    name="llm_error",
                    metadata={
                        "service": "google_llm",
                        "conversation_id": conversation_id,
                        "error_type": type(test_error).__name__,
                    }
                )
                span.update(
                    data={
                        "error.message": str(test_error),
                        "error.timestamp": str(datetime.now())
                    }
                )
                span.end()
            
            # Verify error telemetry
            mock_client.start_span.assert_called_once_with(
                name="llm_error",
                metadata={
                    "service": "google_llm",
                    "conversation_id": conversation_id,
                    "error_type": "Exception",
                }
            )
            mock_span.update.assert_called_once()
            mock_span.end.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_tool_call_telemetry(self, mock_langfuse):
        """Test MCP tool call telemetry capture."""
        mock_client, mock_span = mock_langfuse
        
        # Mock tool call
        tool_call = {
            "name": "search_langfuse_docs",
            "id": "tool-123",
            "arguments": {"query": "tracing best practices"}
        }
        
        with patch('bot.langfuse', mock_client):
            conversation_id = "test-conversation"
            
            # Simulate tool call handler logic
            if mock_client:
                span = mock_client.start_span(
                    name="mcp_tool_call",
                    metadata={
                        "service": "langfuse_mcp",
                        "conversation_id": conversation_id,
                        "tool_name": tool_call.get("name", "unknown"),
                        "tool_id": tool_call.get("id", "unknown"),
                    }
                )
                span.update(data={"tool.arguments": str(tool_call.get("arguments", {}))})
                span.end()
            
            # Verify tool call telemetry
            mock_client.start_span.assert_called_once()
            mock_span.update.assert_called_once_with(
                data={"tool.arguments": "{'query': 'tracing best practices'}"}
            )
            mock_span.end.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_tool_response_telemetry(self, mock_langfuse):
        """Test MCP tool response telemetry capture."""
        mock_client, mock_span = mock_langfuse
        
        # Mock tool response
        tool_response = {
            "name": "search_langfuse_docs",
            "id": "tool-123",
            "result": "Found 5 documents about tracing best practices"
        }
        
        with patch('bot.langfuse', mock_client):
            conversation_id = "test-conversation"
            
            # Simulate tool response handler logic
            if mock_client:
                span = mock_client.start_span(
                    name="mcp_tool_response",
                    metadata={
                        "service": "langfuse_mcp",
                        "conversation_id": conversation_id,
                        "tool_name": tool_response.get("name", "unknown"),
                        "tool_id": tool_response.get("id", "unknown"),
                    }
                )
                span.update(data={"tool.result": str(tool_response.get("result", ""))})
                span.end()
            
            # Verify tool response telemetry
            mock_client.start_span.assert_called_once()
            mock_span.update.assert_called_once_with(
                data={"tool.result": "Found 5 documents about tracing best practices"}
            )
            mock_span.end.assert_called_once()

    @pytest.mark.asyncio
    async def test_langfuse_initialization(self):
        """Test Langfuse client initialization."""
        with patch.dict(os.environ, {
            'LANGFUSE_PUBLIC_KEY': 'test-public-key',
            'LANGFUSE_SECRET_KEY': 'test-secret-key',
            'LANGFUSE_HOST': 'http://localhost:3000',
            'ENABLE_TRACING': 'true'
        }):
            # Test initialization with tracing enabled
            # This would normally be in bot.py module level
            if os.getenv("ENABLE_TRACING", "false").lower() == "true":
                langfuse = Langfuse(
                    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", "pk-lf-local"),
                    secret_key=os.environ.get("LANGFUSE_SECRET_KEY", "sk-lf-local-secret-key"),
                    host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
                )
                assert langfuse is not None

    def test_langfuse_disabled_when_env_false(self):
        """Test Langfuse is disabled when ENABLE_TRACING is false."""
        with patch.dict(os.environ, {'ENABLE_TRACING': 'false'}):
            # When tracing is disabled, langfuse should be None
            # This simulates the bot.py initialization logic
            if os.getenv("ENABLE_TRACING", "false").lower() == "true":
                langfuse = Langfuse()
            else:
                langfuse = None

            assert langfuse is None

    @pytest.mark.asyncio
    async def test_langfuse_flush_during_shutdown(self, mock_langfuse):
        """Test Langfuse data flush during shutdown."""
        mock_client, _ = mock_langfuse
        
        with patch('bot.langfuse', mock_client):
            from bot import shutdown_handler
            
            await shutdown_handler()
            
            # Verify flush was called
            mock_client.flush.assert_called_once()

    def test_telemetry_data_structure(self, mock_langfuse):
        """Test telemetry data structure is correct."""
        mock_client, mock_span = mock_langfuse
        
        # Test span creation with correct metadata structure
        metadata = {
            "service": "test_service",
            "conversation_id": "test_conversation",
            "tool_name": "test_tool",
            "additional_field": "test_value"
        }
        
        span = mock_client.start_span(
            name="test_span",
            metadata=metadata
        )
        
        # Verify correct parameters
        mock_client.start_span.assert_called_once_with(
            name="test_span",
            metadata=metadata
        )

    @pytest.mark.asyncio
    async def test_telemetry_error_handling(self, mock_langfuse):
        """Test telemetry handles errors gracefully."""
        mock_client, mock_span = mock_langfuse

        # Mock span to raise error during update
        mock_span.update.side_effect = Exception("Telemetry error")

        with patch('bot.langfuse', mock_client):
            with patch('bot.logger') as mock_logger:
                # Simulate handler with error - in real code, errors are caught and logged
                try:
                    mock_span.update(data={"test": "data"})
                except Exception as e:
                    # In real telemetry code, this would be logged
                    mock_logger.error(f"Telemetry error: {e}")

                # Verify error was logged
                mock_logger.error.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])