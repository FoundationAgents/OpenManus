"""Token counting and management service."""

import math
from typing import Dict, List, Union

import tiktoken
from pydantic import BaseModel, ConfigDict

from app.logger import logger


class TokenService(BaseModel):
    """Service for counting tokens across different models and providers.
    
    Extracts token counting logic from the monolithic LLM class
    and provides model-specific token counting capabilities.
    """

    # Token constants for OpenAI models
    BASE_MESSAGE_TOKENS: int = 4
    FORMAT_TOKENS: int = 2
    LOW_DETAIL_IMAGE_TOKENS: int = 85
    HIGH_DETAIL_TILE_TOKENS: int = 170

    # Image processing constants
    MAX_SIZE: int = 2048
    HIGH_DETAIL_TARGET_SHORT_SIDE: int = 768
    TILE_SIZE: int = 512

    # Model to tokenizer mapping
    _tokenizers: Dict[str, tiktoken.Encoding] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_tokenizer(self, model_name: str) -> tiktoken.Encoding:
        """Get or create tokenizer for a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Tokenizer for the model
        """
        if model_name not in self._tokenizers:
            try:
                self._tokenizers[model_name] = tiktoken.encoding_for_model(model_name)
            except KeyError:
                # If model not in tiktoken's presets, use cl100k_base as default
                logger.warning(f"Model {model_name} not found in tiktoken, using cl100k_base")
                self._tokenizers[model_name] = tiktoken.get_encoding("cl100k_base")
        
        return self._tokenizers[model_name]

    def count_text_tokens(self, text: str, model_name: str) -> int:
        """Count tokens in text for a specific model.
        
        Args:
            text: Text to count tokens for
            model_name: Name of the model to use for counting
            
        Returns:
            Number of tokens in the text
        """
        if not text:
            return 0
        
        tokenizer = self.get_tokenizer(model_name)
        return len(tokenizer.encode(text))

    def count_image_tokens(self, image_item: Dict, model_name: str) -> int:
        """Count tokens for an image based on detail level and dimensions.
        
        Args:
            image_item: Image item with detail level and optional dimensions
            model_name: Model name (for future model-specific logic)
            
        Returns:
            Number of tokens for the image
        """
        detail = image_item.get("detail", "medium")

        # For low detail, always return fixed token count
        if detail == "low":
            return self.LOW_DETAIL_IMAGE_TOKENS

        # For medium/high detail, calculate based on dimensions
        if detail in ("high", "medium"):
            # If dimensions are provided in the image_item
            if "dimensions" in image_item:
                width, height = image_item["dimensions"]
                return self._calculate_high_detail_tokens(width, height)

        # Default fallback for high/medium detail without dimensions
        return (
            self._calculate_high_detail_tokens(1024, 1024) 
            if detail == "high" 
            else 1024
        )

    def _calculate_high_detail_tokens(self, width: int, height: int) -> int:
        """Calculate tokens for high detail images based on dimensions.
        
        Args:
            width: Image width in pixels
            height: Image height in pixels
            
        Returns:
            Number of tokens for the high detail image
        """
        # Step 1: Scale to fit in MAX_SIZE x MAX_SIZE square
        if width > self.MAX_SIZE or height > self.MAX_SIZE:
            scale = self.MAX_SIZE / max(width, height)
            width = int(width * scale)
            height = int(height * scale)

        # Step 2: Scale so shortest side is HIGH_DETAIL_TARGET_SHORT_SIDE
        scale = self.HIGH_DETAIL_TARGET_SHORT_SIDE / min(width, height)
        scaled_width = int(width * scale)
        scaled_height = int(height * scale)

        # Step 3: Count number of 512px tiles
        tiles_x = math.ceil(scaled_width / self.TILE_SIZE)
        tiles_y = math.ceil(scaled_height / self.TILE_SIZE)
        total_tiles = tiles_x * tiles_y

        # Step 4: Calculate final token count
        return (total_tiles * self.HIGH_DETAIL_TILE_TOKENS) + self.LOW_DETAIL_IMAGE_TOKENS

    def count_content_tokens(
        self, 
        content: Union[str, List[Union[str, Dict]]], 
        model_name: str
    ) -> int:
        """Count tokens for message content (text and/or images).
        
        Args:
            content: Message content (string or list of content items)
            model_name: Model name for tokenization
            
        Returns:
            Total token count for the content
        """
        if not content:
            return 0

        if isinstance(content, str):
            return self.count_text_tokens(content, model_name)

        token_count = 0
        for item in content:
            if isinstance(item, str):
                token_count += self.count_text_tokens(item, model_name)
            elif isinstance(item, dict):
                if "text" in item:
                    token_count += self.count_text_tokens(item["text"], model_name)
                elif "image_url" in item:
                    token_count += self.count_image_tokens(item, model_name)
        
        return token_count

    def count_tool_calls_tokens(self, tool_calls: List[Dict], model_name: str) -> int:
        """Count tokens for tool calls in a message.
        
        Args:
            tool_calls: List of tool call objects
            model_name: Model name for tokenization
            
        Returns:
            Total token count for all tool calls
        """
        token_count = 0
        for tool_call in tool_calls:
            if "function" in tool_call:
                function = tool_call["function"]
                token_count += self.count_text_tokens(function.get("name", ""), model_name)
                token_count += self.count_text_tokens(function.get("arguments", ""), model_name)
        
        return token_count

    def count_message_tokens(self, messages: List[Dict], model_name: str) -> int:
        """Count total tokens in a list of messages.
        
        Args:
            messages: List of formatted messages
            model_name: Model name for tokenization
            
        Returns:
            Total token count for all messages
        """
        total_tokens = self.FORMAT_TOKENS  # Base format tokens

        for message in messages:
            tokens = self.BASE_MESSAGE_TOKENS  # Base tokens per message

            # Add role tokens
            tokens += self.count_text_tokens(message.get("role", ""), model_name)

            # Add content tokens
            if "content" in message:
                tokens += self.count_content_tokens(message["content"], model_name)

            # Add tool calls tokens
            if "tool_calls" in message:
                tokens += self.count_tool_calls_tokens(message["tool_calls"], model_name)

            # Add name and tool_call_id tokens
            tokens += self.count_text_tokens(message.get("name", ""), model_name)
            tokens += self.count_text_tokens(message.get("tool_call_id", ""), model_name)

            total_tokens += tokens

        return total_tokens

    def count_tools_tokens(self, tools: List[Dict], model_name: str) -> int:
        """Count tokens for tool definitions.
        
        Args:
            tools: List of tool definitions
            model_name: Model name for tokenization
            
        Returns:
            Total token count for tool definitions
        """
        total_tokens = 0
        for tool in tools:
            # Convert tool dict to string for token counting
            tool_str = str(tool)
            total_tokens += self.count_text_tokens(tool_str, model_name)
        
        return total_tokens

    def is_model_multimodal(self, model_name: str) -> bool:
        """Check if a model supports multimodal (image) inputs.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if model supports images, False otherwise
        """
        multimodal_models = [
            "gpt-4-vision-preview",
            "gpt-4o",
            "gpt-4o-mini", 
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]
        return model_name in multimodal_models

    def is_reasoning_model(self, model_name: str) -> bool:
        """Check if a model is a reasoning model (uses different parameters).
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if model is a reasoning model, False otherwise
        """
        reasoning_models = ["o1", "o3-mini"]
        return model_name in reasoning_models