import aiohttp
from typing import Dict, List, Optional, Union
import json

from app.logger import logger


class MiraClient:
    """Client for interacting with Mira Network's API."""

    def __init__(self, api_key: str, base_url: str = "https://api.mira.network/v1"):
        """Initialize the Mira client.

        Args:
            api_key: The API key for authentication
            base_url: The base URL for the API
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "OpenManus/1.0",
        }

    async def chat_completions_create(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
        **kwargs
    ) -> Dict:
        """
        Create a chat completion with the Mira Network API.

        Args:
            model: The model to use
            messages: List of message dictionaries
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream the response
            tools: Optional list of tool definitions
            tool_choice: How to handle tool selection
            **kwargs: Additional parameters

        Returns:
            Dict containing the API response
        """
        url = f"{self.base_url}/chat/completions"

        # Prepare the request body
        body = {
            "model": model,
            "messages": messages,
        }

        # Add optional parameters
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if temperature is not None:
            body["temperature"] = temperature
        if stream:
            body["stream"] = True

        # For Mira Network, we need to handle tools differently
        # Instead of using the OpenAI format, we'll include tool information in the system message
        if tools:
            # Create a system message that describes the available tools
            tool_descriptions = []
            for tool in tools:
                if "function" in tool:
                    func = tool["function"]
                    tool_descriptions.append(
                        f"Tool: {func.get('name', 'unnamed')}\n"
                        f"Description: {func.get('description', 'No description')}\n"
                        f"Parameters: {func.get('parameters', {})}"
                    )

            # Add the tool descriptions to the first system message or create a new one
            tool_system_message = {
                "role": "system",
                "content": "You have access to the following tools:\n\n" + "\n\n".join(tool_descriptions)
            }

            # Check if there's already a system message
            has_system = any(msg.get("role") == "system" for msg in messages)

            if has_system:
                # Append to the first system message
                for msg in messages:
                    if msg.get("role") == "system":
                        msg["content"] += "\n\n" + tool_system_message["content"]
                        break
            else:
                # Add a new system message at the beginning
                messages.insert(0, tool_system_message)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, json=body) as response:
                    if response.status == 403:
                        error_text = await response.text()
                        logger.error(f"Mira API error: {response.status} - {error_text}")
                        # Return a special response that will trigger program exit
                        return {
                            "choices": [{
                                "message": {
                                    "role": "assistant",
                                    "content": f"Access denied (403 Forbidden). Please check your API key and permissions."
                                }
                            }]
                        }
                    elif response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Mira API error: {response.status} - {error_text}")
                        return {
                            "choices": [{
                                "message": {
                                    "role": "assistant",
                                    "content": f"I encountered an error: {error_text}"
                                }
                            }]
                        }

                    # Get the response text first
                    response_text = await response.text()

                    try:
                        # Try to parse as JSON
                        response_data = json.loads(response_text)
                        logger.debug(f"Raw Mira API response: {response_data}")

                        # Handle the nested data structure from Mira API
                        if isinstance(response_data, dict) and "data" in response_data:
                            # Extract the actual response data
                            response_data = response_data["data"]
                            logger.debug(f"Extracted Mira API response data: {response_data}")

                            # Ensure the response has the expected structure
                            if "choices" in response_data and response_data["choices"]:
                                return response_data
                            else:
                                logger.error(f"Invalid response structure: {response_data}")
                                return {
                                    "choices": [{
                                        "message": {
                                            "role": "assistant",
                                            "content": "I received an invalid response structure from the API."
                                        }
                                    }]
                                }
                        return response_data
                    except json.JSONDecodeError:
                        # Only log as non-JSON if we actually failed to parse it
                        logger.error(f"Non-JSON response from Mira API: {response_text}")
                        return {
                            "choices": [{
                                "message": {
                                    "role": "assistant",
                                    "content": "I received an invalid response format from the API. Please try again."
                                }
                            }]
                        }

        except Exception as e:
            logger.error(f"Error in Mira API call: {str(e)}")
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": f"I encountered an error: {str(e)}"
                    }
                }]
            }
