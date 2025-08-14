"""Tests for LLMProviderFactory."""

import pytest
from unittest.mock import Mock, patch

from app.config import LLMSettings
from app.services.llm.exceptions import ProviderNotFoundError, ProviderConfigurationError
from app.services.llm.factory import LLMProviderFactory
from app.services.llm.providers import OpenAIProvider, AzureOpenAIProvider, BedrockProvider


@pytest.fixture
def factory():
    """Provide an instance of LLMProviderFactory."""
    return LLMProviderFactory()


@pytest.fixture
def openai_config():
    """Provide a valid OpenAI configuration."""
    return LLMSettings(
        model="gpt-4",
        api_key="test-api-key",
        base_url="http://localhost:8080",
        api_version="2023-05-15",
        max_tokens=4096,
        temperature=1.0,
        api_type="openai"
    )


@pytest.fixture
def azure_config():
    """Provide a valid Azure OpenAI configuration."""
    return LLMSettings(
        model="gpt-4",
        api_key="test-api-key",
        max_tokens=4096,
        temperature=1.0,
        api_type="azure",
        base_url="https://test.openai.azure.com",
        api_version="2023-05-15"
    )


@pytest.fixture
def bedrock_config():
    """Provide a valid AWS Bedrock configuration."""
    return LLMSettings(
        model="claude-v1",
        api_key="bedrock-placeholder",
        base_url="http://localhost:8080",
        api_version="2023-05-15",
        max_tokens=4096,
        temperature=1.0,
        api_type="bedrock"
    )


