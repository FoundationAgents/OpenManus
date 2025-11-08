# Network Toolkit Documentation

## Overview

The Network Toolkit provides comprehensive networking support for AgentFlow with HTTP/HTTPS caching, WebSocket connections, DNS/ICMP diagnostics, API integration management, rate limiting, proxy support, and Guardian-enforced security policies.

## Features

### 1. Guardian Security System

The Guardian system provides risk assessment and policy enforcement for all network operations.

**Features:**
- Risk level assessment (LOW, MEDIUM, HIGH, CRITICAL)
- Host and port blocklists/allowlists
- Operation-specific policies
- Manual approval workflow
- Logging and audit trail

**Usage:**
```python
from app.network import Guardian, NetworkPolicy, OperationType

# Create custom policy
policy = NetworkPolicy(
    name="api_policy",
    description="Policy for API access",
    allowed_operations={OperationType.HTTP_GET, OperationType.HTTP_POST},
    blocked_hosts=["malicious.com"],
    allowed_ports=[80, 443]
)

# Initialize Guardian
guardian = Guardian(policy)

# Assess risk
assessment = guardian.assess_risk(
    operation=OperationType.HTTP_GET,
    host="api.example.com",
    port=443
)

if assessment.approved:
    print(f"Request approved (Risk: {assessment.level})")
else:
    print(f"Request blocked: {', '.join(assessment.reasons)}")
```

### 2. HTTP Client with Caching

Advanced HTTP client built on httpx with response caching, retry logic, and rate limiting.

**Features:**
- Automatic response caching with configurable TTL
- LRU eviction policy
- Retry with exponential backoff
- Rate limiting per host
- Proxy support
- Guardian integration
- Cache persistence

**Usage:**
```python
from app.network import HTTPClientWithCaching, HTTPClientConfig

# Configure client
config = HTTPClientConfig(
    enable_cache=True,
    cache_default_ttl=3600,  # 1 hour
    max_retries=3,
    enable_rate_limiting=True,
    rate_limit_per_second=10.0
)

# Create client
async with HTTPClientWithCaching(config=config) as client:
    # Make GET request (cached)
    response = await client.get("https://api.example.com/data")
    print(f"Status: {response.status_code}")
    print(f"From cache: {response.from_cache}")
    print(f"Content: {response.content}")
    
    # Make POST request
    response = await client.post(
        "https://api.example.com/create",
        json={"name": "test"}
    )
    
    # Get cache statistics
    stats = client.get_cache_stats()
    print(f"Hit rate: {stats['hit_rate']}")
    print(f"Total entries: {stats['entry_count']}")
```

### 3. WebSocket Handler

Async WebSocket client with automatic reconnection, heartbeat monitoring, and message queuing.

**Features:**
- Automatic heartbeat detection
- Reconnection with exponential backoff
- Message queuing
- Event callbacks (on_message, on_connect, on_disconnect, on_error)
- Connection state monitoring
- Guardian integration

**Usage:**
```python
from app.network import WebSocketHandler, WebSocketConfig

# Configure WebSocket
config = WebSocketConfig(
    heartbeat_interval=30.0,
    max_reconnect_attempts=5
)

# Create handler
async with WebSocketHandler("wss://api.example.com/ws", config=config) as ws:
    # Register callbacks
    @ws.on_message
    async def handle_message(message):
        print(f"Received: {message.data}")
    
    @ws.on_connect
    async def handle_connect():
        print("Connected!")
    
    # Send message
    await ws.send_json({"action": "subscribe", "channel": "updates"})
    
    # Receive message with timeout
    message = await ws.receive(timeout=10.0)
    
    # Get statistics
    stats = ws.get_stats()
    print(f"Messages sent: {stats['messages_sent']}")
    print(f"Messages received: {stats['messages_received']}")
```

### 4. Network Diagnostics

DNS lookups, ICMP ping, and traceroute with safe fallbacks.

