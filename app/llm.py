from typing import Dict, List, Literal, Optional, Union

from openai import (
    APIError,
    AsyncOpenAI,
    AuthenticationError,
    OpenAIError,
    RateLimitError,
)
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.config import LLMSettings, config
from app.logger import logger  # Assuming a logger is set up in your app
from app.schema import Message
from openai import AzureOpenAI
from config.settings import Settings
import ipdb; 
import os
import asyncio

class LLM:
    _instances: Dict[str, "LLM"] = {}

    def __new__(
        cls, config_name: str = "default", llm_config: Optional[LLMSettings] = None
    ):
        if config_name not in cls._instances:
            instance = super().__new__(cls)
            instance.__init__(config_name, llm_config)
            cls._instances[config_name] = instance
        return cls._instances[config_name]

    def __init__(
        self, config_name: str = "default", llm_config: Optional[LLMSettings] = None
    ):
        if not hasattr(self, "client"):  # Only initialize if not already initialized
            llm_config = llm_config or config.llm
            llm_config = llm_config.get(config_name, llm_config["default"])
            self.model = llm_config.model
            self.max_tokens = llm_config.max_tokens
            self.temperature = llm_config.temperature
            
            try:
                # 确保先加载环境变量
                Settings.load_env()
                                
                # 从 Settings 获取 Azure OpenAI 凭据
                api_key = Settings.AZURE_OPENAI_API_KEY
                endpoint = Settings.AZURE_OPENAI_ENDPOINT
                self.deployment_name = Settings.AZURE_OPENAI_DEPLOYMENT_NAME
                
                # 检查 API 密钥是否存在
                if not api_key:
                    raise ValueError("Azure OpenAI API 密钥未设置")
                    
                # 初始化 Azure OpenAI 客户端
                self.client = AzureOpenAI(
                    api_key=api_key,
                    api_version="2023-05-15",
                    azure_endpoint=endpoint
                )
                logger.info("成功初始化 Azure OpenAI 客户端")
                
            except (AttributeError, ValueError) as e:
                # 如果 Azure 凭据不可用，回退到标准 OpenAI 客户端
                logger.warning(f"Azure OpenAI 初始化失败: {e}，回退到标准 OpenAI 客户端")
                self.client = AsyncOpenAI(
                    api_key=llm_config.api_key, 
                    base_url=llm_config.base_url
                )

    
    
    
    
    
    # def _call_azure_openai(self, prompt: str) -> Any:
    #     """调用Azure OpenAI API"""
    #     return self.client.chat.completions.create(
    #         model=self.deployment_name,
    #         messages=[
    #             {"role": "system", "content": self._get_system_prompt()},
    #             {"role": "user", "content": prompt}
    #         ],
    #         temperature=0.7,
    #         max_tokens=800
    #     )
    
    
    #Azure OpenAI 的官方客户端（azure-openai 包中的 AzureOpenAI）​默认是同步客户端，不支持直接使用 await
    #所以需要使用异步线程池来包装同步调用
    async def _call_azure_openai(self, messages, temperature, max_tokens, tools, tool_choice=None, timeout=None, **kwargs):
        # 将同步调用包装到异步线程池中
        loop = asyncio.get_event_loop()
        
        response = await loop.run_in_executor(
            None,  # 使用默认线程池
            lambda: self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=self.max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                timeout=timeout,
                **kwargs,
            )
        )
        return response
        # return response.choices[0].message.content

    async def _call_azure_openai_stream(self, messages, temperature, stream, **kwargs):
        # 将同步调用包装到异步线程池中
        loop = asyncio.get_event_loop()
        
        response = await loop.run_in_executor(
            None,  # 使用默认线程池
            lambda: self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=temperature,
                max_tokens=self.max_tokens,
                stream=stream,
                **kwargs,
            )
        )
        return response
        # return response.choices[0].message.content



    @staticmethod
    def format_messages(messages: List[Union[dict, Message]]) -> List[dict]:
        """
        Format messages for LLM by converting them to OpenAI message format.

        Args:
            messages: List of messages that can be either dict or Message objects

        Returns:
            List[dict]: List of formatted messages in OpenAI format

        Raises:
            ValueError: If messages are invalid or missing required fields
            TypeError: If unsupported message types are provided

        Examples:
            >>> msgs = [
            ...     Message.system_message("You are a helpful assistant"),
            ...     {"role": "user", "content": "Hello"},
            ...     Message.user_message("How are you?")
            ... ]
            >>> formatted = LLM.format_messages(msgs)
        """
        formatted_messages = []

        for message in messages:
            if isinstance(message, dict):
                # If message is already a dict, ensure it has required fields
                if "role" not in message:
                    raise ValueError("Message dict must contain 'role' field")
                formatted_messages.append(message)
            elif isinstance(message, Message):
                # If message is a Message object, convert it to dict
                formatted_messages.append(message.to_dict())
            else:
                raise TypeError(f"Unsupported message type: {type(message)}")

        # Validate all messages have required fields
        for msg in formatted_messages:
            if msg["role"] not in ["system", "user", "assistant", "tool"]:
                raise ValueError(f"Invalid role: {msg['role']}")
            if "content" not in msg and "tool_calls" not in msg:
                raise ValueError(
                    "Message must contain either 'content' or 'tool_calls'"
                )

        return formatted_messages

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
    )
    async def ask(
        self,
        messages: List[Union[dict, Message]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        stream: bool = True,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send a prompt to the LLM and get the response.

        Args:
            messages: List of conversation messages
            system_msgs: Optional system messages to prepend
            stream (bool): Whether to stream the response
            temperature (float): Sampling temperature for the response

        Returns:
            str: The generated response

        Raises:
            ValueError: If messages are invalid or response is empty
            OpenAIError: If API call fails after retries
            Exception: For unexpected errors
        """
        try:
            # Format system and user messages
            if system_msgs:
                system_msgs = self.format_messages(system_msgs)
                messages = system_msgs + self.format_messages(messages)
            else:
                messages = self.format_messages(messages)

            if not stream:
                # Non-streaming request
                # response = await self.client.chat.completions.create(
                #     model=self.model,
                #     messages=messages,
                #     max_tokens=self.max_tokens,
                #     temperature=temperature or self.temperature,
                #     stream=False,
                # )
                response = await self._call_azure_openai(
                    messages, 
                    temperature or self.temperature, 
                    stream=False,
                )
                if not response.choices or not response.choices[0].message.content:
                    raise ValueError("Empty or invalid response from LLM")
                return response.choices[0].message.content

            # Streaming request
            # response = await self.client.chat.completions.create(
            #     model=self.model,
            #     messages=messages,
            #     max_tokens=self.max_tokens,
            #     temperature=temperature or self.temperature,
            #     stream=True,
            # )
            response = await self._call_azure_openai_stream(
                messages, 
                temperature or self.temperature, 
                stream=True,
            )
            collected_messages = []
            async for chunk in response:
                chunk_message = chunk.choices[0].delta.content or ""
                collected_messages.append(chunk_message)
                print(chunk_message, end="", flush=True)

            print()  # Newline after streaming
            full_response = "".join(collected_messages).strip()
            if not full_response:
                raise ValueError("Empty response from streaming LLM")
            return full_response

        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            raise
        except OpenAIError as oe:
            logger.error(f"OpenAI API error: {oe}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ask: {e}")
            raise

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
    )
    async def ask_tool(
        self,
        messages: List[Union[dict, Message]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        timeout: int = 60,
        tools: Optional[List[dict]] = None,
        tool_choice: Literal["none", "auto", "required"] = "auto",
        temperature: Optional[float] = None,
        **kwargs,
    ):
        """
        Ask LLM using functions/tools and return the response.

        Args:
            messages: List of conversation messages
            system_msgs: Optional system messages to prepend
            timeout: Request timeout in seconds
            tools: List of tools to use
            tool_choice: Tool choice strategy
            temperature: Sampling temperature for the response
            **kwargs: Additional completion arguments

        Returns:
            ChatCompletionMessage: The model's response

        Raises:
            ValueError: If tools, tool_choice, or messages are invalid
            OpenAIError: If API call fails after retries
            Exception: For unexpected errors
        """
        try:
            # Validate tool_choice
            if tool_choice not in ["none", "auto", "required"]:
                raise ValueError(f"Invalid tool_choice: {tool_choice}")

            # Format messages
            if system_msgs:
                system_msgs = self.format_messages(system_msgs)
                messages = system_msgs + self.format_messages(messages)
            else:
                messages = self.format_messages(messages)

            # Validate tools if provided
            if tools:
                for tool in tools:
                    if not isinstance(tool, dict) or "type" not in tool:
                        raise ValueError("Each tool must be a dict with 'type' field")


            response = await self._call_azure_openai(
                messages, 
                temperature, 
                self.max_tokens, 
                tools, 
                tool_choice, 
                timeout, 
                **kwargs)
            
            # # Set up the completion request
            # response = await self.client.chat.completions.create(
            #     model=self.model,
            #     messages=messages,
            #     temperature=temperature or self.temperature,
            #     max_tokens=self.max_tokens,
            #     tools=tools,
            #     tool_choice=tool_choice,
            #     timeout=timeout,
            #     **kwargs,
            # )

            # Check if response is valid
            if not response.choices or not response.choices[0].message:
                print(response)
                raise ValueError("Invalid or empty response from LLM")

            return response.choices[0].message

        except ValueError as ve:
            logger.error(f"Validation error in ask_tool: {ve}")
            raise
        except OpenAIError as oe:
            if isinstance(oe, AuthenticationError):
                logger.error("Authentication failed. Check API key.")
            elif isinstance(oe, RateLimitError):
                logger.error("Rate limit exceeded. Consider increasing retry attempts.")
            elif isinstance(oe, APIError):
                logger.error(f"API error: {oe}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ask_tool: {e}")
            raise
