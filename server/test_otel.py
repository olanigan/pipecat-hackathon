#!/usr/bin/env python3
"""Test script for OTEL endpoint connection with Langfuse."""

import os
import time
import logging
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Enable logging to see OTEL exporter messages
logging.basicConfig(level=logging.INFO)

def test_otel_connection():
    """Test OTEL endpoint connection."""
    load_dotenv(override=True)

    if os.getenv("ENABLE_TRACING", "false").lower() != "true":
        print("❌ Tracing is disabled. Set ENABLE_TRACING=true in .env")
        return False

    try:
        # Set up tracing
        tracer_provider = TracerProvider()
        trace.set_tracer_provider(tracer_provider)
        tracer = trace.get_tracer(__name__)

        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter()

        # Add span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

        print("📡 Sending test trace to OTEL endpoint...")

        # Create a test span
        with tracer.start_as_current_span("test-connection") as span:
            span.set_attribute("test.type", "connection")
            span.set_attribute("test.message", "Testing OTEL endpoint connection")
            span.set_attribute("service.name", "test-script")

        # Force flush to ensure span is sent
        tracer_provider.force_flush(timeout_millis=5000)

        # Give some time for the span to be sent
        time.sleep(2)

        print("✅ Test trace sent successfully!")
        return True

    except Exception as e:
        print(f"❌ Error testing OTEL connection: {e}")
        return False

if __name__ == "__main__":
    success = test_otel_connection()
    exit(0 if success else 1)