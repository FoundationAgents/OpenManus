"""Concrete LLM provider implementations."""

from typing import Any, Dict, List, Optional, Union

from openai import AsyncAzureOpenAI, AsyncOpenAI, APIError, AuthenticationError, RateLimitError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from app.bedrock import BedrockClient
from app.logger import logger
from app.schema import ROLE_VALUES, Message

from .base import LLMProvider
from .exceptions import (
    MessageFormattingError,
    ProviderAPIError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    TokenLimitExceededError,
    UnsupportedFeatureError,
)
from .token_service import TokenService


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation."""

    provider_name: str = "openai"
    client: Optional[AsyncOpenAI] = None
    token_service: TokenService = TokenService()

    def __init__(self, **data):
        super().__init__(**data)
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        retry=retry_if_exception_type((APIError, Exception))
    )
    async def get_chat_completion(
        self,
        messages: List[Union[Dict, Message]],
        stream: bool = False,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Union[ChatCompletion, str]:
        """Get chat completion from OpenAI API."""
        try:
            # Format messages
            formatted_messages = self.format_messages(
                messages, 
                supports_images=self.token_service.is_model_multimodal(self.llm_model_name)
            )

            # Check token limits
            input_tokens = self.count_message_tokens(formatted_messages)
            if not self.check_token_limit(input_tokens):
                raise TokenLimitExceededError(
                    f"Token limit exceeded: {self.total_input_tokens + input_tokens} > {self.max_input_tokens}",
                    current_tokens=self.total_input_tokens,
                    requested_tokens=input_tokens,
                    max_tokens=self.max_input_tokens,
                    provider=self.provider_name
                )

            # Prepare parameters
            params = {
                "model": self.llm_model_name,
                "messages": formatted_messages,
                "stream": stream,
                **kwargs
            }

            # Handle reasoning vs regular models
            if self.token_service.is_reasoning_model(self.llm_model_name):
                params["max_completion_tokens"] = self.max_tokens
            else:
                params["max_tokens"] = self.max_tokens
                params["temperature"] = temperature if temperature is not None else self.temperature

            # Make API call
            response = await self.client.chat.completions.create(**params)

            if stream:
                return await self._handle_streaming_response(response, input_tokens)
            else:
                return await self._handle_non_streaming_response(response, input_tokens)

        except AuthenticationError as e:
            raise ProviderAuthenticationError(str(e), self.provider_name)
        except RateLimitError as e:
            raise ProviderRateLimitError(str(e), self.provider_name)
        except APIError as e:
            raise ProviderAPIError(str(e), self.provider_name)

    async def _handle_streaming_response(self, response, input_tokens: int) -> str:
        """Handle streaming response from OpenAI."""
        self.update_token_count(input_tokens)
        
        collected_messages = []
        async for chunk in response:
            chunk_message = chunk.choices[0].delta.content or ""
            collected_messages.append(chunk_message)
            print(chunk_message, end="", flush=True)

        print()  # Newline after streaming
        full_response = "".join(collected_messages).strip()
        
        if not full_response:
            raise ProviderAPIError("Empty response from streaming API", self.provider_name)

        # Estimate completion tokens
        completion_tokens = self.count_tokens(full_response)
        self.total_completion_tokens += completion_tokens
        
        return full_response

    async def _handle_non_streaming_response(self, response: ChatCompletion, input_tokens: int) -> str:
        """Handle non-streaming response from OpenAI."""
        if not response.choices or not response.choices[0].message.content:
            raise ProviderAPIError("Empty or invalid response", self.provider_name)

        # Update token counts
        self.update_token_count(
            response.usage.prompt_tokens if response.usage else input_tokens,
            response.usage.completion_tokens if response.usage else 0
        )

        return response.choices[0].message.content

    async def get_chat_completion_with_tools(
        self,
        messages: List[Union[Dict, Message]],
        tools: List[Dict],
        tool_choice: str = "auto",
        timeout: int = 300,
        **kwargs
    ) -> ChatCompletionMessage:
        """Get chat completion with tool calling support."""
        try:
            # Format messages
            formatted_messages = self.format_messages(
                messages,
                supports_images=self.token_service.is_model_multimodal(self.llm_model_name)
            )

            # Calculate tokens including tools
            input_tokens = self.count_message_tokens(formatted_messages)
            tools_tokens = self.token_service.count_tools_tokens(tools, self.llm_model_name)
            total_input_tokens = input_tokens + tools_tokens

            if not self.check_token_limit(total_input_tokens):
                raise TokenLimitExceededError(
                    f"Token limit exceeded with tools: {self.total_input_tokens + total_input_tokens} > {self.max_input_tokens}",
                    current_tokens=self.total_input_tokens,
                    requested_tokens=total_input_tokens,
                    max_tokens=self.max_input_tokens,
                    provider=self.provider_name
                )

            # Prepare parameters
            params = {
                "model": self.llm_model_name,
                "messages": formatted_messages,
                "tools": tools,
                "tool_choice": tool_choice,
                "timeout": timeout,
                "stream": False,  # Always non-streaming for tool calls
                **kwargs
            }

            if self.token_service.is_reasoning_model(self.llm_model_name):
                params["max_completion_tokens"] = self.max_tokens
            else:
                params["max_tokens"] = self.max_tokens
                params["temperature"] = self.temperature

            # Make API call
            response: ChatCompletion = await self.client.chat.completions.create(**params)

            if not response.choices or not response.choices[0].message:
                return None

            # Update token counts
            self.update_token_count(
                response.usage.prompt_tokens if response.usage else total_input_tokens,
                response.usage.completion_tokens if response.usage else 0
            )

            return response.choices[0].message

        except AuthenticationError as e:
            raise ProviderAuthenticationError(str(e), self.provider_name)
        except RateLimitError as e:
            raise ProviderRateLimitError(str(e), self.provider_name)
        except APIError as e:
            raise ProviderAPIError(str(e), self.provider_name)

    async def get_chat_completion_with_images(
        self,
        messages: List[Union[Dict, Message]],
        images: List[Union[str, Dict]],
        stream: bool = False,
        **kwargs
    ) -> str:
        """Get chat completion with image support."""
        if not self.supports_feature("images"):
            raise UnsupportedFeatureError("images", self.provider_name)

        # Format messages with images
        formatted_messages = self.format_messages(messages, supports_images=True)

        # Ensure last message is from user to attach images
        if not formatted_messages or formatted_messages[-1]["role"] != "user":
            raise MessageFormattingError(
                "Last message must be from user to attach images",
                self.provider_name
            )

        # Process images into the last message
        last_message = formatted_messages[-1]
        content = last_message["content"]
        
        # Convert to multimodal format
        multimodal_content = (
            [{"type": "text", "text": content}]
            if isinstance(content, str)
            else content if isinstance(content, list)
            else []
        )

        # Add images
        for image in images:
            if isinstance(image, str):
                multimodal_content.append({
                    "type": "image_url",
                    "image_url": {"url": image}
                })
            elif isinstance(image, dict):
                if "url" in image:
                    multimodal_content.append({
                        "type": "image_url", 
                        "image_url": image
                    })
                elif "image_url" in image:
                    multimodal_content.append(image)
                else:
                    raise MessageFormattingError(f"Invalid image format: {image}", self.provider_name)

        last_message["content"] = multimodal_content

        # Use regular completion method
        return await self.get_chat_completion(formatted_messages, stream=stream, **kwargs)

    def format_messages(
        self, 
        messages: List[Union[Dict, Message]], 
        supports_images: bool = False
    ) -> List[Dict]:
        """Format messages for OpenAI API."""
        formatted_messages = []

        for message in messages:
            # Convert Message objects to dictionaries
            if isinstance(message, Message):
                message = message.to_dict()

            if not isinstance(message, dict):
                raise MessageFormattingError(f"Invalid message type: {type(message)}", self.provider_name)

            if "role" not in message:
                raise MessageFormattingError("Message must contain 'role' field", self.provider_name)

            # Process base64 images if supported
            if supports_images and message.get("base64_image"):
                # Initialize or convert content to appropriate format
                if not message.get("content"):
                    message["content"] = []
                elif isinstance(message["content"], str):
                    message["content"] = [{"type": "text", "text": message["content"]}]
                elif isinstance(message["content"], list):
                    # Convert string items to proper text objects
                    message["content"] = [
                        {"type": "text", "text": item} if isinstance(item, str) else item
                        for item in message["content"]
                    ]

                # Add the image to content
                message["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{message['base64_image']}"
                    }
                })

                # Remove the base64_image field
                del message["base64_image"]
            
            elif not supports_images and message.get("base64_image"):
                # Remove base64 image if not supported
                del message["base64_image"]

            # Only include messages with content or tool_calls
            if "content" in message or "tool_calls" in message:
                # Validate role
                if message["role"] not in ROLE_VALUES:
                    raise MessageFormattingError(f"Invalid role: {message['role']}", self.provider_name)
                
                formatted_messages.append(message)

        return formatted_messages

    def count_tokens(self, text: str) -> int:
        """Count tokens using the token service."""
        return self.token_service.count_text_tokens(text, self.llm_model_name)

    def count_message_tokens(self, messages: List[Dict]) -> int:
        """Count message tokens using the token service."""
        return self.token_service.count_message_tokens(messages, self.llm_model_name)

    def supports_feature(self, feature: str) -> bool:
        """Check if OpenAI provider supports a feature."""
        feature_support = {
            "images": self.token_service.is_model_multimodal(self.llm_model_name),
            "tools": True,  # All OpenAI models support tools
            "streaming": True,
        }
        return feature_support.get(feature, False)


class AzureOpenAIProvider(OpenAIProvider):
    """Azure OpenAI API provider implementation."""

    provider_name: str = "azure"
    api_version: str

    def __init__(self, **data):
        super(LLMProvider, self).__init__(**data)  # Skip OpenAIProvider.__init__
        self.client = AsyncAzureOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            api_version=self.api_version
        )


class BedrockProvider(LLMProvider):
    """AWS Bedrock provider implementation."""

    provider_name: str = "bedrock"
    client: Optional[BedrockClient] = None
    token_service: TokenService = TokenService()

    def __init__(self, **data):
        super().__init__(**data)
        self.client = BedrockClient()

    async def get_chat_completion(
        self,
        messages: List[Union[Dict, Message]],
        stream: bool = False,
        **kwargs
    ) -> Any:
        """Get chat completion from Bedrock."""
        # Format messages
        formatted_messages = self.format_messages(messages, supports_images=False)
        
        # Note: Bedrock implementation would need to be adapted from the existing BedrockClient
        # This is a placeholder for the interface
        raise NotImplementedError("Bedrock provider implementation needs to be completed")

    async def get_chat_completion_with_tools(
        self,
        messages: List[Union[Dict, Message]],
        tools: List[Dict],
        tool_choice: str = "auto",
        **kwargs
    ) -> Any:
        """Get chat completion with tools from Bedrock."""
        raise UnsupportedFeatureError("tools", self.provider_name)

    async def get_chat_completion_with_images(
        self,
        messages: List[Union[Dict, Message]],
        images: List[Union[str, Dict]],
        **kwargs
    ) -> Any:
        """Get chat completion with images from Bedrock."""
        raise UnsupportedFeatureError("images", self.provider_name)

    def format_messages(
        self, 
        messages: List[Union[Dict, Message]], 
        supports_images: bool = False
    ) -> List[Dict]:
        """Format messages for Bedrock API."""
        # Bedrock may have different message formatting requirements
        # This would need to be customized based on the actual Bedrock implementation
        formatted_messages = []
        
        for message in messages:
            if isinstance(message, Message):
                message = message.to_dict()
            
            if isinstance(message, dict) and "role" in message and "content" in message:
                formatted_messages.append(message)
        
        return formatted_messages

    def count_tokens(self, text: str) -> int:
        """Count tokens for Bedrock models."""
        return self.token_service.count_text_tokens(text, self.llm_model_name)

    def count_message_tokens(self, messages: List[Dict]) -> int:
        """Count message tokens for Bedrock models."""
        return self.token_service.count_message_tokens(messages, self.llm_model_name)

    def supports_feature(self, feature: str) -> bool:
        """Check Bedrock feature support."""
        feature_support = {
            "images": False,  # Most Bedrock models don't support images
            "tools": False,   # Limited tool support in Bedrock
            "streaming": True,
        }
        return feature_support.get(feature, False)