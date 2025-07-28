"""Backward-compatibility layer for the refactored LLM service.

IMPORTANT: This module serves as a compatibility adapter between the new
modular LLM service architecture and the existing codebase. It provides 
the same interface as the original monolithic LLM class while delegating
to the new service layer.

This approach allows for incremental migration - the rest of the codebase
continues to work unchanged while benefiting from the improved architecture.
"""

import math
from typing import Dict, List, Optional, Union

import tiktoken
from openai import (
    APIError,
    AsyncAzureOpenAI,
    AsyncOpenAI,
    AuthenticationError,
    OpenAIError,
    RateLimitError,
)
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.bedrock import BedrockClient
from app.config import LLMSettings, config
from app.exceptions import TokenLimitExceeded
from app.logger import logger
from app.schema import (
    ROLE_VALUES,
    TOOL_CHOICE_TYPE,
    TOOL_CHOICE_VALUES,
    Message,
    ToolChoice,
)

# Import the new service layer
from app.services.llm import LLMService, LLMProviderFactory
from app.services.llm.exceptions import TokenLimitExceededError as NewTokenLimitExceededError


# Re-export constants for backward compatibility
REASONING_MODELS = ["o1", "o3-mini"]
MULTIMODAL_MODELS = [
    "gpt-4-vision-preview",
    "gpt-4o",
    "gpt-4o-mini",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
]


class TokenCounter:
    """Legacy TokenCounter class for backward compatibility.
    
    This class maintains the original interface while delegating to the new TokenService.
    """

    # Token constants - kept for compatibility
    BASE_MESSAGE_TOKENS = 4
    FORMAT_TOKENS = 2
    LOW_DETAIL_IMAGE_TOKENS = 85
    HIGH_DETAIL_TILE_TOKENS = 170

    # Image processing constants
    MAX_SIZE = 2048
    HIGH_DETAIL_TARGET_SHORT_SIDE = 768
    TILE_SIZE = 512

    def __init__(self, tokenizer):
        """Initialize with tokenizer for compatibility."""
        self.tokenizer = tokenizer
        # Import here to avoid circular imports
        from app.services.llm.token_service import TokenService
        self._token_service = TokenService()

    def count_text(self, text: str) -> int:
        """Calculate tokens for a text string."""
        return 0 if not text else len(self.tokenizer.encode(text))

    def count_image(self, image_item: dict) -> int:
        """Calculate tokens for an image based on detail level and dimensions."""
        # Use the new token service with a default model
        return self._token_service.count_image_tokens(image_item, "gpt-4")

    def _calculate_high_detail_tokens(self, width: int, height: int) -> int:
        """Calculate tokens for high detail images based on dimensions."""
        return self._token_service._calculate_high_detail_tokens(width, height)

    def count_content(self, content: Union[str, List[Union[str, dict]]]) -> int:
        """Calculate tokens for message content."""
        return self._token_service.count_content_tokens(content, "gpt-4")

    def count_tool_calls(self, tool_calls: List[dict]) -> int:
        """Calculate tokens for tool calls."""
        return self._token_service.count_tool_calls_tokens(tool_calls, "gpt-4")

    def count_message_tokens(self, messages: List[dict]) -> int:
        """Calculate the total number of tokens in a message list."""
        return self._token_service.count_message_tokens(messages, "gpt-4")


