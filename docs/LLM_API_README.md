# LLM API Integration (OpenAI-Compatible)

This document describes the LLM API integration module for connecting to OpenAI-compatible endpoints like vibingfox with automatic fallback, streaming support, and token tracking.

## Overview

The LLM API integration provides:

- **OpenAI-Compatible Client** (`app/llm/api_client.py`): HTTP/HTTPS client for OpenAI-compatible APIs
- **Graceful Fallback** (`app/llm/api_fallback.py`): Automatic retry with fallback endpoints
- **Context Management** (`app/llm/context_manager.py`): Smart message context handling
- **Token Tracking** (`app/llm/token_counter.py`): Usage monitoring and rate limiting
- **Health Checking** (`app/llm/health_check.py`): Endpoint availability monitoring

## Quick Start

### 1. Configuration

Configure your LLM API endpoint in `config/config.toml`:

```toml
[llm_api]
endpoint = "https://gpt4free.pro/v1/vibingfox/chat/completions"
model = "claude-sonnet-4.5"
context_window = 8000
max_tokens_per_request = 2000
temperature = 0.7
request_timeout = 120

# Optional fallback endpoints
[[llm_api.fallbacks]]
endpoint = "https://alternative-api.com/v1/chat/completions"
model = "gpt-4"
priority = 2
```

### 2. Basic Usage

```python
from app.config import config
from app.llm.api_client import OpenAICompatibleClient

# Create client from config
client = OpenAICompatibleClient(
    endpoint=config.llm_api.endpoint,
    model=config.llm_api.model,
    timeout=config.llm_api.request_timeout,
)

# Prepare messages
messages = [
    {"role": "user", "content": "What is Python?"}
]

# Stream response
async for token in await client.create_completion(
    messages=messages,
    stream=True,
    max_tokens=2000,
):
    print(token, end="", flush=True)
print()

# Check token usage
usage = client.get_token_usage()
print(f"Tokens used: {usage}")

await client.close()
```

## Components

### 1. OpenAI-Compatible Client

Located in `app/llm/api_client.py`

**Features:**
- Streaming responses with real-time token display
- Exponential backoff retry logic
- Custom system prompts
- Temperature/top_p tuning
- Token counting for budget awareness
- Health checks

**Usage:**

```python
from app.llm import OpenAICompatibleClient

client = OpenAICompatibleClient(
    endpoint="https://gpt4free.pro/v1/vibingfox/chat/completions",
    model="claude-sonnet-4.5",
    api_key=None,  # Not required for vibingfox
    timeout=120,
)

# Non-streaming
response = await client.create_completion(
    messages=[{"role": "user", "content": "Hello"}],
    stream=False,
    max_tokens=1000,
)

# Streaming
async for chunk in await client.create_completion(
    messages=[{"role": "user", "content": "Hello"}],
    stream=True,
):
    print(chunk, end="")
```

### 2. API Fallback Manager

Located in `app/llm/api_fallback.py`

**Features:**
- Automatic endpoint failover
- Exponential backoff for rate limits
- Server error detection and recovery
- Response caching (degraded mode)
- Priority-based endpoint selection

**Usage:**

```python
from app.llm import APIFallbackManager

manager = APIFallbackManager(
    primary_endpoint="https://primary.com/v1/chat/completions",
    primary_model="claude-sonnet-4.5",
    fallback_endpoints=[
        {
            "url": "https://fallback1.com/v1/chat/completions",
            "model": "gpt-4",
            "priority": 2,
        }
    ],
)

# Query with automatic fallback
response = await manager.query(
    messages=[{"role": "user", "content": "Hello"}],
    stream=False,
)

# Check endpoint status
status = manager.get_endpoint_status()
```

### 3. Context Manager

Located in `app/llm/context_manager.py`

**Features:**
- Smart message ordering (recent > important > oldest)
- Automatic context compression when approaching limits
- System message support
- Token usage monitoring
- Context status reporting

**Usage:**

```python
from app.llm import ContextManager

manager = ContextManager(
    max_tokens=8000,
    compression_threshold=0.9,  # Compress at 90% capacity
)

# Set system prompt
manager.set_system_message("You are a helpful assistant.")

# Add messages
manager.add_message("user", "What is machine learning?", importance=0.9)
manager.add_message("assistant", "Machine learning is...")

# Get formatted context
context = manager.get_context()

# Check status
status = manager.get_status()
print(f"Tokens used: {status['usage_percent']:.1f}%")
```

### 4. Token Counter

Located in `app/llm/token_counter.py`

**Features:**
- Request-level token tracking
- Rate limit monitoring
- Daily usage statistics
- Token budget management
- Usage alerts

**Usage:**

```python
from app.llm import TokenCounter, TokenBudget

# Track usage
counter = TokenCounter(request_limit=300, time_window=60)  # 300 req/min
counter.record_usage(input_tokens=100, output_tokens=50, model="gpt-4")

# Check rate limits
is_ok, msg = counter.check_rate_limit()
if not is_ok:
    print(f"Rate limited: {msg}")

# Get stats
stats = counter.get_usage_stats()
print(f"Total tokens: {stats['total_tokens']}")

# Budget management
budget = TokenBudget(daily_budget=1000000)
status = budget.use_tokens(10000)
```

### 5. Health Checker

Located in `app/llm/health_check.py`

**Features:**
- Periodic endpoint monitoring
- Response time tracking
- Status indicators (🟢 Connected, 🟡 Slow, 🔴 Disconnected)
- Auto-recovery when endpoints come back online

**Usage:**

