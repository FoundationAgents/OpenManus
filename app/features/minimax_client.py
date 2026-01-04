"""Minimax M2 Pro API Client

Handles all communication with Minimax M2 Pro LLM API.
"""

import json
from typing import AsyncGenerator, List, Optional

import aiohttp


class MinimaxMessage:
    """Represents a message in the conversation."""

    def __init__(self, role: str, content: str):
        """Initialize message.

        Args:
            role: Message role (user, assistant, system).
            content: Message content.
        """
        self.role = role
        self.content = content

    def to_dict(self):
        """Convert to dictionary."""
        return {"role": self.role, "content": self.content}


class MinimaxClient:
    """Client for Minimax M2 Pro API."""

    def __init__(
        self,
        api_key: str,
        model: str = "minimax-01",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        base_url: str = "https://api.minimax.io/v1",
    ):
        """Initialize Minimax client.

        Args:
            api_key: Minimax API key.
            model: Model name (minimax-01 or minimax-01-vision).
            temperature: Temperature (0.0-1.0).
            max_tokens: Maximum tokens (1-200000).
            base_url: API base URL.
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url

    def _get_headers(self) -> dict:
        """Get request headers.

        Returns:
            Dictionary with authorization headers.
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat(self, messages: List[MinimaxMessage]) -> str:
        """Send a chat completion request.

        Args:
            messages: List of messages.

        Returns:
            Assistant response text.
        """
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model,
                "messages": [msg.to_dict() for msg in messages],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            try:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API error: {error_text}")

                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                raise Exception(f"Minimax API error: {str(e)}")

    async def chat_stream(
        self, messages: List[MinimaxMessage]
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion request.

        Args:
            messages: List of messages.

        Yields:
            Text chunks from the response.
        """
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model,
                "messages": [msg.to_dict() for msg in messages],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": True,
            }

            try:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API error: {error_text}")

                    async for line in response.content:
                        if line:
                            line_str = line.decode("utf-8").strip()
                            if line_str.startswith("data: "):
                                data_str = line_str[6:]
                                if data_str == "[DONE]":
                                    break

                                try:
                                    data = json.loads(data_str)
                                    content = data["choices"][0]["delta"].get(
                                        "content", ""
                                    )
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    pass
            except Exception as e:
                raise Exception(f"Minimax stream error: {str(e)}")

    async def complete(self, prompt: str) -> str:
        """Generate text completion.

        Args:
            prompt: Input prompt.

        Returns:
            Completion text.
        """
        messages = [MinimaxMessage("user", prompt)]
        return await self.chat(messages)

    async def test_connection(self) -> bool:
        """Test API connection.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers(),
                ) as response:
                    return response.status == 200
        except Exception:
            return False

    def update_config(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Update client configuration.

        Args:
            model: New model name.
            temperature: New temperature.
            max_tokens: New max tokens.
        """
        if model:
            self.model = model
        if temperature is not None:
            self.temperature = max(0.0, min(1.0, temperature))
        if max_tokens:
            self.max_tokens = max(1, min(200000, max_tokens))