class TestLLMProviderFactory:
    """Test suite for LLMProviderFactory."""

    def test_get_available_providers(self, factory):
        """Test that get_available_providers returns expected providers."""
        providers = factory.get_available_providers()
        
        assert "openai" in providers
        assert "azure" in providers
        assert "aws" in providers
        assert "bedrock" in providers
        assert providers["openai"] == OpenAIProvider
        assert providers["azure"] == AzureOpenAIProvider
        assert providers["bedrock"] == BedrockProvider

    @patch('app.services.llm.providers.AsyncOpenAI')
    def test_get_provider_returns_openai_provider_correctly(self, mock_async_openai, factory, openai_config):
        """Test that get_provider returns correct OpenAI provider instance."""
        provider = factory.get_provider("openai", openai_config)
        
        assert isinstance(provider, OpenAIProvider)
        assert provider.provider_name == "openai"
        assert provider.llm_model_name == "gpt-4"
        assert provider.api_key == "test-api-key"
        assert provider.max_tokens == 4096
        assert provider.temperature == 1.0
        
        # Verify the OpenAI client was created
        mock_async_openai.assert_called_once_with(
            api_key="test-api-key",
            base_url="http://localhost:8080"
        )

    @patch('app.services.llm.providers.AsyncAzureOpenAI')
    def test_get_provider_returns_azure_provider_correctly(self, mock_azure_openai, factory, azure_config):
        """Test that get_provider returns correct Azure provider instance."""
        provider = factory.get_provider("azure", azure_config)
        
        assert isinstance(provider, AzureOpenAIProvider)
        assert provider.provider_name == "azure"
        assert provider.llm_model_name == "gpt-4"
        assert provider.api_key == "test-api-key"
        assert provider.api_version == "2023-05-15"
        
        # Verify the Azure OpenAI client was created
        mock_azure_openai.assert_called_once_with(
            base_url="https://test.openai.azure.com",
            api_key="test-api-key",
            api_version="2023-05-15"
        )

    @patch('app.services.llm.providers.BedrockClient')
    def test_get_provider_returns_bedrock_provider_correctly(self, mock_bedrock_client, factory, bedrock_config):
        """Test that get_provider returns correct Bedrock provider instance."""
        provider = factory.get_provider("bedrock", bedrock_config)
        
        assert isinstance(provider, BedrockProvider)
        assert provider.provider_name == "bedrock"
        assert provider.llm_model_name == "claude-v1"
        
        # Verify the Bedrock client was created
        mock_bedrock_client.assert_called_once()

    def test_get_provider_raises_error_for_unsupported_provider(self, factory, openai_config):
        """Test that get_provider raises ProviderNotFoundError for unsupported provider."""
        # Create a new config with unsupported provider instead of modifying the fixture
        unsupported_config = LLMSettings(
            model="gpt-4",
            api_key="test-api-key",
            base_url="http://localhost:8080",
            api_version="2023-05-15",
            api_type="unsupported-provider"
        )
        
        with pytest.raises(ProviderNotFoundError) as exc_info:
            factory.get_provider("unsupported-provider", unsupported_config)
        
        assert "unsupported-provider" in str(exc_info.value)

    def test_get_provider_raises_error_for_invalid_config(self, factory):
        """Test that get_provider raises ProviderConfigurationError for invalid config."""
        invalid_config = LLMSettings(
            model="",  # Empty model name should cause error
            api_key="test-key",
            base_url="http://localhost:8080",
            api_version="2023-05-15",
            api_type="openai"
        )
        
        with pytest.raises(ProviderConfigurationError) as exc_info:
            factory.get_provider("openai", invalid_config)
        
        assert "Missing required field 'llm_model_name'" in str(exc_info.value)

    def test_azure_provider_requires_api_version(self, factory):
        """Test that Azure provider requires api_version in configuration."""
        azure_config_no_version = LLMSettings(
            model="gpt-4",
            api_key="test-api-key",
            api_type="azure",
            base_url="https://test.openai.azure.com",
            api_version=""  # Empty api_version should cause error
        )
        
        with pytest.raises(ProviderConfigurationError) as exc_info:
            factory.get_provider("azure", azure_config_no_version)
        
        assert "Azure provider requires api_version" in str(exc_info.value)

    def test_validate_provider_params_rejects_invalid_token_limits(self, factory):
        """Test that parameter validation rejects invalid token limits."""
        invalid_config = LLMSettings(
            model="gpt-4",
            api_key="test-key",
            base_url="http://localhost:8080",
            api_version="2023-05-15",
            max_tokens=-100,  # Invalid negative value
            api_type="openai"
        )
        
        with pytest.raises(ProviderConfigurationError) as exc_info:
            factory.get_provider("openai", invalid_config)
        
        assert "max_tokens must be positive" in str(exc_info.value)

    def test_validate_provider_params_rejects_invalid_temperature(self, factory):
        """Test that parameter validation rejects invalid temperature."""
        invalid_config = LLMSettings(
            model="gpt-4",
            api_key="test-key",
            base_url="http://localhost:8080",
            api_version="2023-05-15",
            temperature=3.0,  # Invalid temperature > 2.0
            api_type="openai"
        )
        
        with pytest.raises(ProviderConfigurationError) as exc_info:
            factory.get_provider("openai", invalid_config)
        
        assert "temperature must be between 0.0 and 2.0" in str(exc_info.value)

    @patch('app.services.llm.providers.AsyncOpenAI')
    def test_create_provider_from_name_and_config(self, mock_async_openai, factory):
        """Test creating provider from individual parameters."""
        provider = factory.create_provider_from_name_and_config(
            provider_name="openai",
            llm_model_name="gpt-3.5-turbo",
            api_key="test-key",
            max_tokens=2048,
            temperature=0.7
        )
        
        assert isinstance(provider, OpenAIProvider)
        assert provider.provider_name == "openai"
        assert provider.llm_model_name == "gpt-3.5-turbo"
        assert provider.api_key == "test-key"
        assert provider.max_tokens == 2048
        assert provider.temperature == 0.7

    def test_create_provider_from_name_and_config_unsupported_provider(self, factory):
        """Test creating provider with unsupported provider name."""
        with pytest.raises(ProviderNotFoundError) as exc_info:
            factory.create_provider_from_name_and_config(
                provider_name="unknown-provider",
                llm_model_name="some-model",
                api_key="test-key"
            )
        
        assert "unknown-provider" in str(exc_info.value)

    def test_register_provider(self, factory):
        """Test registering a new provider class."""
        class CustomProvider:
            pass
        
        factory.register_provider("custom", CustomProvider)
        providers = factory.get_available_providers()
        
        assert "custom" in providers
        assert providers["custom"] == CustomProvider