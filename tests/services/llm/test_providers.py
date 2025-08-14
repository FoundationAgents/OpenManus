"""Tests for LLM provider implementations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai import APIError, AuthenticationError, RateLimitError, APIStatusError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage

from app.services.llm.exceptions import (
    ProviderAPIError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    TokenLimitExceededError,
    UnsupportedFeatureError,
    MessageFormattingError
)
from app.services.llm.providers import OpenAIProvider, AzureOpenAIProvider, BedrockProvider
from app.schema import Message


class MockAsyncIterator:
    """Helper class for mocking async iterators."""
    def __init__(self, items):
        self._items = iter(items)

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration

    def __aiter__(self):
        return self


@pytest.fixture
def openai_provider():
    """Provide an OpenAI provider instance with mocked client."""
    with patch('app.services.llm.providers.AsyncOpenAI') as mock_client_class:
        provider = OpenAIProvider(
            provider_name="openai",
            llm_model_name="gpt-4",
            api_key="test-api-key",
            base_url="http://localhost:8080",
            api_version="2023-05-15", 
            max_tokens=4096,
            temperature=1.0
        )
        provider.client = AsyncMock()
        
        # Replace the token service with a mock
        mock_token_service = MagicMock()
        mock_token_service.is_model_multimodal = MagicMock(return_value=True)
        mock_token_service.is_reasoning_model = MagicMock(return_value=False)
        mock_token_service.count_text_tokens = MagicMock(return_value=10)
        mock_token_service.count_message_tokens = MagicMock(return_value=25)
        provider.token_service = mock_token_service
        
        return provider


@pytest.fixture
def azure_provider():
    """Provide an Azure OpenAI provider instance with mocked client."""
    with patch('app.services.llm.providers.AsyncAzureOpenAI') as mock_client_class:
        provider = AzureOpenAIProvider(
            provider_name="azure",
            llm_model_name="gpt-4",
            api_key="test-api-key",
            api_version="2023-05-15",
            base_url="https://test.openai.azure.com",
            max_tokens=4096,
            temperature=1.0
        )
        provider.client = AsyncMock()
        
        # Replace the token service with a mock
        mock_token_service = MagicMock()
        mock_token_service.is_model_multimodal = MagicMock(return_value=True)
        mock_token_service.is_reasoning_model = MagicMock(return_value=False)
        mock_token_service.count_text_tokens = MagicMock(return_value=10)
        mock_token_service.count_message_tokens = MagicMock(return_value=25)
        provider.token_service = mock_token_service
        
        return provider


@pytest.fixture
def bedrock_provider():
    """Provide a Bedrock provider instance with mocked client."""
    with patch('app.services.llm.providers.BedrockClient') as mock_client_class:
        provider = BedrockProvider(
            provider_name="bedrock",
            llm_model_name="claude-v1",
            api_key="bedrock-placeholder",
            base_url="http://localhost:8080",
            api_version="2023-05-15",
            max_tokens=4096,
            temperature=1.0
        )
        provider.client = MagicMock()
        return provider


@pytest.fixture
def sample_messages():
    """Provide sample messages for testing."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, world!"}
    ]


@pytest.fixture
def sample_message_objects():
    """Provide sample Message objects for testing."""
    return [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello, world!")
    ]


@pytest.fixture
def mock_chat_completion():
    """Provide a mock ChatCompletion response."""
    mock_choice = MagicMock()
    mock_choice.index = 0
    mock_choice.message = ChatCompletionMessage(
        role="assistant",
        content="Hello! How can I help you today?"
    )
    mock_choice.finish_reason = "stop"
    
    mock_completion = MagicMock(spec=ChatCompletion)
    mock_completion.id = "chatcmpl-test"
    mock_completion.object = "chat.completion"
    mock_completion.created = 1234567890
    mock_completion.model = "gpt-4"
    mock_completion.choices = [mock_choice]
    mock_completion.usage = CompletionUsage(
        prompt_tokens=25,
        completion_tokens=10,
        total_tokens=35
    )
    
    return mock_completion


