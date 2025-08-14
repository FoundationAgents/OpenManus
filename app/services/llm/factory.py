"""Factory for creating LLM provider instances."""

from typing import Dict, Type

from app.config import LLMSettings

from .base import LLMProvider
from .exceptions import ProviderConfigurationError, ProviderNotFoundError
from .providers import AzureOpenAIProvider, BedrockProvider, OpenAIProvider


class LLMProviderFactory:
    """Factory class for creating LLM provider instances.
    
    Supports multiple providers and handles configuration mapping
    between the legacy config format and the new provider instances.
    """

    # Registry of available providers
    _providers: Dict[str, Type[LLMProvider]] = {
        "openai": OpenAIProvider,
        "azure": AzureOpenAIProvider, 
        "aws": BedrockProvider,
        "bedrock": BedrockProvider,  # Alias for AWS
        # Future providers can be added here:
        # "anthropic": AnthropicProvider,
        # "ollama": OllamaProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[LLMProvider]) -> None:
        """Register a new provider class.
        
        Args:
            name: Provider name identifier
            provider_class: Provider class to register
        """
        cls._providers[name] = provider_class

    @classmethod
    def get_available_providers(cls) -> Dict[str, Type[LLMProvider]]:
        """Get all available provider classes.
        
        Returns:
            Dictionary mapping provider names to their classes
        """
        return cls._providers.copy()

    def get_provider(self, provider_name: str, config: LLMSettings) -> LLMProvider:
        """Create a provider instance from configuration.
        
        Args:
            provider_name: Name of the provider to create
            config: LLM configuration settings
            
        Returns:
            Configured provider instance
            
        Raises:
            ProviderNotFoundError: If provider is not supported
            ProviderConfigurationError: If configuration is invalid
        """
        # Determine provider type from config or explicit name
        api_type = getattr(config, 'api_type', None) or provider_name.lower()
        
        if api_type not in self._providers:
            raise ProviderNotFoundError(api_type)

        provider_class = self._providers[api_type]
        
        try:
            # Map legacy config to provider parameters
            provider_params = self._map_config_to_provider_params(config, api_type)
            
            # Create and return provider instance
            return provider_class(**provider_params)
            
        except Exception as e:
            raise ProviderConfigurationError(
                f"Failed to create {api_type} provider: {str(e)}",
                api_type
            )

    def _map_config_to_provider_params(self, config: LLMSettings, api_type: str) -> Dict:
        """Map legacy configuration to provider parameters.
        
        Args:
            config: Legacy LLM configuration
            api_type: API type identifier
            
        Returns:
            Dictionary of provider parameters
        """
        # Base parameters common to all providers
        base_params = {
            "provider_name": api_type,
            "llm_model_name": config.model,
            "api_key": config.api_key,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "max_input_tokens": getattr(config, 'max_input_tokens', None),
        }

        # Add base_url if provided
        if hasattr(config, 'base_url') and config.base_url:
            base_params["base_url"] = config.base_url

        # Provider-specific parameter mapping
        if api_type == "azure":
            # Azure requires api_version
            if not hasattr(config, 'api_version') or not config.api_version:
                raise ProviderConfigurationError(
                    "Azure provider requires api_version in configuration",
                    api_type
                )
            base_params["api_version"] = config.api_version

        elif api_type in ("aws", "bedrock"):
            # AWS Bedrock may have specific requirements
            # The api_key is not actually used for Bedrock (uses AWS credentials)
            base_params["api_key"] = getattr(config, 'api_key', 'bedrock-placeholder')

        # Validate required parameters
        self._validate_provider_params(base_params, api_type)
        
        return base_params

    def _validate_provider_params(self, params: Dict, api_type: str) -> None:
        """Validate provider parameters.
        
        Args:
            params: Provider parameters to validate
            api_type: API type for error context
            
        Raises:
            ProviderConfigurationError: If parameters are invalid
        """
        required_fields = ["provider_name", "llm_model_name", "api_key"]
        
        for field in required_fields:
            if not params.get(field):
                raise ProviderConfigurationError(
                    f"Missing required field '{field}' for {api_type} provider",
                    api_type
                )

        # Validate token limits
        if params.get("max_tokens") and params["max_tokens"] <= 0:
            raise ProviderConfigurationError(
                "max_tokens must be positive",
                api_type
            )

        if params.get("max_input_tokens") and params["max_input_tokens"] <= 0:
            raise ProviderConfigurationError(
                "max_input_tokens must be positive", 
                api_type
            )

        # Validate temperature range
        temperature = params.get("temperature", 1.0)
        if not (0.0 <= temperature <= 2.0):
            raise ProviderConfigurationError(
                "temperature must be between 0.0 and 2.0",
                api_type
            )

    def create_provider_from_name_and_config(
        self, 
        provider_name: str, 
        llm_model_name: str,
        api_key: str,
        **kwargs
    ) -> LLMProvider:
        """Create a provider instance from individual parameters.
        
        Args:
            provider_name: Name of the provider
            llm_model_name: Model to use
            api_key: API key for authentication
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Configured provider instance
            
        Raises:
            ProviderNotFoundError: If provider is not supported
            ProviderConfigurationError: If parameters are invalid
        """
        if provider_name not in self._providers:
            raise ProviderNotFoundError(provider_name)

        provider_class = self._providers[provider_name]
        
        # Prepare parameters
        params = {
            "provider_name": provider_name,
            "llm_model_name": llm_model_name,
            "api_key": api_key,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 1.0),
            "max_input_tokens": kwargs.get("max_input_tokens"),
            **kwargs
        }

        try:
            return provider_class(**params)
        except Exception as e:
            raise ProviderConfigurationError(
                f"Failed to create {provider_name} provider: {str(e)}",
                provider_name
            )