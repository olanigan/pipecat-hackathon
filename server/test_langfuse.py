#!/usr/bin/env python3
"""Test script for Langfuse SDK connection."""

import os
import logging
from dotenv import load_dotenv
from langfuse import Langfuse

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("langfuse").setLevel(logging.DEBUG)

def test_langfuse_connection():
    """Test Langfuse SDK connection."""
    load_dotenv(override=True)

    if os.getenv("ENABLE_TRACING", "false").lower() != "true":
        print("❌ Tracing is disabled. Set ENABLE_TRACING=true in .env")
        return False

    try:
        # Initialize Langfuse client
        langfuse = Langfuse(
            public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", "pk-lf-local"),
            secret_key=os.environ.get("LANGFUSE_SECRET_KEY", "sk-lf-local-secret-key"),
            host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
        )

        # Try to get project ID
        try:
            project_id = langfuse._get_project_id()
            print(f"🔧 Retrieved Project ID: {project_id}")
        except Exception as e:
            print(f"🔧 Project ID retrieval failed: {e}")

        print("📡 Testing Langfuse SDK connection...")
        print(f"🔧 Client initialized: {langfuse._tracing_enabled}")

        # Test auth
        auth_check = langfuse.auth_check()
        print(f"🔐 Auth check: {auth_check}")
        print(f"🔧 Host: {langfuse._host}")
        print(f"🔧 Project ID: {langfuse._project_id}")

        # Create a test span (this creates a trace automatically)
        span = langfuse.start_span(
            name="test-connection",
            metadata={"test.type": "connection", "test.message": "Testing Langfuse SDK connection", "user_id": "test-user"}
        )

        # Create a child span
        child_span = span.start_span(
            name="test-span",
            metadata={"service.name": "test-script"}
        )

        # End the child span
        child_span.end()

        # End the main span
        span.end()

        print(f"🔍 Span created with ID: {span.id}")

        # Flush to ensure data is sent
        print("🔄 Flushing data...")
        result = langfuse.flush()
        print(f"🔄 Flush result: {result}")

        # Wait a bit for async processing
        import time
        time.sleep(5)

        print("✅ Test completed!")
        print(f"🔗 View traces at: http://localhost:3000")
        return True

    except Exception as e:
        print(f"❌ Error testing Langfuse connection: {e}")
        return False

if __name__ == "__main__":
    success = test_langfuse_connection()
    exit(0 if success else 1)
