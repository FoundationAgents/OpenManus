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
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from app.bedrock import BedrockClient
from app.config import LLMSettings, config
from app.exceptions import TokenLimitExceeded
from app.logger import logger  # Assuming a logger is set up in your app
from app.schema import (
    ROLE_VALUES,
    TOOL_CHOICE_TYPE,
    TOOL_CHOICE_VALUES,
    Message,
    ToolChoice,
)
from app.task_context import (
    emit_current_task,
    get_current_llm_connection,
    get_current_model,
)


# Models that use max_completion_tokens instead of max_tokens (cloud providers).
# For local models (LM-Studio / Ollama) these are detected dynamically.
REASONING_MODELS = ["o1", "o1-mini", "o3", "o3-mini", "o4-mini"]

# Models that require reasoning_effort instead of temperature (OpenAI cloud only)
REASONING_EFFORT_MODELS = {"o3", "o3-mini", "o4-mini"}

# Claude models with extended thinking support (cloud only — local models use auto-detect)
CLAUDE_THINKING_MODELS = {
    "claude-3-7-sonnet-20250219",
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
}

# Cloud multimodal models (local models report vision capability via /api/v0/models)
MULTIMODAL_MODELS = [
    "gpt-4-vision-preview",
    "gpt-4o",
    "gpt-4o-mini",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-7-sonnet-20250219",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
]

# --- Local-server detection helpers ---

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _is_local_server(base_url: str) -> bool:
    """Return True when base_url points at a local inference server."""
    try:
        from urllib.parse import urlparse
        host = urlparse(base_url).hostname or ""
        return host in _LOCAL_HOSTS or host.startswith("192.168.") or host.startswith("10.")
    except Exception:
        return False


def _should_retry_llm_exception(exc: Exception) -> bool:
    """Retry transient provider failures only."""
    if isinstance(exc, (TokenLimitExceeded, ValueError)):
        return False
    text = str(exc).lower()
    if "no user query found in messages" in text:
        return False
    if "jinja template" in text and "prompt template" in text:
        return False
    return isinstance(exc, (RateLimitError, APIError, OpenAIError))