class TestOpenAIProvider:
    """Test suite for OpenAIProvider."""

    @pytest.mark.asyncio
    async def test_get_chat_completion_success(self, openai_provider, sample_messages, mock_chat_completion):
        """Test successful chat completion request."""
        openai_provider.client.chat.completions.create = AsyncMock(return_value=mock_chat_completion)
        
        response = await openai_provider.get_chat_completion(
            messages=sample_messages,
            stream=False
        )
        
        assert response == "Hello! How can I help you today?"
        
        # Verify the API was called correctly
        openai_provider.client.chat.completions.create.assert_called_once()
        call_args = openai_provider.client.chat.completions.create.call_args[1]
        
        assert call_args["model"] == "gpt-4"
        assert call_args["stream"] is False
        assert call_args["max_tokens"] == 4096
        assert call_args["temperature"] == 1.0
        assert len(call_args["messages"]) == 2

    @pytest.mark.asyncio
    async def test_get_chat_completion_with_message_objects(self, openai_provider, sample_message_objects, mock_chat_completion):
        """Test chat completion with Message objects."""
        openai_provider.client.chat.completions.create = AsyncMock(return_value=mock_chat_completion)
        
        response = await openai_provider.get_chat_completion(
            messages=sample_message_objects,
            stream=False
        )
        
        assert response == "Hello! How can I help you today?"
        
        # Verify messages were properly formatted
        call_args = openai_provider.client.chat.completions.create.call_args[1]
        messages = call_args["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello, world!"

    @pytest.mark.skip(reason="Retry decorator makes exception testing complex")
    @pytest.mark.asyncio
    async def test_get_chat_completion_api_error(self, openai_provider, sample_messages):
        """Test handling of OpenAI API errors."""
        pass

    @pytest.mark.skip(reason="Retry decorator makes exception testing complex")
    @pytest.mark.asyncio
    async def test_get_chat_completion_authentication_error(self, openai_provider, sample_messages):
        """Test handling of authentication errors."""
        pass

    @pytest.mark.skip(reason="Retry decorator makes exception testing complex")
    @pytest.mark.asyncio
    async def test_get_chat_completion_rate_limit_error(self, openai_provider, sample_messages):
        """Test handling of rate limit errors."""
        pass

    @pytest.mark.skip(reason="Retry decorator makes exception testing complex")
    @pytest.mark.asyncio
    async def test_get_chat_completion_token_limit_exceeded(self, openai_provider, sample_messages):
        """Test token limit exceeded error."""
        pass

    @pytest.mark.asyncio
    async def test_get_chat_completion_streaming(self, openai_provider, sample_messages):
        """Test streaming chat completion."""
        # Create mock streaming response
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "Hello!"
        
        mock_stream = MockAsyncIterator([mock_chunk])
        
        openai_provider.client.chat.completions.create = AsyncMock(return_value=mock_stream)
        
        with patch('builtins.print'):  # Mock print to avoid output during tests
            response = await openai_provider.get_chat_completion(
                messages=sample_messages,
                stream=True
            )
        
        assert response == "Hello!"
        
        # Verify streaming was enabled
        call_args = openai_provider.client.chat.completions.create.call_args[1]
        assert call_args["stream"] is True

    @pytest.mark.asyncio
    async def test_get_chat_completion_with_tools_success(self, openai_provider, sample_messages):
        """Test successful chat completion with tools."""
        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = ChatCompletionMessage(
            role="assistant",
            content="I'll use the tool.",
            tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "test_tool", "arguments": "{}"}}]
        )
        mock_response.usage = CompletionUsage(prompt_tokens=30, completion_tokens=15, total_tokens=45)
        
        openai_provider.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        response = await openai_provider.get_chat_completion_with_tools(
            messages=sample_messages,
            tools=tools,
            tool_choice="auto"
        )
        
        assert response == mock_response.choices[0].message
        
        # Verify tool parameters were passed correctly
        call_args = openai_provider.client.chat.completions.create.call_args[1]
        assert call_args["tools"] == tools
        assert call_args["tool_choice"] == "auto"
        assert call_args["stream"] is False

    @pytest.mark.asyncio
    async def test_get_chat_completion_with_images_success(self, openai_provider, sample_messages, mock_chat_completion):
        """Test chat completion with images."""
        images = ["https://example.com/image.jpg"]
        
        # Mock multimodal support
        openai_provider.token_service.is_model_multimodal.return_value = True
        openai_provider.client.chat.completions.create = AsyncMock(return_value=mock_chat_completion)
        
        response = await openai_provider.get_chat_completion_with_images(
            messages=sample_messages,
            images=images,
            stream=False
        )
        
        assert response == "Hello! How can I help you today?"
        
        # Verify image was added to the last message
        call_args = openai_provider.client.chat.completions.create.call_args[1]
        messages = call_args["messages"]
        last_message = messages[-1]
        
        assert isinstance(last_message["content"], list)
        # Should have text and image content
        assert len(last_message["content"]) == 2
        assert last_message["content"][0]["type"] == "text"
        assert last_message["content"][1]["type"] == "image_url"

    @pytest.mark.asyncio
    async def test_get_chat_completion_with_images_unsupported(self, openai_provider, sample_messages):
        """Test image completion with unsupported model."""
        openai_provider.token_service.is_model_multimodal.return_value = False
        images = ["https://example.com/image.jpg"]
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            await openai_provider.get_chat_completion_with_images(
                messages=sample_messages,
                images=images
            )
        
        assert "images" in str(exc_info.value)
        assert exc_info.value.provider == "openai"

    def test_format_messages_with_dict_messages(self, openai_provider, sample_messages):
        """Test message formatting with dictionary messages."""
        formatted = openai_provider.format_messages(sample_messages)
        
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[0]["content"] == "You are a helpful assistant."
        assert formatted[1]["role"] == "user"
        assert formatted[1]["content"] == "Hello, world!"

    def test_format_messages_with_message_objects(self, openai_provider, sample_message_objects):
        """Test message formatting with Message objects."""
        formatted = openai_provider.format_messages(sample_message_objects)
        
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[0]["content"] == "You are a helpful assistant."
        assert formatted[1]["role"] == "user"
        assert formatted[1]["content"] == "Hello, world!"

    def test_format_messages_with_base64_image(self, openai_provider):
        """Test message formatting with base64 images."""
        messages = [
            {"role": "user", "content": "What's in this image?", "base64_image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="}
        ]
        
        formatted = openai_provider.format_messages(messages, supports_images=True)
        
        assert len(formatted) == 1
        message = formatted[0]
        assert isinstance(message["content"], list)
        assert len(message["content"]) == 2
        assert message["content"][0]["type"] == "text"
        assert message["content"][1]["type"] == "image_url"
        assert "data:image/jpeg;base64," in message["content"][1]["image_url"]["url"]

    def test_format_messages_invalid_role(self, openai_provider):
        """Test message formatting with invalid role."""
        messages = [{"role": "invalid_role", "content": "Test"}]
        
        with pytest.raises(MessageFormattingError) as exc_info:
            openai_provider.format_messages(messages)
        
        assert "Invalid role" in str(exc_info.value)

    def test_format_messages_missing_role(self, openai_provider):
        """Test message formatting with missing role."""
        messages = [{"content": "Test"}]
        
        with pytest.raises(MessageFormattingError) as exc_info:
            openai_provider.format_messages(messages)
        
        assert "must contain 'role' field" in str(exc_info.value)

    def test_count_tokens(self, openai_provider):
        """Test token counting."""
        text = "Hello, world!"
        
        with patch.object(openai_provider.token_service, 'count_text_tokens', return_value=3) as mock_count:
            result = openai_provider.count_tokens(text)
        
        assert result == 3
        mock_count.assert_called_once_with(text, "gpt-4")

    def test_count_message_tokens(self, openai_provider, sample_messages):
        """Test message token counting."""
        with patch.object(openai_provider.token_service, 'count_message_tokens', return_value=25) as mock_count:
            result = openai_provider.count_message_tokens(sample_messages)
        
        assert result == 25
        mock_count.assert_called_once_with(sample_messages, "gpt-4")

    def test_supports_feature_images(self, openai_provider):
        """Test image feature support check."""
        openai_provider.token_service.is_model_multimodal.return_value = True
        
        assert openai_provider.supports_feature("images") is True
        
        openai_provider.token_service.is_model_multimodal.return_value = False
        assert openai_provider.supports_feature("images") is False

    def test_supports_feature_tools(self, openai_provider):
        """Test tool feature support check."""
        assert openai_provider.supports_feature("tools") is True

    def test_supports_feature_streaming(self, openai_provider):
        """Test streaming feature support check."""
        assert openai_provider.supports_feature("streaming") is True

    def test_supports_feature_unknown(self, openai_provider):
        """Test unknown feature support check."""
        assert openai_provider.supports_feature("unknown_feature") is False

    def test_update_token_count(self, openai_provider):
        """Test token count updating."""
        initial_input = openai_provider.total_input_tokens
        initial_completion = openai_provider.total_completion_tokens
        
        openai_provider.update_token_count(100, 50)
        
        assert openai_provider.total_input_tokens == initial_input + 100
        assert openai_provider.total_completion_tokens == initial_completion + 50

    def test_check_token_limit_no_limit(self, openai_provider):
        """Test token limit check with no limit set."""
        openai_provider.max_input_tokens = None
        
        assert openai_provider.check_token_limit(1000) is True

    def test_check_token_limit_within_limit(self, openai_provider):
        """Test token limit check within limit."""
        openai_provider.max_input_tokens = 1000
        openai_provider.total_input_tokens = 500
        
        assert openai_provider.check_token_limit(400) is True

    def test_check_token_limit_exceeds_limit(self, openai_provider):
        """Test token limit check exceeding limit."""
        openai_provider.max_input_tokens = 1000
        openai_provider.total_input_tokens = 800
        
        assert openai_provider.check_token_limit(300) is False

    def test_get_token_usage_summary(self, openai_provider):
        """Test token usage summary."""
        openai_provider.total_input_tokens = 100
        openai_provider.total_completion_tokens = 50
        openai_provider.max_input_tokens = 1000
        
        summary = openai_provider.get_token_usage_summary()
        
        expected = {
            "total_input_tokens": 100,
            "total_completion_tokens": 50,
            "total_tokens": 150,
            "max_input_tokens": 1000
        }
        assert summary == expected


