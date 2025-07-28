"""Main LLM service providing the primary interface for LLM operations."""

from typing import Dict, List, Optional, Union

from openai.types.chat import ChatCompletionMessage
from pydantic import BaseModel

from app.config import LLMSettings
from app.logger import logger
from app.schema import Message, TOOL_CHOICE_TYPE, ToolChoice

from .base import LLMProvider
from .exceptions import LLMServiceError, ProviderConfigurationError
from .factory import LLMProviderFactory


class LLMService(BaseModel):
    """Main LLM service interface.
    
    This service acts as the primary facade for all LLM operations,
    providing a consistent interface while delegating to appropriate providers.
    Uses dependency injection for improved testability and modularity.
    """

    factory: LLMProviderFactory
    _provider_instances: Dict[str, LLMProvider] = {}

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, factory: LLMProviderFactory, **data):
        super().__init__(factory=factory, **data)

    def get_provider(self, config_name: str = "default", llm_config: Optional[Dict[str, LLMSettings]] = None) -> LLMProvider:
        """Get or create a provider instance for the given configuration.
        
        Args:
            config_name: Configuration name to use
            llm_config: Optional LLM configuration dictionary
            
        Returns:
            Provider instance for the configuration
            
        Raises:
            ProviderConfigurationError: If configuration is invalid
        """
        # Check if we already have an instance for this config
        if config_name in self._provider_instances:
            return self._provider_instances[config_name]

        # Import config here to avoid circular imports
        from app.config import config as app_config
        
        # Get configuration
        if llm_config is None:
            llm_config = app_config.llm

        # Get specific config or fall back to default
        config = llm_config.get(config_name, llm_config.get("default"))
        if config is None:
            raise ProviderConfigurationError(f"No configuration found for '{config_name}'")

        # Create provider instance
        provider = self.factory.get_provider(config_name, config)
        
        # Cache the instance
        self._provider_instances[config_name] = provider
        
        logger.info(f"Created {provider.provider_name} provider for config '{config_name}' with model '{provider.model_name}'")
        
        return provider

    async def ask(
        self,
        messages: List[Union[Dict, Message]],
        system_msgs: Optional[List[Union[Dict, Message]]] = None,
        stream: bool = True,
        temperature: Optional[float] = None,
        config_name: str = "default",
        **kwargs
    ) -> str:
        """Send a prompt to the LLM and get the response.
        
        Args:
            messages: List of conversation messages
            system_msgs: Optional system messages to prepend
            stream: Whether to stream the response
            temperature: Sampling temperature for the response
            config_name: Configuration name to use
            **kwargs: Additional provider-specific parameters
            
        Returns:
            The generated response string
            
        Raises:
            LLMServiceError: For any LLM-related errors
        """
        try:
            provider = self.get_provider(config_name)
            
            # Combine system and user messages if system messages provided
            if system_msgs:
                all_messages = system_msgs + messages
            else:
                all_messages = messages
            
            # Get response from provider
            response = await provider.get_chat_completion(
                messages=all_messages,
                stream=stream,
                temperature=temperature,
                **kwargs
            )
            
            # Return string response (providers handle streaming vs non-streaming)
            return response if isinstance(response, str) else str(response)
            
        except Exception as e:
            logger.error(f"Error in ask method: {str(e)}")
            if isinstance(e, LLMServiceError):
                raise
            raise LLMServiceError(f"Unexpected error in ask: {str(e)}")

    async def ask_with_images(
        self,
        messages: List[Union[Dict, Message]],
        images: List[Union[str, Dict]],
        system_msgs: Optional[List[Union[Dict, Message]]] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        config_name: str = "default",
        **kwargs
    ) -> str:
        """Send a prompt with images to the LLM and get the response.
        
        Args:
            messages: List of conversation messages
            images: List of image URLs or image data dictionaries
            system_msgs: Optional system messages to prepend
            stream: Whether to stream the response
            temperature: Sampling temperature for the response
            config_name: Configuration name to use
            **kwargs: Additional provider-specific parameters
            
        Returns:
            The generated response string
            
        Raises:
            LLMServiceError: For any LLM-related errors
            UnsupportedFeatureError: If images are not supported by the provider
        """
        try:
            provider = self.get_provider(config_name)
            
            # Combine system and user messages if system messages provided
            if system_msgs:
                all_messages = system_msgs + messages
            else:
                all_messages = messages
            
            # Get response with images from provider
            response = await provider.get_chat_completion_with_images(
                messages=all_messages,
                images=images,
                stream=stream,
                temperature=temperature,
                **kwargs
            )
            
            return response if isinstance(response, str) else str(response)
            
        except Exception as e:
            logger.error(f"Error in ask_with_images method: {str(e)}")
            if isinstance(e, LLMServiceError):
                raise
            raise LLMServiceError(f"Unexpected error in ask_with_images: {str(e)}")

    async def ask_tool(
        self,
        messages: List[Union[Dict, Message]], 
        system_msgs: Optional[List[Union[Dict, Message]]] = None,
        timeout: int = 300,
        tools: Optional[List[Dict]] = None,
        tool_choice: TOOL_CHOICE_TYPE = ToolChoice.AUTO,
        temperature: Optional[float] = None,
        config_name: str = "default",
        **kwargs
    ) -> Optional[ChatCompletionMessage]:
        """Ask LLM using functions/tools and return the response.
        
        Args:
            messages: List of conversation messages
            system_msgs: Optional system messages to prepend
            timeout: Request timeout in seconds
            tools: List of tools to use
            tool_choice: Tool choice strategy
            temperature: Sampling temperature for the response
            config_name: Configuration name to use
            **kwargs: Additional provider-specific parameters
            
        Returns:
            ChatCompletionMessage with potential tool calls, or None if no response
            
        Raises:
            LLMServiceError: For any LLM-related errors
            UnsupportedFeatureError: If tools are not supported by the provider
        """
        try:
            provider = self.get_provider(config_name)
            
            # Combine system and user messages if system messages provided
            if system_msgs:
                all_messages = system_msgs + messages
            else:
                all_messages = messages
            
            # Get response with tools from provider
            if tools is None:
                tools = []
                
            response = await provider.get_chat_completion_with_tools(
                messages=all_messages,
                tools=tools,
                tool_choice=tool_choice,
                timeout=timeout,
                temperature=temperature,
                **kwargs
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error in ask_tool method: {str(e)}")
            if isinstance(e, LLMServiceError):
                raise
            raise LLMServiceError(f"Unexpected error in ask_tool: {str(e)}")

    def count_tokens(self, text: str, config_name: str = "default") -> int:
        """Count tokens in text using the specified provider.
        
        Args:
            text: Text to count tokens for
            config_name: Configuration name to use for the provider
            
        Returns:
            Number of tokens in the text
        """
        try:
            provider = self.get_provider(config_name)
            return provider.count_tokens(text)
        except Exception as e:
            logger.error(f"Error counting tokens: {str(e)}")
            # Fallback to a basic estimate
            return len(text.split()) * 1.3  # Rough approximation

    def count_message_tokens(self, messages: List[Dict], config_name: str = "default") -> int:
        """Count total tokens in a list of messages.
        
        Args:
            messages: List of formatted messages
            config_name: Configuration name to use for the provider
            
        Returns:
            Total token count for all messages
        """
        try:
            provider = self.get_provider(config_name)
            return provider.count_message_tokens(messages)
        except Exception as e:
            logger.error(f"Error counting message tokens: {str(e)}")
            # Fallback to basic estimation
            total = 0
            for msg in messages:
                if "content" in msg:
                    content = msg["content"]
                    if isinstance(content, str):
                        total += len(content.split()) * 1.3
            return int(total)

    def get_token_usage_summary(self, config_name: str = "default") -> Dict[str, int]:
        """Get token usage summary for a provider configuration.
        
        Args:
            config_name: Configuration name to get usage for
            
        Returns:
            Dictionary with token usage statistics
        """
        try:
            provider = self.get_provider(config_name)
            return provider.get_token_usage_summary()
        except Exception as e:
            logger.error(f"Error getting token usage: {str(e)}")
            return {"error": "Unable to get token usage"}

    def supports_feature(self, feature: str, config_name: str = "default") -> bool:
        """Check if a provider supports a specific feature.
        
        Args:
            feature: Feature name to check ("images", "tools", "streaming", etc.)
            config_name: Configuration name to check
            
        Returns:
            True if feature is supported, False otherwise
        """
        try:
            provider = self.get_provider(config_name)
            return provider.supports_feature(feature)
        except Exception as e:
            logger.error(f"Error checking feature support: {str(e)}")
            return False

    def get_available_providers(self) -> Dict[str, str]:
        """Get list of available providers.
        
        Returns:
            Dictionary mapping provider names to their class names
        """
        return {
            name: provider_class.__name__ 
            for name, provider_class in self.factory.get_available_providers().items()
        }

    def clear_provider_cache(self) -> None:
        """Clear the provider instance cache.
        
        Useful for testing or when configuration changes.
        """
        self._provider_instances.clear()
        logger.info("Provider cache cleared")

    @classmethod
    def create_default(cls) -> "LLMService":
        """Create a default LLMService instance with standard factory.
        
        Returns:
            LLMService instance with default factory
        """
        factory = LLMProviderFactory()
        return cls(factory=factory)