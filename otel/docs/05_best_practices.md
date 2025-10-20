# Best Practices for Langfuse Integration

## Development Workflow

### Local Development Setup
```bash
# 1. Start Langfuse stack
cd app/otel && docker-compose up -d

# 2. Verify services
docker-compose ps

# 3. Test SDK connection
cd app/server && uv run python test_langfuse.py

# 4. Start Pipecat bot
cd app/server && uv run python bot.py
```

### Environment Management
```bash
# .env structure
ENABLE_TRACING=true
LANGFUSE_PUBLIC_KEY=pk-lf-local
LANGFUSE_SECRET_KEY=sk-lf-local-secret-key
LANGFUSE_HOST=http://localhost:3000

# Production override
LANGFUSE_HOST=https://langfuse.company.com
LANGFUSE_PUBLIC_KEY=pk-lf-prod-...
LANGFUSE_SECRET_KEY=sk-lf-prod-...
```

## Authentication Best Practices

### API Key Management
```bash
# Never commit secrets
LANGFUSE_SECRET_KEY=sk-lf-...  # Use environment variables

# Use different keys for different environments
# local: pk-lf-local, sk-lf-local-secret-key
# staging: pk-lf-staging-..., sk-lf-staging-...
# prod: pk-lf-prod-..., sk-lf-prod-...
```

### SDK Initialization
```python
# Recommended initialization pattern
def init_langfuse():
    if not os.getenv("ENABLE_TRACING", "false").lower() == "true":
        return None

    try:
        return Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
        )
    except Exception as e:
        logger.warning(f"Langfuse initialization failed: {e}")
        return None

langfuse = init_langfuse()
```

## Tracing Best Practices

### Span Naming Conventions
```python
# Use consistent naming
conversation_span = langfuse.start_span(
    name="voice_conversation",
    user_id=user_id,
    metadata={"conversation_id": conversation_id}
)

# Hierarchical spans
stt_span = conversation_span.start_span("speech_to_text")
llm_span = conversation_span.start_span("llm_inference")
tts_span = conversation_span.start_span("text_to_speech")
```

### Metadata Standards
```python
# Standard attributes
span.set_attribute("service.name", "pipecat-bot")
span.set_attribute("service.version", "1.0.0")
span.set_attribute("user.id", user_id)
span.set_attribute("conversation.id", conversation_id)

# Voice-specific attributes
span.set_attribute("audio.format", "wav")
span.set_attribute("audio.sample_rate", 16000)
span.set_attribute("audio.duration_seconds", duration)
span.set_attribute("audio.channels", 1)

# LLM attributes
span.set_attribute("llm.model", "gemini-1.5-flash")
span.set_attribute("llm.provider", "google")
span.set_attribute("llm.tokens.prompt", prompt_tokens)
span.set_attribute("llm.tokens.completion", completion_tokens)
span.set_attribute("llm.temperature", 0.7)
```

### Error Handling
```python
def trace_with_error_handling(operation_name):
    span = langfuse.start_span(operation_name)
    try:
        result = perform_operation()
        span.set_attribute("status", "success")
        return result
    except Exception as e:
        span.set_attribute("status", "error")
        span.set_attribute("error.message", str(e))
        span.set_attribute("error.type", type(e).__name__)
        raise
    finally:
        span.end()
```

## Performance Optimization

### Batch Configuration
```python
# Optimize for your use case
langfuse = Langfuse(
    # ... credentials ...
    batch_size=50,           # Balance latency vs throughput
    flush_interval=10,       # Frequent flushes for real-time monitoring
    max_queue_size=5000,     # Handle traffic spikes
)
```

### Resource Management
```python
# Memory-efficient span creation
with langfuse.start_as_current_span("operation") as span:
    span.set_attribute("memory_usage_mb", get_memory_usage())
    # Span automatically ends when context exits
```

### Sampling Strategies
```python
# Sample based on user or conversation
if should_trace_user(user_id):
    span = langfuse.start_span("conversation")
    # Full tracing
else:
    # Minimal or no tracing
    pass
```

## Monitoring and Alerting

### Health Checks
```python
def check_langfuse_health():
    if not langfuse:
        return False

    try:
        # Test authentication
        auth_ok = langfuse.auth_check()

        # Test basic operation
        test_span = langfuse.start_span("health_check")
        test_span.end()
        langfuse.flush()

        return auth_ok
    except Exception as e:
        logger.error(f"Langfuse health check failed: {e}")
        return False
```

### Metrics Collection
```python
# Custom performance metrics
span.set_attribute("performance.response_time_ms", response_time)
span.set_attribute("performance.cpu_percent", cpu_usage)
span.set_attribute("performance.memory_percent", memory_usage)

# Business metrics
span.set_attribute("business.user_satisfaction", satisfaction_score)
span.set_attribute("business.conversation_length", message_count)
```