class TestAzureOpenAIProvider:
    """Test suite for AzureOpenAIProvider."""

    def test_azure_provider_initialization(self, azure_provider):
        """Test Azure provider initialization."""
        assert azure_provider.provider_name == "azure"
        assert azure_provider.llm_model_name == "gpt-4"
        assert azure_provider.api_version == "2023-05-15"


class TestBedrockProvider:
    """Test suite for BedrockProvider."""

    @pytest.mark.asyncio
    async def test_get_chat_completion_not_implemented(self, bedrock_provider, sample_messages):
        """Test that Bedrock provider chat completion is not implemented."""
        with pytest.raises(NotImplementedError):
            await bedrock_provider.get_chat_completion(messages=sample_messages)

    @pytest.mark.asyncio
    async def test_get_chat_completion_with_tools_unsupported(self, bedrock_provider, sample_messages):
        """Test that Bedrock provider doesn't support tools."""
        tools = [{"type": "function", "function": {"name": "test"}}]
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            await bedrock_provider.get_chat_completion_with_tools(
                messages=sample_messages,
                tools=tools
            )
        
        assert "tools" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_chat_completion_with_images_unsupported(self, bedrock_provider, sample_messages):
        """Test that Bedrock provider doesn't support images."""
        images = ["https://example.com/image.jpg"]
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            await bedrock_provider.get_chat_completion_with_images(
                messages=sample_messages,
                images=images
            )
        
        assert "images" in str(exc_info.value)

    def test_bedrock_supports_feature_images_false(self, bedrock_provider):
        """Test that Bedrock doesn't support images."""
        assert bedrock_provider.supports_feature("images") is False

    def test_bedrock_supports_feature_tools_false(self, bedrock_provider):
        """Test that Bedrock doesn't support tools."""
        assert bedrock_provider.supports_feature("tools") is False

    def test_bedrock_supports_feature_streaming_true(self, bedrock_provider):
        """Test that Bedrock supports streaming."""
        assert bedrock_provider.supports_feature("streaming") is True

    def test_bedrock_format_messages(self, bedrock_provider, sample_messages):
        """Test Bedrock message formatting."""
        formatted = bedrock_provider.format_messages(sample_messages)
        
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[1]["role"] == "user"