class TokenCounter:
    # Token constants
    BASE_MESSAGE_TOKENS = 4
    FORMAT_TOKENS = 2
    LOW_DETAIL_IMAGE_TOKENS = 85
    HIGH_DETAIL_TILE_TOKENS = 170

    # Image processing constants
    MAX_SIZE = 2048
    HIGH_DETAIL_TARGET_SHORT_SIDE = 768
    TILE_SIZE = 512

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def count_text(self, text: str) -> int:
        """Calculate tokens for a text string"""
        return 0 if not text else len(self.tokenizer.encode(text))

    def count_image(self, image_item: dict) -> int:
        """
        Calculate tokens for an image based on detail level and dimensions

        For "low" detail: fixed 85 tokens
        For "high" detail:
        1. Scale to fit in 2048x2048 square
        2. Scale shortest side to 768px
        3. Count 512px tiles (170 tokens each)
        4. Add 85 tokens
        """
        detail = image_item.get("detail", "medium")

        # For low detail, always return fixed token count
        if detail == "low":
            return self.LOW_DETAIL_IMAGE_TOKENS

        # For medium detail (default in OpenAI), use high detail calculation
        # OpenAI doesn't specify a separate calculation for medium

        # For high detail, calculate based on dimensions if available
        if detail == "high" or detail == "medium":
            # If dimensions are provided in the image_item
            if "dimensions" in image_item:
                width, height = image_item["dimensions"]
                return self._calculate_high_detail_tokens(width, height)

        return (
            self._calculate_high_detail_tokens(1024, 1024) if detail == "high" else 1024
        )

    def _calculate_high_detail_tokens(self, width: int, height: int) -> int:
        """Calculate tokens for high detail images based on dimensions"""
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
        return (
            total_tiles * self.HIGH_DETAIL_TILE_TOKENS
        ) + self.LOW_DETAIL_IMAGE_TOKENS

    def count_content(self, content: Union[str, List[Union[str, dict]]]) -> int:
        """Calculate tokens for message content"""
        if not content:
            return 0

        if isinstance(content, str):
            return self.count_text(content)

        token_count = 0
        for item in content:
            if isinstance(item, str):
                token_count += self.count_text(item)
            elif isinstance(item, dict):
                if "text" in item:
                    token_count += self.count_text(item["text"])
                elif "image_url" in item:
                    token_count += self.count_image(item)
        return token_count

    def count_tool_calls(self, tool_calls: List[dict]) -> int:
        """Calculate tokens for tool calls"""
        token_count = 0
        for tool_call in tool_calls:
            if "function" in tool_call:
                function = tool_call["function"]
                token_count += self.count_text(function.get("name", ""))
                token_count += self.count_text(function.get("arguments", ""))
        return token_count

    def count_message_tokens(self, messages: List[dict]) -> int:
        """Calculate the total number of tokens in a message list"""
        total_tokens = self.FORMAT_TOKENS  # Base format tokens

        for message in messages:
            tokens = self.BASE_MESSAGE_TOKENS  # Base tokens per message

            # Add role tokens
            tokens += self.count_text(message.get("role", ""))

            # Add content tokens
            if "content" in message:
                tokens += self.count_content(message["content"])

            # Add tool calls tokens
            if "tool_calls" in message:
                tokens += self.count_tool_calls(message["tool_calls"])

            # Add name and tool_call_id tokens
            tokens += self.count_text(message.get("name", ""))
            tokens += self.count_text(message.get("tool_call_id", ""))

            total_tokens += tokens

        return total_tokens


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
            self.api_type = llm_config.api_type
            self.api_key = llm_config.api_key
            self.api_version = llm_config.api_version
            self.base_url = llm_config.base_url

            # Add token counting related attributes
            self.total_input_tokens = 0
            self.total_completion_tokens = 0
            self.max_input_tokens = (
                llm_config.max_input_tokens
                if hasattr(llm_config, "max_input_tokens")
                else None
            )

            # Initialize tokenizer
            try:
                self.tokenizer = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # If the model is not in tiktoken's presets, use cl100k_base as default
                self.tokenizer = tiktoken.get_encoding("cl100k_base")

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

            self.token_counter = TokenCounter(self.tokenizer)

            # --- Capability flags ---
            # These control thinking/vision behaviour and are used in ask_tool().
            # For cloud models they start from the static name-list defaults;
            # for local servers (LM-Studio / Ollama) we try to probe the API.
            self._enable_thinking: Optional[bool] = getattr(llm_config, "enable_thinking", None)
            self.caps_thinking: bool = self.model in CLAUDE_THINKING_MODELS
            self.caps_vision: bool = self.model in MULTIMODAL_MODELS

            if _is_local_server(self.base_url):
                self._probe_local_server_caps()

    # ------------------------------------------------------------------
    # Local-server capability probe
    # ------------------------------------------------------------------

    def _probe_local_server_caps(self) -> None:
        """Synchronously probe LM-Studio (or Ollama) for the active model's
        capability flags (thinking / vision).

        LM-Studio exposes /api/v0/models with per-model ``info`` objects:
          { "id": "...", "info": { "vision": bool, "reasoning": bool } }

        The ``reasoning`` flag is True for models with built-in chain-of-thought
        (QwQ, DeepSeek-R1, Phi-4 reasoning, Gemma 3 thinking variants, etc.).

        The user can always override via ``enable_thinking`` in config.toml.
        """
        import urllib.request, urllib.error, json as _json
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(self.base_url)
        origin = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))

        # --- Try LM-Studio first ---
        lms_url = f"{origin}/api/v0/models"
        try:
            with urllib.request.urlopen(lms_url, timeout=3) as resp:
                data = _json.loads(resp.read())
            models: list = data.get("data", [])
            # Find the entry matching the configured model id
            match = next(
                (m for m in models if m.get("id") == self.model or self.model in str(m.get("id", ""))),
                None,
            )
            if match:
                info = match.get("info", {})
                detected_thinking = bool(info.get("reasoning", False))
                detected_vision   = bool(info.get("vision",    False))
                self.caps_thinking = detected_thinking
                self.caps_vision   = detected_vision
                logger.info(
                    "[LM-Studio] Model '%s' caps → thinking=%s  vision=%s",
                    self.model, self.caps_thinking, self.caps_vision,
                )
            else:
                logger.debug(
                    "[LM-Studio] Could not find model '%s' in /api/v0/models list; keeping defaults.",
                    self.model,
                )
            return  # LM-Studio responded — skip Ollama probe
        except Exception as exc:
            logger.debug("[LM-Studio] /api/v0/models probe failed: %s — trying Ollama.", exc)

        # --- Fallback: Ollama /api/tags ---
        ollama_url = f"{origin}/api/tags"
        try:
            with urllib.request.urlopen(ollama_url, timeout=3) as resp:
                data = _json.loads(resp.read())
            model_names = [m.get("name", "") for m in data.get("models", [])]
            if any(self.model in name for name in model_names):
                logger.debug(
                    "[Ollama] Model '%s' found; capability auto-detect not available "
                    "— use enable_thinking in config.toml to override.",
                    self.model,
                )
        except Exception as exc:
            logger.debug("[Ollama] /api/tags probe failed: %s", exc)

    @property
    def thinking_enabled(self) -> bool:
        """True when thinking/reasoning mode should be activated for this model.

        Resolution order (highest priority first):
        1. ``enable_thinking`` in config.toml   (explicit user override)
        2. Capability flag from local-server probe  (LM-Studio ``reasoning`` flag)
        3. Cloud model name in ``CLAUDE_THINKING_MODELS``
        """
        if self._enable_thinking is not None:
            return bool(self._enable_thinking)
        return self.caps_thinking

    @property
    def vision_enabled(self) -> bool:
        """True when the active model supports image inputs."""
        return self.caps_vision

    # ------------------------------------------------------------------

    @property
    def active_model(self) -> str:
        connection = get_current_llm_connection() or {}
        return get_current_model() or connection.get("model") or self.model

    def active_request_overrides(self) -> dict:
        connection = get_current_llm_connection() or {}
        return {
            key: value
            for key, value in {
                "base_url": connection.get("base_url"),
                "api_key": connection.get("api_key"),
                "api_type": connection.get("api_type"),
                "max_tokens": connection.get("max_tokens"),
                "temperature": connection.get("temperature"),
            }.items()
            if value not in (None, "") and not self._is_masked_value(value)
        }

    @staticmethod
    def _is_masked_value(value: object) -> bool:
        return isinstance(value, str) and value.strip() == "********"

    @staticmethod
    def _safe_int(value: object, fallback: int) -> int:
        if LLM._is_masked_value(value):
            return fallback
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _safe_float(value: object, fallback: float) -> float:
        if LLM._is_masked_value(value):
            return fallback
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return fallback

    def active_client(self):
        overrides = self.active_request_overrides()
        api_type = overrides.get("api_type", self.api_type)
        if not overrides:
            return self.client
        if api_type == "aws":
            return BedrockClient()
        if api_type == "azure":
            return AsyncAzureOpenAI(
                base_url=overrides.get("base_url", self.base_url),
                api_key=overrides.get("api_key", self.api_key),
                api_version=self.api_version,
            )
        return AsyncOpenAI(
            api_key=overrides.get("api_key", self.api_key),
            base_url=overrides.get("base_url", self.base_url),
        )

    def active_max_tokens(self) -> int:
        overrides = self.active_request_overrides()
        return self._safe_int(
            overrides.get("max_tokens", self.max_tokens), self.max_tokens
        )

    def active_temperature(self) -> float:
        overrides = self.active_request_overrides()
        return self._safe_float(
            overrides.get("temperature", self.temperature), self.temperature
        )

    def active_base_url(self) -> str:
        overrides = self.active_request_overrides()
        return str(overrides.get("base_url", self.base_url) or "")

    def active_api_type(self) -> str:
        overrides = self.active_request_overrides()
        return str(overrides.get("api_type", self.api_type) or "")

    def count_tokens(self, text: str) -> int:
        """Calculate the number of tokens in a text"""
        if not text:
            return 0
        return len(self.tokenizer.encode(text))

    def count_message_tokens(self, messages: List[dict]) -> int:
        return self.token_counter.count_message_tokens(messages)

    def update_token_count(self, input_tokens: int, completion_tokens: int = 0) -> None:
        """Update token counts"""
        # Only track tokens if max_input_tokens is set
        self.total_input_tokens += input_tokens
        self.total_completion_tokens += completion_tokens
        emit_current_task(
            "token_count",
            {
                "input": input_tokens,
                "completion": completion_tokens,
                "total_input": self.total_input_tokens,
                "total_completion": self.total_completion_tokens,
            },
        )
        logger.info(
            f"Token usage: Input={input_tokens}, Completion={completion_tokens}, "
            f"Cumulative Input={self.total_input_tokens}, Cumulative Completion={self.total_completion_tokens}, "
            f"Total={input_tokens + completion_tokens}, Cumulative Total={self.total_input_tokens + self.total_completion_tokens}"
        )

    def check_token_limit(self, input_tokens: int) -> bool:
        """Check if token limits are exceeded"""
        if self.max_input_tokens is not None:
            return (self.total_input_tokens + input_tokens) <= self.max_input_tokens
        # If max_input_tokens is not set, always return True
        return True

    def get_limit_error_message(self, input_tokens: int) -> str:
        """Generate error message for token limit exceeded"""
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
        """
        Format messages for LLM by converting them to OpenAI message format.

        Args:
            messages: List of messages that can be either dict or Message objects
            supports_images: Flag indicating if the target model supports image inputs

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
            # Convert Message objects to dictionaries
            if isinstance(message, Message):
                message = message.to_dict()

            if isinstance(message, dict):
                # If message is a dict, ensure it has required fields
                if "role" not in message:
                    raise ValueError("Message dict must contain 'role' field")

                # Process base64 images if present and model supports images
                if supports_images and message.get("base64_image"):
                    # Initialize or convert content to appropriate format
                    if not message.get("content"):
                        message["content"] = []
                    elif isinstance(message["content"], str):
                        message["content"] = [
                            {"type": "text", "text": message["content"]}
                        ]
                    elif isinstance(message["content"], list):
                        # Convert string items to proper text objects
                        message["content"] = [
                            (
                                {"type": "text", "text": item}
                                if isinstance(item, str)
                                else item
                            )
                            for item in message["content"]
                        ]

                    # Add the image to content
                    message["content"].append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{message['base64_image']}"
                            },
                        }
                    )

                    # Remove the base64_image field
                    del message["base64_image"]
                # If model doesn't support images but message has base64_image, handle gracefully
                elif not supports_images and message.get("base64_image"):
                    # Just remove the base64_image field and keep the text content
                    del message["base64_image"]

                if "content" in message or "tool_calls" in message:
                    formatted_messages.append(message)
                # else: do not include the message
            else:
                raise TypeError(f"Unsupported message type: {type(message)}")

        # Validate all messages have required fields
        for msg in formatted_messages:
            if msg["role"] not in ROLE_VALUES:
                raise ValueError(f"Invalid role: {msg['role']}")

        return formatted_messages

    @staticmethod
    def ensure_user_query(messages: List[dict]) -> List[dict]:
        """Ensure local chat templates always see a user query.

        Some OpenAI-compatible local servers, notably LM Studio templates for
        tool-capable models, reject requests that contain only system/tool
        context or end with a tool observation. Keep the transcript intact, but
        add a small user continuation when needed so those templates have a
        concrete query to render.

        Note: this method NEVER mutates the input list; it always returns a new list.
        """
        if any(message.get("role") == "user" for message in messages):
            if messages and messages[-1].get("role") in {"tool", "assistant", "system"}:
                # Non-mutating: return a new list
                return [
                    *messages,
                    {
                        "role": "user",
                        "content": (
                            "Continue from the latest observation. If the task is complete, "
                            "provide the final answer or call the finish tool with a summary."
                        ),
                    },
                ]
            return messages

        for index in range(len(messages) - 1, -1, -1):
            if messages[index].get("role") == "system":
                # Return a new list with the system message role swapped to user
                return [
                    *messages[:index],
                    {**messages[index], "role": "user"},
                    *messages[index + 1:],
                ]

        return [*messages, {"role": "user", "content": "Continue."}]


    def needs_local_template_compat(self) -> bool:
        """Return true for OpenAI-compatible local servers with brittle chat templates."""
        base_url = self.active_base_url().lower()
        api_type = self.active_api_type().lower()
        return (
            api_type in {"ollama", "lmstudio", "local"}
            or ":1234" in base_url
            or "localhost" in base_url
            or "127.0.0.1" in base_url
            or "lmstudio" in base_url
        )

    @staticmethod
    def flatten_tool_history_for_templates(messages: List[dict]) -> List[dict]:
        """Convert OpenAI tool transcript details into plain chat messages.

        Some local model templates throw "No user query found" when `tool`
        roles or assistant `tool_calls` appear deep in the history. The model
        still needs the observations, so keep them as compact user-visible text.
        """
        flattened: list[dict] = []
        for message in messages:
            role = message.get("role")
            content = message.get("content") or ""

            if role == "tool":
                name = message.get("name") or message.get("tool_call_id") or "tool"
                flattened.append(
                    {
                        "role": "user",
                        "content": f"Tool observation from {name}:\n{content}",
                    }
                )
                continue

            if role == "assistant" and message.get("tool_calls"):
                if content:
                    flattened.append({"role": "assistant", "content": content})
                calls = []
                for call in message.get("tool_calls") or []:
                    function = call.get("function") or {}
                    calls.append(
                        f"- {function.get('name', 'tool')}({function.get('arguments', '{}')})"
                    )
                if calls:
                    flattened.append(
                        {
                            "role": "user",
                            "content": "Assistant requested these tools:\n"
                            + "\n".join(calls),
                        }
                    )
                continue

            cleaned = {
                key: value
                for key, value in message.items()
                if key not in {"tool_calls", "tool_call_id", "name"}
            }
            if cleaned.get("content") or cleaned.get("role") == "system":
                flattened.append(cleaned)

        return flattened

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        retry=retry_if_exception(_should_retry_llm_exception),
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
            TokenLimitExceeded: If token limits are exceeded
            ValueError: If messages are invalid or response is empty
            OpenAIError: If API call fails after retries
            Exception: For unexpected errors
        """
        try:
            # Check if the model supports images
            model = self.active_model
            supports_images = model in MULTIMODAL_MODELS

            # Format system and user messages with image support check
            if system_msgs:
                system_msgs = self.format_messages(system_msgs, supports_images)
                messages = system_msgs + self.format_messages(messages, supports_images)
            else:
                messages = self.format_messages(messages, supports_images)

            # Calculate input token count
            input_tokens = self.count_message_tokens(messages)

            # Check if token limits are exceeded
            if not self.check_token_limit(input_tokens):
                error_message = self.get_limit_error_message(input_tokens)
                # Raise a special exception that won't be retried
                raise TokenLimitExceeded(error_message)

            params = {
                "model": model,
                "messages": messages,
            }

            if model in REASONING_MODELS:
                params["max_completion_tokens"] = self.active_max_tokens()
            else:
                params["max_tokens"] = self.active_max_tokens()
                params["temperature"] = (
                    temperature
                    if temperature is not None
                    else self.active_temperature()
                )

            if not stream:
                # Non-streaming request
                response = await self.active_client().chat.completions.create(
                    **params, stream=False
                )

                if not response.choices or not response.choices[0].message.content:
                    raise ValueError("Empty or invalid response from LLM")

                # Update token counts
                self.update_token_count(
                    response.usage.prompt_tokens, response.usage.completion_tokens
                )

                return response.choices[0].message.content

            # Streaming: estimate input tokens upfront; real usage arrives in the final chunk
            self.update_token_count(input_tokens)

            response = await self.active_client().chat.completions.create(
                **params, stream=True, stream_options={"include_usage": True}
            )

            collected_messages = []
            real_completion_tokens: int = 0
            async for chunk in response:
                # The final chunk carries usage data (via stream_options); others carry content.
                if chunk.usage:
                    real_completion_tokens = chunk.usage.completion_tokens or 0
                if chunk.choices:
                    chunk_message = chunk.choices[0].delta.content or ""
                    collected_messages.append(chunk_message)

            full_response = "".join(collected_messages).strip()
            if not full_response:
                raise ValueError("Empty response from streaming LLM")

            # Use real token count when available; fall back to estimation.
            completion_tokens = real_completion_tokens or self.count_tokens(full_response)
            logger.info(
                f"Streaming completion tokens: {completion_tokens} "
                f"({'real' if real_completion_tokens else 'estimated'})"
            )
            self.update_token_count(0, completion_tokens)

            return full_response

        except TokenLimitExceeded:
            # Re-raise token limit errors without logging
            raise
        except ValueError:
            logger.exception(f"Validation error")
            raise
        except OpenAIError as oe:
            logger.exception(f"OpenAI API error")
            if isinstance(oe, AuthenticationError):
                logger.error("Authentication failed. Check API key.")
            elif isinstance(oe, RateLimitError):
                logger.error("Rate limit exceeded. Consider increasing retry attempts.")
            elif isinstance(oe, APIError):
                logger.error(f"API error: {oe}")
            raise
        except Exception:
            logger.exception(f"Unexpected error in ask")
            raise

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        retry=retry_if_exception(_should_retry_llm_exception),
    )
    async def ask_with_images(
        self,
        messages: List[Union[dict, Message]],
        images: List[Union[str, dict]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send a prompt with images to the LLM and get the response.

        Args:
            messages: List of conversation messages
            images: List of image URLs or image data dictionaries
            system_msgs: Optional system messages to prepend
            stream (bool): Whether to stream the response
            temperature (float): Sampling temperature for the response

        Returns:
            str: The generated response

        Raises:
            TokenLimitExceeded: If token limits are exceeded
            ValueError: If messages are invalid or response is empty
            OpenAIError: If API call fails after retries
            Exception: For unexpected errors
        """
        try:
            # For ask_with_images, we always set supports_images to True because
            # this method should only be called with models that support images
            model = self.active_model
            if model not in MULTIMODAL_MODELS:
                raise ValueError(
                    f"Model {model} does not support images. Use a model from {MULTIMODAL_MODELS}"
                )

            # Format messages with image support
            formatted_messages = self.format_messages(messages, supports_images=True)

            # Ensure the last message is from the user to attach images
            if not formatted_messages or formatted_messages[-1]["role"] != "user":
                raise ValueError(
                    "The last message must be from the user to attach images"
                )

            # Process the last user message to include images
            last_message = formatted_messages[-1]

            # Convert content to multimodal format if needed
            content = last_message["content"]
            multimodal_content = (
                [{"type": "text", "text": content}]
                if isinstance(content, str)
                else content
                if isinstance(content, list)
                else []
            )

            # Add images to content
            for image in images:
                if isinstance(image, str):
                    multimodal_content.append(
                        {"type": "image_url", "image_url": {"url": image}}
                    )
                elif isinstance(image, dict) and "url" in image:
                    multimodal_content.append({"type": "image_url", "image_url": image})
                elif isinstance(image, dict) and "image_url" in image:
                    multimodal_content.append(image)
                else:
                    raise ValueError(f"Unsupported image format: {image}")

            # Update the message with multimodal content
            last_message["content"] = multimodal_content

            # Add system messages if provided
            if system_msgs:
                all_messages = (
                    self.format_messages(system_msgs, supports_images=True)
                    + formatted_messages
                )
            else:
                all_messages = formatted_messages

            # Calculate tokens and check limits
            input_tokens = self.count_message_tokens(all_messages)
            if not self.check_token_limit(input_tokens):
                raise TokenLimitExceeded(self.get_limit_error_message(input_tokens))

            # Set up API parameters
            params = {
                "model": model,
                "messages": all_messages,
                "stream": stream,
            }

            # Add model-specific parameters
            if model in REASONING_MODELS:
                params["max_completion_tokens"] = self.active_max_tokens()
            else:
                params["max_tokens"] = self.active_max_tokens()
                params["temperature"] = (
                    temperature
                    if temperature is not None
                    else self.active_temperature()
                )

            # Handle non-streaming request
            if not stream:
                response = await self.active_client().chat.completions.create(**params)

                if not response.choices or not response.choices[0].message.content:
                    raise ValueError("Empty or invalid response from LLM")

                self.update_token_count(
                    response.usage.prompt_tokens, response.usage.completion_tokens
                )
                return response.choices[0].message.content

            # Handle streaming request
            self.update_token_count(input_tokens)
            response = await self.active_client().chat.completions.create(**params)

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

        except TokenLimitExceeded:
            raise
        except ValueError as ve:
            logger.error(f"Validation error in ask_with_images: {ve}")
            raise
        except OpenAIError as oe:
            logger.error(f"OpenAI API error: {oe}")
            if isinstance(oe, AuthenticationError):
                logger.error("Authentication failed. Check API key.")
            elif isinstance(oe, RateLimitError):
                logger.error("Rate limit exceeded. Consider increasing retry attempts.")
            elif isinstance(oe, APIError):
                logger.error(f"API error: {oe}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ask_with_images: {e}")
            raise

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        retry=retry_if_exception(_should_retry_llm_exception),
    )
    async def ask_tool(
        self,
        messages: List[Union[dict, Message]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        timeout: int = 300,
        tools: Optional[List[dict]] = None,
        tool_choice: TOOL_CHOICE_TYPE = ToolChoice.AUTO,  # type: ignore
        temperature: Optional[float] = None,
        **kwargs,
    ) -> ChatCompletionMessage | None:
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
            TokenLimitExceeded: If token limits are exceeded
            ValueError: If tools, tool_choice, or messages are invalid
            OpenAIError: If API call fails after retries
            Exception: For unexpected errors
        """

        def _template_error_text(exc: Exception) -> str:
            return str(exc).lower()

        def _is_template_user_query_error(exc: Exception) -> bool:
            text = _template_error_text(exc)
            return "no user query found in messages" in text or (
                "jinja template" in text and "prompt template" in text
            )

        def _build_template_fallback_messages(
            source_messages: List[dict],
        ) -> List[dict]:
            # Preserve intent while avoiding brittle tool/template transcript shapes.
            snippets: list[str] = []
            for msg in reversed(source_messages):
                role = str(msg.get("role") or "")
                content = str(msg.get("content") or "").strip()
                if role in {"assistant", "tool", "user"} and content:
                    snippets.append(f"{role}: {content[:500]}")
                if len(snippets) >= 8:
                    break
            snippets.reverse()
            fallback_prompt = (
                "The local model template rejected the full tool transcript. "
                "Continue the task from this compact context. "
                "Return a FINAL SUMMARY now with: completed work, verification, "
                "artifacts/paths, and remaining limitations. Do not request more tools.\n\n"
                + ("\n".join(snippets) if snippets else "No prior context available.")
            )
            return [{"role": "user", "content": fallback_prompt}]

        try:
            # Validate tool_choice
            if tool_choice not in TOOL_CHOICE_VALUES:
                raise ValueError(f"Invalid tool_choice: {tool_choice}")

            # Check if the model supports images
            model = self.active_model
            supports_images = model in MULTIMODAL_MODELS

            # Format messages
            if system_msgs:
                system_msgs = self.format_messages(system_msgs, supports_images)
                messages = system_msgs + self.format_messages(messages, supports_images)
            else:
                messages = self.format_messages(messages, supports_images)

            messages = self.ensure_user_query(messages)
            if self.needs_local_template_compat():
                messages = self.flatten_tool_history_for_templates(messages)
                messages = self.ensure_user_query(messages)

            # Calculate input token count
            input_tokens = self.count_message_tokens(messages)

            # If there are tools, calculate token count for tool descriptions
            tools_tokens = 0
            if tools:
                for tool in tools:
                    tools_tokens += self.count_tokens(str(tool))

            input_tokens += tools_tokens

            # Check if token limits are exceeded
            if not self.check_token_limit(input_tokens):
                error_message = self.get_limit_error_message(input_tokens)
                # Raise a special exception that won't be retried
                raise TokenLimitExceeded(error_message)

            # Validate tools if provided
            if tools:
                for tool in tools:
                    if not isinstance(tool, dict) or "type" not in tool:
                        raise ValueError("Each tool must be a dict with 'type' field")

            # Pop thinking_budget from kwargs before building params (Claude extended thinking)
            thinking_budget: Optional[int] = kwargs.pop("thinking_budget", None)
            reasoning_effort: Optional[str] = kwargs.pop("reasoning_effort", None)

            # Set up the completion request
            params = {
                "model": model,
                "messages": messages,
                "tools": tools,
                "tool_choice": tool_choice,
                "timeout": timeout,
                **kwargs,
            }

            if model in REASONING_MODELS:
                params["max_completion_tokens"] = self.active_max_tokens()
                # o3 / o4-mini accept reasoning_effort instead of temperature
                if model in REASONING_EFFORT_MODELS:
                    effort = reasoning_effort or "medium"
                    params["reasoning_effort"] = effort
                    # temperature is not valid for these models
                    params.pop("temperature", None)
            else:
                params["max_tokens"] = self.active_max_tokens()
                params["temperature"] = (
                    temperature
                    if temperature is not None
                    else self.active_temperature()
                )

            # Claude extended thinking / LM-Studio reasoning mode:
            # Prefer the instance-level thinking_enabled property which respects
            # the user's enable_thinking config and LM-Studio auto-detection.
            effective_thinking = self.thinking_enabled
            if thinking_budget and not effective_thinking:
                # Caller explicitly passed a budget — treat as opt-in override
                effective_thinking = True

            if effective_thinking:
                # Cloud Claude: structured "thinking" block
                if model in CLAUDE_THINKING_MODELS and thinking_budget:
                    params["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": int(thinking_budget),
                    }
                    logger.debug(
                        "Claude extended thinking enabled: budget=%d tokens, model=%s",
                        thinking_budget,
                        model,
                    )
                # LM-Studio / local reasoning models: pass thinking_budget as
                # extra_body so the server can honour it if supported.
                elif _is_local_server(self.base_url) and thinking_budget:
                    params.setdefault("extra_body", {})["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": int(thinking_budget),
                    }
                    logger.debug(
                        "Local-model thinking enabled: budget=%d tokens, model=%s",
                        thinking_budget,
                        model,
                    )
                elif effective_thinking:
                    logger.debug(
                        "Thinking mode active for model '%s' but no budget provided — skipping block.",
                        model,
                    )

            params["stream"] = False  # Always use non-streaming for tool requests
            response: ChatCompletion = (
                await self.active_client().chat.completions.create(**params)
            )

            # Check if response is valid
            if not response.choices or not response.choices[0].message:
                logger.warning("LLM returned an empty or invalid response: %s", response)
                return None

            # Update token counts
            self.update_token_count(
                response.usage.prompt_tokens, response.usage.completion_tokens
            )

            return response.choices[0].message

        except TokenLimitExceeded:
            # Re-raise token limit errors without logging
            raise
        except ValueError as ve:
            logger.error(f"Validation error in ask_tool: {ve}")
            raise
        except OpenAIError as oe:
            logger.error(f"OpenAI API error: {oe}")
            if isinstance(oe, AuthenticationError):
                logger.error("Authentication failed. Check API key.")
            elif isinstance(oe, RateLimitError):
                logger.error("Rate limit exceeded. Consider increasing retry attempts.")
            elif isinstance(oe, APIError):
                logger.error(f"API error: {oe}")
            if _is_template_user_query_error(oe):
                # One-shot fallback for brittle local templates:
                # retry with a compact plain user message and no tool schema.
                try:
                    emit_current_task(
                        "warning",
                        {
                            "message": "Model template rejected tool transcript; using compact fallback prompt.",
                            "detail": str(oe),
                            "fatal": False,
                        },
                    )
                    fallback_messages = _build_template_fallback_messages(messages)
                    fallback_params = {
                        "model": model,
                        "messages": fallback_messages,
                        "timeout": timeout,
                        "stream": False,
                    }
                    if model in REASONING_MODELS:
                        fallback_params[
                            "max_completion_tokens"
                        ] = self.active_max_tokens()
                    else:
                        fallback_params["max_tokens"] = self.active_max_tokens()
                        fallback_params["temperature"] = (
                            temperature
                            if temperature is not None
                            else self.active_temperature()
                        )
                    fallback_response: ChatCompletion = (
                        await self.active_client().chat.completions.create(
                            **fallback_params
                        )
                    )
                    if (
                        fallback_response.choices
                        and fallback_response.choices[0].message is not None
                    ):
                        usage = fallback_response.usage
                        if usage is not None:
                            self.update_token_count(
                                usage.prompt_tokens, usage.completion_tokens
                            )
                        # Mark fallback summaries so the agent can terminate gracefully.
                        fb_msg = fallback_response.choices[0].message
                        if fb_msg.content:
                            fb_msg.content = (
                                "[TEMPLATE_FALLBACK_FINAL]\n" + fb_msg.content
                            )
                        return fb_msg
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback after template error failed: {fallback_error}"
                    )
                raise ValueError(
                    "Model prompt template rejected this tool-call transcript "
                    "(No user query found). Use a tool-capable template/model."
                ) from oe
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ask_tool: {e}")
            raise