### Alerting Thresholds
```python
# Monitor key metrics
alerts = {
    "auth_failures": auth_failure_count > 5,
    "high_latency": avg_response_time > 5000,  # 5 seconds
    "queue_full": queue_size > max_queue_size * 0.9,
    "trace_drops": dropped_traces > 100,
}
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Authentication Failures
```python
# Symptom: auth_check() returns False
# Solutions:
# 1. Verify API keys in environment
# 2. Check network connectivity to Langfuse
# 3. Confirm project permissions
# 4. Check Langfuse server logs
```

#### 2. Missing Traces
```python
# Symptom: Traces not appearing in UI
# Solutions:
# 1. Verify flush() is called
# 2. Check ClickHouse connectivity
# 3. Enable debug logging
# 4. Verify span.end() is called
```

#### 3. Performance Degradation
```python
# Symptom: Application slowdown
# Solutions:
# 1. Reduce batch_size
# 2. Increase flush_interval
# 3. Implement sampling
# 4. Profile span creation overhead
```

#### 4. Memory Issues
```python
# Symptom: Memory usage increasing
# Solutions:
# 1. Monitor queue_size
# 2. Implement span limits
# 3. Force periodic flushes
# 4. Check for span leaks
```

### Debug Commands
```bash
# Enable detailed logging
import logging
logging.getLogger("langfuse").setLevel(logging.DEBUG)

# Check service status
docker-compose ps

# View recent traces
docker-compose exec clickhouse clickhouse-client \
  --query "SELECT * FROM traces ORDER BY timestamp DESC LIMIT 10;"

# Monitor network traffic
tcpdump -i lo0 port 3000  # macOS
tcpdump -i lo port 3000   # Linux
```

## Production Deployment

### Infrastructure Requirements
```
Minimum Requirements:
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB SSD
- Network: 100Mbps

Recommended:
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 100GB+ SSD
- Network: 1Gbps
```

### Security Considerations
```bash
# Use HTTPS in production
LANGFUSE_HOST=https://langfuse.company.com

# Rotate API keys regularly
# Use IAM roles if available
# Encrypt sensitive span data
# Implement audit logging
```

### Backup and Recovery
```bash
# Database backups
docker-compose exec postgres pg_dump -U postgres postgres > backup.sql

# ClickHouse backups
docker-compose exec clickhouse clickhouse-client \
  --query "BACKUP traces TO '/backup/traces_$(date +%Y%m%d_%H%M%S)'"

# Configuration backup
cp docker-compose.yml docker-compose.yml.backup
cp .env .env.backup
```

## Testing Strategies

### Unit Tests
```python
def test_langfuse_integration():
    # Mock Langfuse client
    mock_langfuse = Mock()
    mock_span = Mock()

    # Test span creation
    mock_langfuse.start_span.return_value = mock_span
    span = create_traced_operation(mock_langfuse)

    # Verify span lifecycle
    mock_langfuse.start_span.assert_called_once()
    mock_span.end.assert_called_once()
    mock_langfuse.flush.assert_called_once()
```

### Integration Tests
```python
def test_end_to_end_tracing():
    # Start with clean database
    reset_langfuse_data()

    # Perform traced operation
    result = traced_voice_conversation()

    # Verify traces exist
    traces = get_recent_traces()
    assert len(traces) > 0

    # Verify span hierarchy
    spans = get_trace_spans(traces[0].id)
    assert "speech_to_text" in [s.name for s in spans]
    assert "llm_inference" in [s.name for s in spans]
```

### Load Testing
```python
def test_tracing_under_load():
    # Simulate concurrent conversations
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(simulate_conversation) for _ in range(100)]

        # Monitor performance
        start_time = time.time()
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
        end_time = time.time()

        # Verify all traces recorded
        total_traces = count_total_traces()
        assert total_traces >= 100

        # Check performance impact
        avg_latency = (end_time - start_time) / 100
        assert avg_latency < 2.0  # seconds
```

## Future Considerations

### Scaling Strategies
- **Horizontal Scaling**: Multiple Langfuse instances
- **Data Partitioning**: Time-based or project-based partitioning
- **Caching Layer**: Redis for frequently accessed data
- **CDN Integration**: For global trace access

### Advanced Features
- **Custom Dashboards**: Voice agent specific metrics
- **Anomaly Detection**: Automatic performance issue identification
- **Cost Optimization**: Intelligent sampling and retention
- **Multi-tenant Support**: Organization-level isolation

### Compliance and Governance
- **Data Retention**: Configurable trace lifetime
- **PII Masking**: Sensitive data protection
- **Audit Trails**: Trace access logging
- **GDPR Compliance**: Data deletion and portability

---

*Following these best practices ensures reliable, performant, and maintainable Langfuse integration with Pipecat voice agents.*</content>
