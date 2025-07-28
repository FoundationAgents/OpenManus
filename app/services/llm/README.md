# LLM Service Layer

This directory contains the refactored, modular LLM service architecture that replaces the monolithic `app/llm.py` implementation. The new design follows modern software engineering principles including Single Responsibility Principle (SRP), Dependency Injection (DI), and async-first architecture.

## Architecture Overview

The service layer is organized into focused, single-responsibility modules:

```
app/services/llm/
├── __init__.py           # Package exports  
├── README.md            # This documentation
├── base.py              # Abstract base class (LLMProvider)
├── providers.py         # Concrete provider implementations
├── factory.py           # Provider factory (LLMProviderFactory) 
├── token_service.py     # Token counting service (TokenService)
├── service.py           # Main service interface (LLMService)
└── exceptions.py        # Custom exceptions
```

## Key Components

### 1. LLMProvider (Abstract Base Class)

**File**: `base.py`

Defines the contract that all LLM providers must implement:

```python
from app.services.llm import LLMProvider

class MyCustomProvider(LLMProvider):
    async def get_chat_completion(self, messages, **kwargs):
        # Implementation
        pass
    
    async def get_chat_completion_with_tools(self, messages, tools, **kwargs):
        # Implementation  
        pass
    
    # ... other required methods
```

**Key Methods**:
- `get_chat_completion()` - Basic chat completion
- `get_chat_completion_with_tools()` - Chat with function calling
- `get_chat_completion_with_images()` - Multimodal chat
- `format_messages()` - Provider-specific message formatting
- `count_tokens()` - Token counting
- `supports_feature()` - Feature capability checking

### 2. Concrete Providers

**File**: `providers.py`

Currently implemented providers:
- `OpenAIProvider` - OpenAI API integration
- `AzureOpenAIProvider` - Azure OpenAI integration  
- `BedrockProvider` - AWS Bedrock integration (placeholder)

Each provider handles:
- API authentication and configuration
- Provider-specific request/response formatting
- Error handling and retry logic
- Feature capability reporting

### 3. LLMProviderFactory

**File**: `factory.py`

Creates provider instances from configuration:

```python
from app.services.llm import LLMProviderFactory
from app.config import config

factory = LLMProviderFactory()
provider = factory.get_provider("openai", config.llm["default"])
```

**Features**:
- Maps legacy configuration to provider parameters
- Validates provider configuration
- Supports provider registration for extensibility
- Handles provider-specific parameter mapping

### 4. TokenService

**File**: `token_service.py`

Centralized token counting and management:

```python
from app.services.llm import TokenService

token_service = TokenService()
tokens = token_service.count_text_tokens("Hello world", "gpt-4")
message_tokens = token_service.count_message_tokens(messages, "gpt-4")
```

**Features**:
- Model-specific tokenization
- Image token calculation
- Message and tool token counting
- Model capability detection (multimodal, reasoning)

### 5. LLMService (Main Interface)

**File**: `service.py`

Primary service interface with dependency injection:

```python
from app.services.llm import LLMService, LLMProviderFactory

# Create service with factory
factory = LLMProviderFactory()
service = LLMService(factory=factory)

# Use the service
response = await service.ask(messages, config_name="default")
tool_response = await service.ask_tool(messages, tools, config_name="vision")
```

**Key Methods**:
- `ask()` - Basic chat completion
- `ask_with_images()` - Multimodal chat  
- `ask_tool()` - Function calling
- `count_tokens()` - Token counting
- `supports_feature()` - Feature checking

## Usage Examples

### Basic Usage

```python
from app.services.llm import LLMService

# Create service (or inject it)
service = LLMService.create_default()

# Simple chat
response = await service.ask([
    {"role": "user", "content": "Hello, how are you?"}
])

# With system message
response = await service.ask(
    messages=[{"role": "user", "content": "What's the weather?"}],
    system_msgs=[{"role": "system", "content": "You are a helpful assistant."}],
    config_name="default",
    temperature=0.7
)
```