```python
from app.llm import HealthChecker, HealthStatus

checker = HealthChecker(check_interval=300)  # Check every 5 minutes

# Register endpoints
checker.register_endpoint(
    "https://gpt4free.pro/v1/vibingfox/chat/completions",
    "claude-sonnet-4.5"
)

# Start monitoring
await checker.start_monitoring()

# Check status
overall_status = checker.get_overall_status()
emoji = checker.get_status_emoji(overall_status)
print(f"System status: {emoji} {overall_status.value}")

# Stop monitoring
await checker.stop_monitoring()
```

## Configuration Reference

### llm_api.toml

```toml
[llm_api]
# Primary endpoint
endpoint = "https://gpt4free.pro/v1/vibingfox/chat/completions"
model = "claude-sonnet-4.5"
api_key = ""  # Leave empty for free endpoints

# Context limits
context_window = 8000          # Max tokens in memory
max_tokens_per_request = 2000  # Per-request limit

# API parameters
temperature = 0.7
top_p = 0.9

# Rate limiting
max_requests_per_minute = 5
request_timeout = 120

# Health checks
enable_health_check = true
health_check_interval = 300
health_check_timeout = 10

# Retry strategy
retry_attempts = 3
retry_backoff_multiplier = 2.0

# Token tracking
enable_token_tracking = true
daily_token_budget = 1000000  # 0 = unlimited
token_warning_threshold = 0.8

# Response caching
enable_response_cache = true
cache_ttl = 3600

# Streaming
enable_streaming = true

# Fallback endpoints
[[llm_api.fallbacks]]
endpoint = "alternative_endpoint_url"
model = "alternative_model"
priority = 2
```

## Error Handling

The module includes custom exceptions for different error types:

```python
from app.llm import (
    APIClientError,        # Base exception
    APITimeoutError,       # Request timeout
    APIRateLimitError,     # 429 Too Many Requests
    APIServerError,        # 5xx Server errors
)
```

## Streaming Response Example

```python
from app.llm import OpenAICompatibleClient

client = OpenAICompatibleClient(
    endpoint="https://gpt4free.pro/v1/vibingfox/chat/completions",
    model="claude-sonnet-4.5",
)

# Stream response with real-time display
messages = [{"role": "user", "content": "Explain quantum computing"}]

token_count = 0
async for token in await client.create_completion(
    messages=messages,
    stream=True,
    max_tokens=2000,
):
    print(token, end="", flush=True)
    token_count += len(token) // 4  # Rough estimate

print(f"\n\nTokens: ~{token_count}")
```

## Complete Workflow Example

See `demo_llm_api.py` for comprehensive examples including:

1. Basic API client usage
2. Fallback mechanism
3. Context management
4. Token tracking
5. Budget management
6. Health checking
7. Complete workflow integration

Run with:
```bash
python3 demo_llm_api.py
```

## Testing

Run the test suite:

```bash
# Unit tests
python3 -m pytest tests/test_llm_api.py -v

# Integration tests
python3 -m pytest tests/test_llm_api_integration.py -v

# All tests
python3 -m pytest tests/test_llm_api*.py -v
```

## Architecture

```
app/llm/
├── __init__.py                 # Package exports
├── api_client.py               # OpenAI-compatible client
├── api_fallback.py             # Fallback mechanism
├── context_manager.py          # Message context handling
├── token_counter.py            # Token usage tracking
└── health_check.py             # Endpoint health monitoring

config/
└── llm_api.toml               # Configuration file
```

## Integration Points

The LLM API module integrates with:

- **app.config**: Configuration loading
- **app.logger**: Logging and diagnostics
- **app.schema**: Message format support
- **httpx**: HTTP/2-enabled async HTTP client
- **tenacity**: Retry logic with exponential backoff

## Rate Limiting Strategy

The module implements adaptive rate limiting:

1. **Per-endpoint**: Track requests per minute
2. **Exponential backoff**: Failed requests increase wait time
3. **Window-based**: Requests counted in rolling time window
4. **Graceful degradation**: Use cached responses if all endpoints fail

## Token Budget Alerts

The system alerts when:
- Daily usage exceeds warning threshold (default: 80%)
- Rate limit is reached
- Context window approaches capacity
- Endpoint health degrades

## Security Considerations

- API keys stored in config files (protect via .gitignore)
- Free endpoints don't require keys (vibingfox)
- HTTPS enforced for all API communication
- Request validation before sending
- Response timeout prevents hangs
- No local model loading (pure API)

## Performance Notes

- Streaming reduces latency for long responses
- Connection pooling via httpx
- Token estimation ~1 token per 4 characters
- Health checks run in background
- Response caching for fault tolerance

## Future Enhancements

- [ ] gRPC support for backend communication
- [ ] WebSocket-based real-time search
- [ ] Advanced caching with CDN integration
- [ ] Multi-modal support (images, audio)
- [ ] Federated search across multiple backends
- [ ] Custom result ranking models
- [ ] Usage analytics dashboard

## Troubleshooting

### Timeout Errors
- Increase `request_timeout` in config
- Check network connectivity
- Verify endpoint is accessible

### Rate Limit Errors
- Reduce `max_requests_per_minute`
- Add fallback endpoints
- Implement longer backoff delays

### Context Overflow
- Reduce `context_window` size
- Enable `enable_compression`
- Clear old messages more aggressively

### Health Check Failures
- Verify endpoint URL is correct
- Check network connectivity
- Disable health checks if problematic

## License

Part of the OpenManus framework. See LICENSE file for details.