**Features:**
- DNS lookups (A, AAAA, CNAME, MX)
- ICMP ping with statistics
- Traceroute with hop information
- Reverse DNS lookup
- Guardian integration

**Usage:**
```python
from app.network import NetworkDiagnostics

diagnostics = NetworkDiagnostics()

# DNS lookup
result = await diagnostics.dns_lookup("example.com", record_type="A")
print(f"IP addresses: {result.ip_addresses}")
print(f"Resolution time: {result.resolution_time}s")

# Ping
result = await diagnostics.ping("example.com", count=4)
print(f"Packet loss: {result.packet_loss}%")
print(f"Average RTT: {result.avg_rtt}ms")

# Traceroute
result = await diagnostics.traceroute("example.com", max_hops=30)
for hop in result.hops:
    print(f"Hop {hop.hop_number}: {hop.ip_address} ({hop.rtt_ms}ms)")

# Reverse DNS
hostname = await diagnostics.resolve_reverse("8.8.8.8")
print(f"Hostname: {hostname}")
```

### 5. API Integration Manager

Centralized management of external API profiles with authentication and rate limiting.

**Features:**
- API profile management
- Multiple authentication types (API Key, Bearer Token, OAuth2, Basic)
- Per-API rate limiting
- Endpoint configuration
- Call logging and statistics
- Persistent storage
- Guardian policy enforcement

**Usage:**
```python
from app.network import APIIntegrationManager, APIAuthConfig, AuthType, HTTPMethod

# Create manager
manager = APIIntegrationManager(storage_path="config/api_profiles")

# Create API profile
auth_config = APIAuthConfig(
    auth_type=AuthType.API_KEY,
    api_key="your-api-key",
    api_key_header="X-API-Key"
)

profile = manager.create_profile(
    profile_id="github_api",
    name="GitHub API",
    base_url="https://api.github.com",
    description="GitHub REST API",
    auth_config=auth_config,
    rate_limit_per_minute=60
)

# Add endpoint
manager.add_endpoint(
    profile_id="github_api",
    endpoint_id="get_user",
    path="/users/{username}",
    methods=[HTTPMethod.GET],
    cache_ttl=300
)

# Make API call
response = await manager.call(
    profile_id="github_api",
    endpoint_id="get_user",
    method=HTTPMethod.GET
)

# Get statistics
stats = manager.get_stats(profile_id="github_api")
print(f"Total calls: {stats['total_calls']}")
print(f"Success rate: {stats['success_rate']:.2%}")
```

### 6. Rate Limiting

Token bucket and sliding window rate limiting.

**Features:**
- Token bucket algorithm
- Per-host rate limiting
- Burst allowance
- Configurable rates
- Statistics tracking

**Usage:**
```python
from app.network import RateLimiter, RateLimitConfig

# Configure rate limiter
config = RateLimitConfig(
    requests_per_second=10.0,
    burst_size=20,
    per_host=True
)

limiter = RateLimiter(config)

# Acquire permission (with waiting)
await limiter.acquire(host="api.example.com", wait=True)

# Acquire without waiting (raises exception if limit exceeded)
try:
    await limiter.acquire(host="api.example.com", wait=False)
except RateLimitExceeded:
    print("Rate limit exceeded")

# Get statistics
stats = limiter.get_stats()
print(f"Available tokens: {stats['global_tokens_available']}")
```

## MCP Tools

The Network Toolkit provides MCP-compatible tools for agent integration:

### HTTPRequestTool

Make HTTP requests with caching and Guardian validation.

```json
{
  "tool": "http_request",
  "parameters": {
    "url": "https://api.example.com/data",
    "method": "GET",
    "params": {"limit": 10},
    "headers": {"Accept": "application/json"},
    "use_cache": true
  }
}
```

### DNSLookupTool

Perform DNS lookups.

```json
{
  "tool": "dns_lookup",
  "parameters": {
    "hostname": "example.com",
    "record_type": "A"
  }
}
```

### PingTool