### Function Calling

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather information",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                }
            }
        }
    }
]

response = await service.ask_tool(
    messages=[{"role": "user", "content": "What's the weather in NYC?"}],
    tools=tools,
    tool_choice="auto"
)

if response and response.tool_calls:
    # Handle tool calls
    for tool_call in response.tool_calls:
        print(f"Tool: {tool_call.function.name}")
        print(f"Args: {tool_call.function.arguments}")
```

### Image Processing

```python
response = await service.ask_with_images(
    messages=[{"role": "user", "content": "What's in this image?"}],
    images=["https://example.com/image.jpg"],
    config_name="vision"  # Use a vision-capable model
)
```

### Custom Provider

```python
from app.services.llm import LLMProvider, LLMProviderFactory

class MyProvider(LLMProvider):
    provider_name = "my_provider"
    
    async def get_chat_completion(self, messages, **kwargs):
        # Your implementation
        return "Custom response"
    
    # Implement other required methods...

# Register and use
factory = LLMProviderFactory()
factory.register_provider("my_provider", MyProvider)

service = LLMService(factory=factory)
# Use with custom provider configuration
```

## Migration from Legacy LLM Class

The original `app/llm.py` has been converted to a backward-compatibility layer that delegates to the new service architecture. **No code changes are required** for existing usage:

```python
# This still works exactly as before
from app.llm import LLM

llm = LLM(config_name="default")
response = await llm.ask(messages)
tool_response = await llm.ask_tool(messages, tools=tools)
```

The legacy interface automatically uses the new service layer under the hood.

## Configuration

The service layer works with existing configuration formats:

```toml
# config.toml
[llm]
model = "gpt-4"
api_key = "your-key"
base_url = "https://api.openai.com/v1/"
api_type = "openai"
max_tokens = 4096
temperature = 0.7

[llm.vision]
model = "gpt-4-vision-preview"
# ... other vision-specific settings
```

## Error Handling

The service layer provides structured error handling:

```python
from app.services.llm.exceptions import (
    TokenLimitExceededError,
    ProviderNotFoundError,
    ProviderAuthenticationError
)

try:
    response = await service.ask(messages)
except TokenLimitExceededError as e:
    print(f"Token limit exceeded: {e.current_tokens}/{e.max_tokens}")
except ProviderAuthenticationError as e:
    print(f"Auth failed for {e.provider}: {e}")
except ProviderNotFoundError as e:
    print(f"Provider not found: {e.provider}")
```

## Benefits of the New Architecture

1. **Single Responsibility**: Each class has one clear purpose
2. **Dependency Injection**: Improved testability and modularity
3. **Async-First**: Built for modern async/await patterns
4. **Extensibility**: Easy to add new providers and features
5. **Error Handling**: Structured, provider-aware exceptions
6. **Type Safety**: Full type annotations throughout
7. **Backward Compatibility**: Existing code continues to work
8. **Performance**: Reduced memory footprint and better caching

## Testing

The modular architecture makes testing much easier:

```python
# Mock factory for testing
class MockFactory(LLMProviderFactory):
    def get_provider(self, name, config):
        return MockProvider()

# Test with dependency injection
service = LLMService(factory=MockFactory())
```

## Future Extensions

The architecture is designed for future enhancements:

- **Anthropic Provider**: Add `AnthropicProvider` class
- **Ollama Provider**: Add local model support
- **Caching Layer**: Add response caching
- **Rate Limiting**: Add per-provider rate limiting
- **Metrics**: Add detailed usage metrics
- **Streaming**: Enhanced streaming support
- **Tool Registry**: Dynamic tool registration

## Performance Considerations

- **Provider Caching**: Providers are cached per configuration
- **Token Service**: Tokenizers are cached per model
- **Connection Reuse**: HTTP connections are reused within providers
- **Memory Efficiency**: Only active providers are kept in memory

This modular architecture provides a solid foundation for building scalable, maintainable LLM integrations while preserving full backward compatibility with the existing codebase.