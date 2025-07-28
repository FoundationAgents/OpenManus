"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from app.schema import Message


class LLMProvider(ABC, BaseModel):
    """Abstract base class for all LLM provider implementations.
    
    This class defines the contract that all LLM providers must implement,
    ensuring consistent interfaces across different provider implementations.
    """

    provider_name: str
    model_name: str
    api_key: str
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 1.0
    
    # Token tracking
    total_input_tokens: int = 0
    total_completion_tokens: int = 0
    max_input_tokens: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    async def get_chat_completion(
        self,
        messages: List[Union[Dict, Message]],
        **kwargs
    ) -> Any:
        """Get a chat completion from the LLM provider.
        
        Args:
            messages: List of conversation messages
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Provider-specific response object
            
        Raises:
            LLMServiceError: For provider-specific errors
        """
        pass

    @abstractmethod
    async def get_chat_completion_with_tools(
        self,
        messages: List[Union[Dict, Message]],
        tools: List[Dict],
        tool_choice: str = "auto",
        **kwargs
    ) -> Any:
        """Get a chat completion with tool calling support.
        
        Args:
            messages: List of conversation messages
            tools: List of available tools
            tool_choice: Tool choice strategy ("auto", "none", "required")
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Provider-specific response object with tool calls
            
        Raises:
            LLMServiceError: For provider-specific errors
            UnsupportedFeatureError: If tool calling is not supported
        """
        pass

    @abstractmethod
    async def get_chat_completion_with_images(
        self,
        messages: List[Union[Dict, Message]],  
        images: List[Union[str, Dict]],
        **kwargs
    ) -> Any:
        """Get a chat completion with image support.
        
        Args:
            messages: List of conversation messages
            images: List of image URLs or image data
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Provider-specific response object
            
        Raises:
            LLMServiceError: For provider-specific errors
            UnsupportedFeatureError: If images are not supported
        """
        pass

    @abstractmethod
    def format_messages(
        self, 
        messages: List[Union[Dict, Message]], 
        supports_images: bool = False
    ) -> List[Dict]:
        """Format messages for the specific provider.
        
        Args:
            messages: List of messages to format
            supports_images: Whether the target model supports images
            
        Returns:
            List of formatted messages in provider format
            
        Raises:
            MessageFormattingError: If message formatting fails
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text for this provider's models.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens in the text
        """
        pass

    @abstractmethod
    def count_message_tokens(self, messages: List[Dict]) -> int:
        """Count total tokens in a list of messages.
        
        Args:
            messages: List of formatted messages
            
        Returns:
            Total token count for all messages
        """
        pass

    @abstractmethod
    def supports_feature(self, feature: str) -> bool:
        """Check if provider supports a specific feature.
        
        Args:
            feature: Feature name ("images", "tools", "streaming", etc.)
            
        Returns:
            True if feature is supported, False otherwise
        """
        pass

    # Common utility methods that can be overridden if needed
    
    def update_token_count(self, input_tokens: int, completion_tokens: int = 0) -> None:
        """Update cumulative token counts.
        
        Args:
            input_tokens: Number of input tokens used
            completion_tokens: Number of completion tokens generated
        """
        self.total_input_tokens += input_tokens
        self.total_completion_tokens += completion_tokens

    def check_token_limit(self, input_tokens: int) -> bool:
        """Check if adding input tokens would exceed limits.
        
        Args:
            input_tokens: Number of input tokens to add
            
        Returns:
            True if within limits, False if would exceed
        """
        if self.max_input_tokens is None:
            return True
        return (self.total_input_tokens + input_tokens) <= self.max_input_tokens

    def get_token_usage_summary(self) -> Dict[str, int]:
        """Get summary of token usage.
        
        Returns:
            Dictionary with token usage statistics
        """
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_input_tokens + self.total_completion_tokens,
            "max_input_tokens": self.max_input_tokens,
        }