Ping a host.

```json
{
  "tool": "ping",
  "parameters": {
    "host": "example.com",
    "count": 4,
    "timeout": 5
  }
}
```

### TracerouteTool

Perform traceroute.

```json
{
  "tool": "traceroute",
  "parameters": {
    "host": "example.com",
    "max_hops": 30
  }
}
```

## Configuration

Add to `config/config.toml`:

```toml
[network]
# HTTP Client
enable_http_cache = true
http_cache_max_size = 1000
http_cache_max_memory_mb = 100
http_cache_default_ttl = 3600
http_cache_persist = false
http_timeout = 30.0
http_max_retries = 3
http_verify_ssl = true

# Rate Limiting
enable_rate_limiting = true
rate_limit_per_second = 10.0
rate_limit_burst = 20

# WebSocket
websocket_heartbeat_interval = 30.0
websocket_ping_interval = 20.0
websocket_max_reconnect = 5

# Diagnostics
enable_diagnostics = true
ping_count = 4
traceroute_max_hops = 30

# API Manager
api_profiles_dir = "config/api_profiles"
```

## Architecture

```
app/network/
├── __init__.py           # Public API exports
├── guardian.py           # Security and policy enforcement
├── cache.py              # Response caching
├── rate_limiter.py       # Rate limiting
├── client.py             # HTTP client with caching
├── websocket.py          # WebSocket handler
├── diagnostics.py        # DNS/ICMP diagnostics
└── api_manager.py        # API integration manager

app/tool/
└── network_tools.py      # MCP tools

tests/network/
├── test_guardian.py      # Guardian tests
├── test_cache.py         # Cache tests
├── test_rate_limiter.py  # Rate limiter tests
└── test_client.py        # HTTP client tests
```

## Security Considerations

1. **Guardian Policies**: Always configure appropriate Guardian policies for production use
2. **SSL Verification**: Keep SSL verification enabled unless absolutely necessary
3. **Rate Limiting**: Configure appropriate rate limits to avoid overwhelming external services
4. **API Keys**: Store API keys securely, never commit to version control
5. **Network Isolation**: Use Guardian to restrict access to internal networks
6. **Logging**: Enable logging for audit trails of network operations

## Performance Tips

1. **Caching**: Enable HTTP caching for frequently accessed resources
2. **TTL Configuration**: Set appropriate TTL values based on data freshness requirements
3. **Rate Limiting**: Configure per-host rate limiting for better control
4. **Connection Pooling**: httpx handles connection pooling automatically
5. **Async Operations**: Always use async/await for non-blocking I/O

## Troubleshooting

### Cache Not Working

- Check `enable_http_cache` is `true`
- Verify cache TTL settings
- Only GET requests are cached by default
- Check cache statistics with `get_cache_stats()`

### Rate Limiting Too Aggressive

- Increase `rate_limit_per_second`
- Increase `rate_limit_burst` for burst allowance
- Disable with `enable_rate_limiting = false` if not needed

### Guardian Blocking Requests

- Check risk assessment with `assess_risk()`
- Review blocked hosts and ports in policy
- Manually approve operations with `approve_operation()`
- Check if operation is in `allowed_operations`

### WebSocket Reconnection Issues

- Increase `websocket_max_reconnect`
- Adjust `websocket_heartbeat_interval`
- Check network connectivity
- Review WebSocket server logs

## Examples

See the `examples/` directory for complete examples:

- `examples/network_http_example.py` - HTTP client usage
- `examples/network_websocket_example.py` - WebSocket connections
- `examples/network_diagnostics_example.py` - DNS and ICMP tools
- `examples/network_api_manager_example.py` - API integration

## Testing

Run tests:

```bash
# All network tests
pytest tests/network/ -v

# Specific test file
pytest tests/network/test_guardian.py -v

# With coverage
pytest tests/network/ --cov=app/network --cov-report=html
```

## License

Part of AgentFlow - see LICENSE file for details.
