# Modern Web Search Protocol & RAG Helper

This implementation replaces the legacy web search system with modern HTTP/2-enabled backends and LLM-based semantic refinement.

## Features

### Modern Search Backends
- **SerpAPI**: Google search results with rich snippets and knowledge graph
- **Brave Search API**: Privacy-focused search with mixed results (news, videos)
- **DuckDuckGo**: Instant answers and HTML parsing fallback
- **Google Custom Search**: Enterprise search with structured data support

### HTTP/2 & Modern Protocols
- HTTP/2 multiplexing for faster parallel requests
- Connection pooling and keep-alive
- Request/response compression (gzip, br)
- User-Agent rotation for reliability
- Configurable timeouts and retry logic

### Structured Results Parsing
- JSON-LD structured data extraction
- Microdata parsing
- Rich snippet detection
- Knowledge graph integration
- Publication metadata extraction

### LLM-Based RAG Helper
- **No embeddings required** - pure LLM reasoning
- Query reformulation and disambiguation
- Iterative refinement (up to 3 iterations)
- Semantic result ranking
- Reasoning traces for transparency
- SQLite caching (not vector store)

### Guardian Integration
- All search operations logged and audited
- Risk assessment before execution
- Domain whitelist/blacklist support
- Agent-based rate limiting

## Configuration

### TOML Configuration

```toml
[search]
# Backend selection
search_backend = "serpapi"  # serpapi, brave, duckduckgo, google

# RAG settings
search_rag_enabled = true
rag_max_iterations = 3
rag_context_window = 4000
rag_similarity_threshold = 0.7
rag_enable_reasoning_trace = true

# HTTP/2 settings
enable_http2 = true
enable_connection_pooling = true
max_connections_per_backend = 10
enable_request_compression = true
enable_response_compression = true

# Structured results
enable_structured_results = true
enable_query_expansion = true
enable_query_disambiguation = true

# API Keys
serpapi_key = "your_serpapi_key"
brave_api_key = "your_brave_api_key"
google_api_key = "your_google_api_key"
google_search_engine_id = "your_search_engine_id"
```

### Environment Variables

```bash
export SERPAPI_KEY="your_serpapi_key"
export BRAVE_API_KEY="your_brave_api_key"
export GOOGLE_API_KEY="your_google_api_key"
export GOOGLE_SEARCH_ENGINE_ID="your_search_engine_id"
```

## Usage

### Basic Search

```python
from app.tool.modern_web_search import ModernWebSearch

search = ModernWebSearch()
response = await search.execute(
    query="Python async programming",
    num_results=10,
    backend="serpapi",
    enable_rag=True
)

print(f"Found {len(response.results)} results")
for result in response.results:
    print(f"- {result.title}")
    print(f"  {result.url}")
    print(f"  RAG: {result.rag_reasoning}")
```

### Legacy Compatibility

```python
from app.tool.web_search import WebSearch

# Uses modern backend under the hood
search = WebSearch()
response = await search.execute(
    query="Python async programming",
    num_results=5,
    fetch_content=True
)

# Returns legacy format but with modern results
print(response.output)
```

### Advanced Features

```python
# Disable RAG for faster results
response = await search.execute(
    query="quick lookup",
    enable_rag=False
)

# Use specific backend
response = await search.execute(
    query="privacy search",
    backend="duckduckgo"
)

# Fetch full content
response = await search.execute(
    query="detailed analysis",
    fetch_content=True,
    num_results=3
)
```

## RAG Helper Workflow

1. **Initial Search**: Execute query with selected backend
2. **Result Analysis**: LLM analyzes result relevance and gaps
3. **Query Reformulation**: Improve query based on insights
4. **Iterative Refinement**: Repeat until satisfactory results
5. **Semantic Ranking**: Rank results by relevance to intent
6. **Cache Results**: Store in SQLite for future queries

### Query Reformulation

- Add technical terms and specificity
- Disambiguate ambiguous queries
- Include context from previous results
- Expand with related concepts

### Result Ranking

- Semantic relevance scoring (0.0-1.0)
- Key insights extraction
- Relevance reasoning
- Type-aware ranking (web, news, images, etc.)

## Performance Optimizations

### HTTP/2 Benefits
- **Multiplexing**: Multiple requests over single connection
- **Header Compression**: Reduced overhead
- **Server Push**: Proactive content delivery
- **Binary Protocol**: More efficient parsing

