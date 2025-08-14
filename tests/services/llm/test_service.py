"""Tests for LLMService orchestration layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai.types.chat import ChatCompletionMessage

from app.config import LLMSettings
from app.services.llm.service import LLMService
from app.services.llm.factory import LLMProviderFactory
from app.services.llm.exceptions import LLMServiceError, ProviderConfigurationError
from app.schema import Message, ToolChoice


@pytest.fixture
def mock_factory():
    """Provide a mocked LLMProviderFactory."""
    return MagicMock(spec=LLMProviderFactory)


@pytest.fixture
def mock_provider():
    """Provide a mocked LLM provider."""
    provider = MagicMock()
    provider.provider_name = "openai"
    provider.llm_model_name = "gpt-4"
    provider.get_chat_completion = AsyncMock(return_value="Hello! How can I help you?")
    provider.get_chat_completion_with_tools = AsyncMock()
    provider.get_chat_completion_with_images = AsyncMock(return_value="I can see the image.")
    provider.count_tokens = MagicMock(return_value=10)
    provider.count_message_tokens = MagicMock(return_value=25)
    provider.supports_feature = MagicMock(return_value=True)
    provider.get_token_usage_summary = MagicMock(return_value={
        "total_input_tokens": 100,
        "total_completion_tokens": 50,
        "total_tokens": 150,
        "max_input_tokens": 1000
    })
    return provider


@pytest.fixture
def llm_service(mock_factory):
    """Provide an LLMService instance with mocked factory."""
    return LLMService(factory=mock_factory)


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
def mock_llm_config():
    """Provide mock LLM configuration."""
    return {
        "default": LLMSettings(
            model="gpt-4",
            api_key="test-api-key",
            base_url="http://localhost:8080",
            api_version="2023-05-15",
            max_tokens=4096,
            temperature=1.0,
            api_type="openai"
        ),
        "azure": LLMSettings(
            model="gpt-4",
            api_key="test-azure-key",
            base_url="https://test.openai.azure.com",
            max_tokens=4096,
            temperature=0.7,
            api_type="azure",
            api_version="2023-05-15"
        )
    }


class TestLLMService:
    """Test suite for LLMService orchestration."""

    def test_llm_service_initialization(self, mock_factory):
        """Test LLMService initialization."""
        service = LLMService(factory=mock_factory)
        
        assert service.factory == mock_factory
        assert service._provider_instances == {}

    @patch('app.config.config')
    def test_get_provider_creates_and_caches_instance(self, mock_config, llm_service, mock_factory, mock_provider, mock_llm_config):
        """Test that get_provider creates and caches provider instances."""
        mock_config.llm = mock_llm_config
        mock_factory.get_provider.return_value = mock_provider
        
        # First call should create the provider
        provider = llm_service.get_provider("default")
        
        assert provider == mock_provider
        assert "default" in llm_service._provider_instances
        
        # Verify factory was called correctly
        mock_factory.get_provider.assert_called_once_with("default", mock_llm_config["default"])
        
        # Second call should return cached instance
        mock_factory.reset_mock()
        provider2 = llm_service.get_provider("default")
        
        assert provider2 == mock_provider
        mock_factory.get_provider.assert_not_called()  # Should not be called again

    @patch('app.config.config')
    def test_get_provider_with_custom_config(self, mock_config, llm_service, mock_factory, mock_provider):
        """Test get_provider with custom configuration."""
        custom_config = {
            "custom": LLMSettings(
                model="gpt-3.5-turbo",
                api_key="custom-key",
                base_url="http://localhost:8080",
                api_version="2023-05-15",
                api_type="openai"
            )
        }
        
        mock_factory.get_provider.return_value = mock_provider
        
        provider = llm_service.get_provider("custom", custom_config)
        
        assert provider == mock_provider
        mock_factory.get_provider.assert_called_once_with("custom", custom_config["custom"])

    @patch('app.config.config')
    def test_get_provider_nonexistent_config(self, mock_config, llm_service, mock_llm_config):
        """Test get_provider with nonexistent configuration."""
        # Mock config that doesn't have nonexistent key and no default
        mock_config.llm = {"other": mock_llm_config["default"]}
        
        with pytest.raises(ProviderConfigurationError) as exc_info:
            llm_service.get_provider("nonexistent")
        
        assert "No configuration found for 'nonexistent'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ask_success(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test successful ask method."""
        mock_factory.get_provider.return_value = mock_provider
        
        response = await llm_service.ask(
            messages=sample_messages,
            stream=True,
            temperature=0.8,
            config_name="default"
        )
        
        assert response == "Hello! How can I help you?"
        
        # Verify provider method was called correctly
        mock_provider.get_chat_completion.assert_called_once_with(
            messages=sample_messages,
            stream=True,
            temperature=0.8
        )

    @pytest.mark.asyncio
    async def test_ask_with_system_messages(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test ask method with system messages."""
        mock_factory.get_provider.return_value = mock_provider
        
        system_msgs = [{"role": "system", "content": "Custom system message."}]
        
        response = await llm_service.ask(
            messages=sample_messages,
            system_msgs=system_msgs,
            config_name="default"
        )
        
        assert response == "Hello! How can I help you?"
        
        # Verify system messages were prepended
        call_args = mock_provider.get_chat_completion.call_args[1]
        expected_messages = system_msgs + sample_messages
        assert call_args["messages"] == expected_messages

    @pytest.mark.asyncio
    async def test_ask_with_message_objects(self, llm_service, mock_factory, mock_provider, sample_message_objects):
        """Test ask method with Message objects."""
        mock_factory.get_provider.return_value = mock_provider
        
        response = await llm_service.ask(
            messages=sample_message_objects,
            config_name="default"
        )
        
        assert response == "Hello! How can I help you?"
        
        # Verify provider was called with the messages
        call_args = mock_provider.get_chat_completion.call_args[1]
        assert call_args["messages"] == sample_message_objects

    @pytest.mark.asyncio
    async def test_ask_error_handling(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test ask method error handling."""
        mock_factory.get_provider.return_value = mock_provider
        mock_provider.get_chat_completion.side_effect = Exception("Unexpected error")
        
        with pytest.raises(LLMServiceError) as exc_info:
            await llm_service.ask(messages=sample_messages)
        
        assert "Unexpected error in ask" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ask_with_images_success(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test successful ask_with_images method."""
        mock_factory.get_provider.return_value = mock_provider
        
        images = ["https://example.com/image.jpg", {"url": "https://example.com/image2.jpg"}]
        
        response = await llm_service.ask_with_images(
            messages=sample_messages,
            images=images,
            stream=False,
            temperature=0.5,
            config_name="default"
        )
        
        assert response == "I can see the image."
        
        # Verify provider method was called correctly
        mock_provider.get_chat_completion_with_images.assert_called_once_with(
            messages=sample_messages,
            images=images,
            stream=False,
            temperature=0.5
        )

    @pytest.mark.asyncio
    async def test_ask_with_images_with_system_messages(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test ask_with_images with system messages."""
        mock_factory.get_provider.return_value = mock_provider
        
        system_msgs = [{"role": "system", "content": "Analyze this image."}]
        images = ["https://example.com/image.jpg"]
        
        response = await llm_service.ask_with_images(
            messages=sample_messages,
            images=images,
            system_msgs=system_msgs
        )
        
        assert response == "I can see the image."
        
        # Verify system messages were prepended
        call_args = mock_provider.get_chat_completion_with_images.call_args[1]
        expected_messages = system_msgs + sample_messages
        assert call_args["messages"] == expected_messages

    @pytest.mark.asyncio
    async def test_ask_tool_success(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test successful ask_tool method."""
        mock_factory.get_provider.return_value = mock_provider
        
        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        mock_completion_message = ChatCompletionMessage(
            role="assistant",
            content="I'll use the tool.",
            tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "test_tool", "arguments": "{}"}}]
        )
        mock_provider.get_chat_completion_with_tools.return_value = mock_completion_message
        
        response = await llm_service.ask_tool(
            messages=sample_messages,
            tools=tools,
            tool_choice=ToolChoice.AUTO,
            timeout=60,
            temperature=0.3,
            config_name="default"
        )
        
        assert response == mock_completion_message
        
        # Verify provider method was called correctly
        mock_provider.get_chat_completion_with_tools.assert_called_once_with(
            messages=sample_messages,
            tools=tools,
            tool_choice=ToolChoice.AUTO,
            timeout=60,
            temperature=0.3
        )

    @pytest.mark.asyncio
    async def test_ask_tool_with_system_messages(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test ask_tool with system messages."""
        mock_factory.get_provider.return_value = mock_provider
        
        system_msgs = [{"role": "system", "content": "Use tools when appropriate."}]
        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        
        await llm_service.ask_tool(
            messages=sample_messages,
            system_msgs=system_msgs,
            tools=tools
        )
        
        # Verify system messages were prepended
        call_args = mock_provider.get_chat_completion_with_tools.call_args[1]
        expected_messages = system_msgs + sample_messages
        assert call_args["messages"] == expected_messages

    @pytest.mark.asyncio
    async def test_ask_tool_with_none_tools(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test ask_tool with None tools (should default to empty list)."""
        mock_factory.get_provider.return_value = mock_provider
        
        await llm_service.ask_tool(messages=sample_messages, tools=None)
        
        # Verify tools were set to empty list
        call_args = mock_provider.get_chat_completion_with_tools.call_args[1]
        assert call_args["tools"] == []

    def test_count_tokens(self, llm_service, mock_factory, mock_provider):
        """Test count_tokens method."""
        mock_factory.get_provider.return_value = mock_provider
        
        result = llm_service.count_tokens("Hello, world!", "default")
        
        assert result == 10
        mock_provider.count_tokens.assert_called_once_with("Hello, world!")

    def test_count_tokens_fallback_on_error(self, llm_service, mock_factory, mock_provider):
        """Test count_tokens fallback when provider raises error."""
        mock_factory.get_provider.return_value = mock_provider
        mock_provider.count_tokens.side_effect = Exception("Token counting failed")
        
        # Should fall back to basic estimation
        result = llm_service.count_tokens("Hello world test", "default")
        
        # Basic estimation: 3 words * 1.3 = 3.9
        assert result == pytest.approx(3.9)  # len("Hello world test".split()) * 1.3

    def test_count_message_tokens(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test count_message_tokens method."""
        mock_factory.get_provider.return_value = mock_provider
        
        result = llm_service.count_message_tokens(sample_messages, "default")
        
        assert result == 25
        mock_provider.count_message_tokens.assert_called_once_with(sample_messages)

    def test_count_message_tokens_fallback_on_error(self, llm_service, mock_factory, mock_provider):
        """Test count_message_tokens fallback when provider raises error."""
        mock_factory.get_provider.return_value = mock_provider
        mock_provider.count_message_tokens.side_effect = Exception("Message counting failed")
        
        messages = [
            {"content": "Hello world"},  # 2 words * 1.3 = 2.6
            {"content": "Test message"}  # 2 words * 1.3 = 2.6
        ]
        
        result = llm_service.count_message_tokens(messages, "default")
        
        # Should estimate: (2 + 2) * 1.3 = 5.2 -> 5 (int conversion)
        assert result == 5

    def test_get_token_usage_summary(self, llm_service, mock_factory, mock_provider):
        """Test get_token_usage_summary method."""
        mock_factory.get_provider.return_value = mock_provider
        
        result = llm_service.get_token_usage_summary("default")
        
        expected = {
            "total_input_tokens": 100,
            "total_completion_tokens": 50,
            "total_tokens": 150,
            "max_input_tokens": 1000
        }
        assert result == expected
        mock_provider.get_token_usage_summary.assert_called_once()

    def test_get_token_usage_summary_error_handling(self, llm_service, mock_factory, mock_provider):
        """Test get_token_usage_summary error handling."""
        mock_factory.get_provider.return_value = mock_provider
        mock_provider.get_token_usage_summary.side_effect = Exception("Usage summary failed")
        
        result = llm_service.get_token_usage_summary("default")
        
        assert result == {"error": "Unable to get token usage"}

    def test_supports_feature(self, llm_service, mock_factory, mock_provider):
        """Test supports_feature method."""
        mock_factory.get_provider.return_value = mock_provider
        
        result = llm_service.supports_feature("images", "default")
        
        assert result is True
        mock_provider.supports_feature.assert_called_once_with("images")

    def test_supports_feature_error_handling(self, llm_service, mock_factory, mock_provider):
        """Test supports_feature error handling."""
        mock_factory.get_provider.return_value = mock_provider
        mock_provider.supports_feature.side_effect = Exception("Feature check failed")
        
        result = llm_service.supports_feature("tools", "default")
        
        assert result is False

    def test_get_available_providers(self, llm_service, mock_factory):
        """Test get_available_providers method."""
        mock_factory.get_available_providers.return_value = {
            "openai": MagicMock(__name__="OpenAIProvider"),
            "azure": MagicMock(__name__="AzureOpenAIProvider"),
            "bedrock": MagicMock(__name__="BedrockProvider")
        }
        
        result = llm_service.get_available_providers()
        
        expected = {
            "openai": "OpenAIProvider",
            "azure": "AzureOpenAIProvider", 
            "bedrock": "BedrockProvider"
        }
        assert result == expected

    def test_clear_provider_cache(self, llm_service, mock_factory, mock_provider):
        """Test clear_provider_cache method."""
        # Add a provider to cache
        llm_service._provider_instances["default"] = mock_provider
        assert len(llm_service._provider_instances) == 1
        
        # Clear cache
        llm_service.clear_provider_cache()
        
        assert len(llm_service._provider_instances) == 0

    def test_create_default(self):
        """Test create_default class method."""
        with patch('app.services.llm.service.LLMProviderFactory') as mock_factory_class:
            # Create a real instance for this test since Pydantic validates the type
            from app.services.llm.factory import LLMProviderFactory
            factory_instance = LLMProviderFactory()
            mock_factory_class.return_value = factory_instance
            
            service = LLMService.create_default()
            
            assert isinstance(service, LLMService)
            assert service.factory == factory_instance
            mock_factory_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_llm_service_error_passthrough(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test that LLMServiceError exceptions are passed through unchanged."""
        mock_factory.get_provider.return_value = mock_provider
        original_error = LLMServiceError("Original LLM error")
        mock_provider.get_chat_completion.side_effect = original_error
        
        with pytest.raises(LLMServiceError) as exc_info:
            await llm_service.ask(messages=sample_messages)
        
        # Should be the exact same exception, not wrapped
        assert exc_info.value == original_error

    @pytest.mark.asyncio
    async def test_ask_with_images_error_handling(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test ask_with_images error handling."""
        mock_factory.get_provider.return_value = mock_provider
        mock_provider.get_chat_completion_with_images.side_effect = Exception("Image processing failed")
        
        with pytest.raises(LLMServiceError) as exc_info:
            await llm_service.ask_with_images(
                messages=sample_messages,
                images=["https://example.com/image.jpg"]
            )
        
        assert "Unexpected error in ask_with_images" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ask_tool_error_handling(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test ask_tool error handling."""
        mock_factory.get_provider.return_value = mock_provider
        mock_provider.get_chat_completion_with_tools.side_effect = Exception("Tool processing failed")
        
        with pytest.raises(LLMServiceError) as exc_info:
            await llm_service.ask_tool(
                messages=sample_messages,
                tools=[{"type": "function", "function": {"name": "test"}}]
            )
        
        assert "Unexpected error in ask_tool" in str(exc_info.value)

    def test_string_response_conversion(self, llm_service, mock_factory, mock_provider, sample_messages):
        """Test that non-string responses are converted to strings."""
        # Test with a mock object that has __str__ method
        mock_response = MagicMock()
        mock_response.__str__ = MagicMock(return_value="String representation")
        
        mock_factory.get_provider.return_value = mock_provider
        mock_provider.get_chat_completion.return_value = mock_response
        
        # Use asyncio.run to handle the async method
        import asyncio
        result = asyncio.run(llm_service.ask(messages=sample_messages))
        
        assert result == "String representation"
        mock_response.__str__.assert_called_once()