class LLM:
    """Legacy LLM class providing backward compatibility.
    
    This class maintains the original interface while delegating all operations
    to the new LLMService. It preserves the singleton pattern and instance
    caching behavior expected by the existing codebase.
    """

    _instances: Dict[str, "LLM"] = {}
    _service: Optional[LLMService] = None

    def __new__(
        cls, config_name: str = "default", llm_config: Optional[LLMSettings] = None
    ):
        """Maintain singleton pattern for backward compatibility."""
        if config_name not in cls._instances:
            instance = super().__new__(cls)
            instance.__init__(config_name, llm_config)
            cls._instances[config_name] = instance
        return cls._instances[config_name]

    def __init__(
        self, config_name: str = "default", llm_config: Optional[LLMSettings] = None
    ):
        """Initialize the legacy LLM instance."""
        if not hasattr(self, "client"):  # Only initialize if not already initialized
            # Store config information for compatibility
            self.config_name = config_name
            llm_config = llm_config or config.llm
            llm_config = llm_config.get(config_name, llm_config["default"])
            
            # Store original attributes for compatibility
            self.model = llm_config.model
            self.max_tokens = llm_config.max_tokens
            self.temperature = llm_config.temperature
            self.api_type = llm_config.api_type
            self.api_key = llm_config.api_key
            self.api_version = llm_config.api_version
            self.base_url = llm_config.base_url

            # Token tracking attributes
            self.total_input_tokens = 0
            self.total_completion_tokens = 0
            self.max_input_tokens = (
                llm_config.max_input_tokens
                if hasattr(llm_config, "max_input_tokens")
                else None
            )

            # Initialize tokenizer for backward compatibility
            try:
                self.tokenizer = tiktoken.encoding_for_model(self.model)
            except KeyError:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")

            # Create legacy client attributes for compatibility
            if self.api_type == "azure":
                self.client = AsyncAzureOpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    api_version=self.api_version,
                )
            elif self.api_type == "aws":
                self.client = BedrockClient()
            else:
                self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

            # Initialize token counter
            self.token_counter = TokenCounter(self.tokenizer)

            # Initialize the service if not already done
            if LLM._service is None:
                factory = LLMProviderFactory()
                LLM._service = LLMService(factory=factory)

    def _get_service(self) -> LLMService:
        """Get the underlying service instance."""
        if LLM._service is None:
            factory = LLMProviderFactory()
            LLM._service = LLMService(factory=factory)
        return LLM._service

    def _sync_token_counts_from_service(self):
        """Sync token counts from the service provider."""
        try:
            service = self._get_service()
            provider = service.get_provider(self.config_name)
            self.total_input_tokens = provider.total_input_tokens
            self.total_completion_tokens = provider.total_completion_tokens
        except Exception as e:
            logger.warning(f"Could not sync token counts: {e}")

    def count_tokens(self, text: str) -> int:
        """Calculate the number of tokens in a text."""
        service = self._get_service()
        return service.count_tokens(text, self.config_name)

    def count_message_tokens(self, messages: List[dict]) -> int:
        """Count tokens in messages using the service."""
        service = self._get_service()
        return service.count_message_tokens(messages, self.config_name)

    def update_token_count(self, input_tokens: int, completion_tokens: int = 0) -> None:
        """Update token counts and sync with service."""
        self.total_input_tokens += input_tokens
        self.total_completion_tokens += completion_tokens
        logger.info(
            f"Token usage: Input={input_tokens}, Completion={completion_tokens}, "
            f"Cumulative Input={self.total_input_tokens}, Cumulative Completion={self.total_completion_tokens}, "
            f"Total={input_tokens + completion_tokens}, Cumulative Total={self.total_input_tokens + self.total_completion_tokens}"
        )

    def check_token_limit(self, input_tokens: int) -> bool:
        """Check if token limits are exceeded."""
        if self.max_input_tokens is not None:
            return (self.total_input_tokens + input_tokens) <= self.max_input_tokens
        return True

    def get_limit_error_message(self, input_tokens: int) -> str:
        """Generate error message for token limit exceeded."""
        if (
            self.max_input_tokens is not None
            and (self.total_input_tokens + input_tokens) > self.max_input_tokens
        ):
            return f"Request may exceed input token limit (Current: {self.total_input_tokens}, Needed: {input_tokens}, Max: {self.max_input_tokens})"
        return "Token limit exceeded"

    @staticmethod
    def format_messages(
        messages: List[Union[dict, Message]], supports_images: bool = False
    ) -> List[dict]:
        """Format messages for LLM - delegates to service provider."""
        # Use the new service's provider to format messages
        try:
            # Get a default service instance
            if LLM._service is None:
                factory = LLMProviderFactory()
                LLM._service = LLMService(factory=factory)
            
            provider = LLM._service.get_provider("default")
            return provider.format_messages(messages, supports_images)
        except Exception:
            # Fallback to basic formatting if service unavailable
            formatted_messages = []
            for message in messages:
                if isinstance(message, Message):
                    message = message.to_dict()
                if isinstance(message, dict) and "role" in message:
                    formatted_messages.append(message)
            return formatted_messages

    async def ask(
        self,
        messages: List[Union[dict, Message]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        stream: bool = True,
        temperature: Optional[float] = None,
    ) -> str:
        """Send a prompt to the LLM and get the response."""
        try:
            service = self._get_service()
            result = await service.ask(
                messages=messages,
                system_msgs=system_msgs,
                stream=stream,
                temperature=temperature,
                config_name=self.config_name
            )
            
            # Sync token counts after the call
            self._sync_token_counts_from_service()
            
            return result
            
        except NewTokenLimitExceededError as e:
            # Convert new exception to legacy exception
            raise TokenLimitExceeded(str(e))
        except Exception as e:
            logger.error(f"Error in legacy ask method: {e}")
            raise

    async def ask_with_images(
        self,
        messages: List[Union[dict, Message]],
        images: List[Union[str, dict]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
    ) -> str:
        """Send a prompt with images to the LLM and get the response."""
        try:
            service = self._get_service()
            result = await service.ask_with_images(
                messages=messages,
                images=images,
                system_msgs=system_msgs,
                stream=stream,
                temperature=temperature,
                config_name=self.config_name
            )
            
            # Sync token counts after the call
            self._sync_token_counts_from_service()
            
            return result
            
        except NewTokenLimitExceededError as e:
            raise TokenLimitExceeded(str(e))
        except Exception as e:
            logger.error(f"Error in legacy ask_with_images method: {e}")
            raise

    async def ask_tool(
        self,
        messages: List[Union[dict, Message]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        timeout: int = 300,
        tools: Optional[List[dict]] = None,
        tool_choice: TOOL_CHOICE_TYPE = ToolChoice.AUTO,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> ChatCompletionMessage | None:
        """Ask LLM using functions/tools and return the response."""
        try:
            service = self._get_service()
            result = await service.ask_tool(
                messages=messages,
                system_msgs=system_msgs,
                timeout=timeout,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                config_name=self.config_name,
                **kwargs
            )
            
            # Sync token counts after the call  
            self._sync_token_counts_from_service()
            
            return result
            
        except NewTokenLimitExceededError as e:
            raise TokenLimitExceeded(str(e))
        except Exception as e:
            logger.error(f"Error in legacy ask_tool method: {e}")
            raise