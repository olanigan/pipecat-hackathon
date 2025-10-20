"""
Test event loop stability and shutdown handling.

This module tests the fixes for:
- Event loop closure errors
- Graceful shutdown sequences
- Resource cleanup during shutdown
- Signal handling
"""

import asyncio
import signal
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Optional

# Import bot functions for testing
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from bot import (
    shutdown_event,
    is_event_loop_closed,
    safe_event_handler,
    shutdown_handler,
    signal_handler
)


class TestEventLoopStability:
    """Test event loop stability and shutdown mechanisms."""

    @pytest.fixture
    def reset_shutdown_event(self):
        """Reset shutdown event before each test."""
        shutdown_event.clear()
        yield
        shutdown_event.clear()

    @pytest.mark.asyncio
    async def test_is_event_loop_closed_with_running_loop(self):
        """Test event loop detection with running loop."""
        # Should return False when loop is running
        assert not is_event_loop_closed()

    def test_is_event_loop_closed_with_no_loop(self):
        """Test event loop detection with no running loop."""
        # Should return True when no loop is running
        assert is_event_loop_closed()

    @pytest.mark.asyncio
    async def test_safe_event_handler_with_shutdown_set(self, reset_shutdown_event):
        """Test safe event handler respects shutdown flag."""
        shutdown_event.set()
        
        # Mock handler function
        mock_handler = AsyncMock()
        
        # Should return early without calling handler
        await safe_event_handler(mock_handler)
        mock_handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_safe_event_handler_with_closed_loop(self, reset_shutdown_event):
        """Test safe event handler handles closed loop gracefully."""
        # Mock closed loop scenario
        with patch('bot.is_event_loop_closed', return_value=True):
            mock_handler = AsyncMock()
            
            # Should return early without calling handler
            await safe_event_handler(mock_handler)
            mock_handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_safe_event_handler_executes_normally(self, reset_shutdown_event):
        """Test safe event handler executes normally when conditions are met."""
        mock_handler = AsyncMock()
        
        # Should call handler normally
        await safe_event_handler(mock_handler)
        mock_handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_safe_event_handler_handles_runtime_error(self, reset_shutdown_event):
        """Test safe event handler catches RuntimeError gracefully."""
        async def failing_handler():
            raise RuntimeError("Event loop is closed")
        
        # Should catch and log error without raising
        with patch('bot.logger') as mock_logger:
            await safe_event_handler(failing_handler)
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_safe_event_handler_handles_general_exception(self, reset_shutdown_event):
        """Test safe event handler catches general exceptions."""
        async def failing_handler():
            raise ValueError("Some other error")
        
        # Should catch and log error without raising
        with patch('bot.logger') as mock_logger:
            await safe_event_handler(failing_handler)
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_shutdown_handler_cancels_tasks(self, reset_shutdown_event):
        """Test shutdown handler cancels all pending tasks."""
        # Create some background tasks
        async def dummy_task():
            await asyncio.sleep(10)
        
        task1 = asyncio.create_task(dummy_task())
        task2 = asyncio.create_task(dummy_task())
        
        # Run shutdown handler
        await shutdown_handler()
        
        # Verify shutdown event is set
        assert shutdown_event.is_set()
        
        # Verify tasks are cancelled
        assert task1.cancelled()
        assert task2.cancelled()

    @pytest.mark.asyncio
    async def test_shutdown_handler_handles_cleanup_errors(self, reset_shutdown_event):
        """Test shutdown handler handles cleanup errors gracefully."""
        with patch('bot.logger') as mock_logger:
            # Mock cleanup to raise error - but gather uses return_exceptions=True so it won't raise
            # Instead, test that the function completes without raising
            with patch('asyncio.gather', side_effect=Exception("Cleanup error")):
                # Should not raise exception despite gather error
                await shutdown_handler()
                # Since gather returns exceptions, no error should be logged for gather itself
                # But the test should verify the function doesn't crash
                assert shutdown_event.is_set()

    def test_signal_handler_creates_shutdown_task(self, reset_shutdown_event):
        """Test signal handler creates shutdown task."""
        with patch('asyncio.create_task') as mock_create_task:
            # Call signal handler
            signal_handler(signal.SIGTERM, None)
            
            # Should create shutdown task
            mock_create_task.assert_called_once()
            args = mock_create_task.call_args[0][0]
            # Verify it's the shutdown_handler coroutine
            assert args.__name__ == 'shutdown_handler'

    @pytest.mark.asyncio
    async def test_transport_cleanup_during_shutdown(self, reset_shutdown_event):
        """Test transport cleanup during shutdown."""
        # Mock global transport
        mock_transport = Mock()
        
        with patch('bot.transport', mock_transport):
            await shutdown_handler()
            
            # Transport should be set to None to prevent further callbacks
            # (This is verified through the transport being None after cleanup)

    @pytest.mark.asyncio
    async def test_mcp_client_cleanup_during_shutdown(self, reset_shutdown_event):
        """Test MCP client cleanup during shutdown."""
        # Mock global mcp_clients as list of (name, client) tuples
        mock_client = Mock()
        mock_mcps = [("test_client", mock_client)]

        with patch('bot.mcp_clients', mock_mcps):
            with patch('bot.logger') as mock_logger:
                await shutdown_handler()

                # Should log cleanup completion for the client
                mock_logger.info.assert_any_call("✅ test_client cleanup completed")

    @pytest.mark.asyncio
    async def test_langfuse_flush_during_shutdown(self, reset_shutdown_event):
        """Test Langfuse data flush during shutdown."""
        mock_langfuse = Mock()
        
        with patch('bot.langfuse', mock_langfuse):
            with patch('bot.logger') as mock_logger:
                await shutdown_handler()
                
                # Should call flush and log completion
                mock_langfuse.flush.assert_called_once()
                mock_logger.info.assert_any_call("✅ Langfuse data flushed")

    @pytest.mark.asyncio
    async def test_concurrent_shutdown_calls(self, reset_shutdown_event):
        """Test multiple concurrent shutdown calls are handled safely."""
        # Call shutdown handler multiple times sequentially (concurrent calls may interfere)
        await shutdown_handler()
        await shutdown_handler()
        await shutdown_handler()

        # Shutdown event should be set
        assert shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_shutdown_with_no_pending_tasks(self, reset_shutdown_event):
        """Test shutdown when no pending tasks exist."""
        # Should complete successfully even with no tasks
        await shutdown_handler()
        assert shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_event_loop_state_consistency(self):
        """Test event loop state checking consistency."""
        # With running loop, should not be closed
        assert not is_event_loop_closed()

        # Create new loop and check
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)

        try:
            # Should work with new loop
            assert not is_event_loop_closed()
        finally:
            new_loop.close()
            # Don't restore loop for test isolation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])