### Caching Strategy
- **SQLite Cache**: Query→results mapping
- **TTL-based Expiration**: Configurable cache lifetime
- **Access Tracking**: Popular queries stay cached
- **Automatic Cleanup**: Remove expired entries

### Connection Pooling
- **Keep-Alive**: Reuse connections
- **Limits**: Prevent resource exhaustion
- **Timeouts**: Handle unresponsive backends
- **Retry Logic**: Exponential backoff

## Security & Privacy

### Guardian Integration
- **Risk Assessment**: Pre-execution validation
- **Audit Trail**: Complete operation logging
- **Domain Controls**: Whitelist/blacklist enforcement
- **Agent Limits**: Per-agent rate limiting

### Privacy Features
- **User-Agent Rotation**: Avoid fingerprinting
- **No Tracking**: DuckDuckGo integration
- **Local Caching**: Reduce external requests
- **Configurable Backends**: Choose privacy-focused options

## Monitoring & Debugging

### Reasoning Traces
```python
# Enable detailed reasoning traces
response = await search.execute(
    query="complex query",
    enable_rag=True
)

for step in response.reasoning_trace:
    print(f"Step: {step}")
```

### Performance Metrics
```python
metadata = response.metadata
print(f"Search time: {metadata.search_time_seconds:.2f}s")
print(f"Query reformulations: {metadata.query_reformulations}")
print(f"RAG iterations: {metadata.rag_iterations}")
print(f"Cache hits: {metadata.cache_hits}")
print(f"HTTP/2 enabled: {metadata.http2_enabled}")
```

### Error Handling
```python
if response.error:
    print(f"Search failed: {response.error}")
    
    # Check Guardian blocking
    if "Guardian" in response.error:
        print("Search blocked by security policy")
```

## Testing

```bash
# Run all tests
python -m pytest tests/test_modern_web_search.py -v

# Run specific test class
python -m pytest tests/test_modern_web_search.py::TestModernSearchBackends -v

# Run smoke test
python tests/test_modern_web_search.py
```

## Migration Guide

### From Legacy Web Search
1. Update configuration to include API keys
2. Set `search_backend` to preferred backend
3. Enable `search_rag_enabled` for semantic refinement
4. Existing code works without changes (backward compatible)

### API Key Setup
1. **SerpAPI**: Get key from https://serpapi.com/
2. **Brave**: Get key from https://brave.com/search/api/
3. **Google**: Set up Custom Search Engine at https://cse.google.com/

### Performance Tuning
1. Enable HTTP/2: `enable_http2 = true`
2. Adjust connection pool: `max_connections_per_backend = 20`
3. Configure cache TTL: `search_cache_ttl = 7200`
4. Tune RAG iterations: `rag_max_iterations = 2`

## Troubleshooting

### Common Issues

**No search results**
- Check API keys are valid
- Verify backend is enabled in config
- Check network connectivity

**RAG not working**
- Ensure `search_rag_enabled = true`
- Check LLM configuration
- Verify context window size

**HTTP/2 not working**
- Backend may not support HTTP/2
- Check proxy configuration
- Verify SSL certificates

**Cache not working**
- Ensure `data/` directory exists
- Check SQLite permissions
- Verify cache TTL settings

### Debug Mode
```python
import logging
logging.getLogger('app.tool.modern_web_search').setLevel(logging.DEBUG)
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Legacy API    │    │  Modern Web     │    │   RAG Helper    │
│   WebSearch     │───▶│   Search         │───▶│   Agent          │
│                 │    │                 │    │                 │
│ Backward        │    │ HTTP/2          │    │ Query Reform.   │
│ Compatible      │    │ Structured       │    │ Result Ranking   │
│                 │    │ Results         │    │ Reasoning       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Search        │
                       │   Backends      │
                       │                 │
                       │ ┌─────────────┐ │
                       │ │   SerpAPI   │ │
                       │ │   Brave     │ │
                       │ │ DuckDuckGo  │ │
                       │ │   Google    │ │
                       │ └─────────────┘ │
                       └──────────────────┘
```

## Future Enhancements

- gRPC support for backend communication
- Streaming result delivery
- WebSocket-based real-time search
- Advanced caching with CDN integration
- Multi-modal search (images, videos, audio)
- Federated search across multiple backends
- Custom result ranking models
- Search analytics and usage tracking