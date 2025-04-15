import json
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Literal, Optional

import boto3


# Global variables to track the current tool use ID across function calls
# Tmp solution
CURRENT_TOOLUSE_ID = None


# Class to handle OpenAI-style response formatting
class OpenAIResponse:
    def __init__(self, data):
        # Recursively convert nested dicts and lists to OpenAIResponse objects
        for key, value in data.items():
            if isinstance(value, dict):
                value = OpenAIResponse(value)
            elif isinstance(value, list):
                value = [
                    OpenAIResponse(item) if isinstance(item, dict) else item
                    for item in value
                ]
            setattr(self, key, value)

    def model_dump(self, *args, **kwargs):
        # Convert object to dict and add timestamp
        data = self.__dict__
        data["created_at"] = datetime.now().isoformat()
        return data


# Main client class for interacting with Amazon Bedrock
class BedrockClient:
    def __init__(self):
        # Initialize Bedrock client, you need to configure AWS env first
        try:
            self.client = boto3.client("bedrock-runtime")
            self.chat = Chat(self.client)
        except Exception as e:
            print(f"Error initializing Bedrock client: {e}")
            sys.exit(1)


# Chat interface class
class Chat:
    def __init__(self, client):
        self.completions = ChatCompletions(client)


# Core class handling chat completions functionality
class ChatCompletions:
    def __init__(self, client):
        self.client = client

    def _convert_openai_tools_to_bedrock_format(self, tools):
        # Convert OpenAI function calling format to Bedrock tool format
        bedrock_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                function = tool.get("function", {})
                bedrock_tool = {
                    "toolSpec": {
                        "name": function.get("name", ""),
                        "description": function.get("description", ""),
                        "inputSchema": {
                            "json": {
                                "type": "object",
                                "properties": function.get("parameters", {}).get(
                                    "properties", {}
                                ),
                                "required": function.get("parameters", {}).get(
                                    "required", []
                                ),
                            }
                        },
                    }
                }
                bedrock_tools.append(bedrock_tool)
        return bedrock_tools

    def _convert_openai_messages_to_bedrock_format(self, messages):
        # Convert OpenAI message format to Bedrock message format
        bedrock_messages = []
        system_prompt = []
        for message in messages:
            if message.get("role") == "system":
                system_prompt = [{"text": message.get("content")}]
            elif message.get("role") == "user":
                bedrock_message = {
                    "role": message.get("role", "user"),
                    "content": [{"text": message.get("content")}],
                }
                bedrock_messages.append(bedrock_message)
            elif message.get("role") == "assistant":
                bedrock_message = {
                    "role": "assistant",
                    "content": [{"text": message.get("content")}],
                }
                openai_tool_calls = message.get("tool_calls", [])
                if openai_tool_calls:
                    bedrock_tool_use = {
                        "toolUseId": openai_tool_calls[0]["id"],
                        "name": openai_tool_calls[0]["function"]["name"],
                        "input": json.loads(
                            openai_tool_calls[0]["function"]["arguments"]
                        ),
                    }
                    bedrock_message["content"].append({"toolUse": bedrock_tool_use})
                    global CURRENT_TOOLUSE_ID
                    CURRENT_TOOLUSE_ID = openai_tool_calls[0]["id"]
                bedrock_messages.append(bedrock_message)
            elif message.get("role") == "tool":
                bedrock_message = {
                    "role": "user",
                    "content": [
                        {
                            "toolResult": {
                                "toolUseId": CURRENT_TOOLUSE_ID,
                                "content": [{"text": message.get("content")}],
                            }
                        }
                    ],
                }
                bedrock_messages.append(bedrock_message)
            else:
                raise ValueError(f"Invalid role: {message.get('role')}")
        return system_prompt, bedrock_messages

    def _convert_bedrock_response_to_openai_format(self, bedrock_response):
        # Convert Bedrock response format to OpenAI format
        content = ""
        if bedrock_response.get("output", {}).get("message", {}).get("content"):
            content_array = bedrock_response["output"]["message"]["content"]
            content = "".join(item.get("text", "") for item in content_array)
        if content == "":
            content = "."

        # Handle tool calls in response
        openai_tool_calls = []
        if bedrock_response.get("output", {}).get("message", {}).get("content"):
            for content_item in bedrock_response["output"]["message"]["content"]:
                if content_item.get("toolUse"):
                    bedrock_tool_use = content_item["toolUse"]
                    global CURRENT_TOOLUSE_ID
                    CURRENT_TOOLUSE_ID = bedrock_tool_use["toolUseId"]
                    openai_tool_call = {
                        "id": CURRENT_TOOLUSE_ID,
                        "type": "function",
                        "function": {
                            "name": bedrock_tool_use["name"],
                            "arguments": json.dumps(bedrock_tool_use["input"]),
                        },
                    }
                    openai_tool_calls.append(openai_tool_call)

        # Construct final OpenAI format response
        openai_format = {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "created": int(time.time()),
            "object": "chat.completion",
            "system_fingerprint": None,
            "choices": [
                {
                    "finish_reason": bedrock_response.get("stopReason", "end_turn"),
                    "index": 0,
                    "message": {
                        "content": content,
                        "role": bedrock_response.get("output", {})
                        .get("message", {})
                        .get("role", "assistant"),
                        "tool_calls": openai_tool_calls
                        if openai_tool_calls != []
                        else None,
                        "function_call": None,
                    },
                }
            ],
            "usage": {
                "completion_tokens": bedrock_response.get("usage", {}).get(
                    "outputTokens", 0
                ),
                "prompt_tokens": bedrock_response.get("usage", {}).get(
                    "inputTokens", 0
                ),
                "total_tokens": bedrock_response.get("usage", {}).get("totalTokens", 0),
            },
        }
        return OpenAIResponse(openai_format)

    async def _invoke_bedrock(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        tools: Optional[List[dict]] = None,
        tool_choice: Literal["none", "auto", "required"] = "auto",
        **kwargs,
    ) -> OpenAIResponse:
        # Non-streaming invocation of Bedrock model
        (
            system_prompt,
            bedrock_messages,
        ) = self._convert_openai_messages_to_bedrock_format(messages)
        response = self.client.converse(
            modelId=model,
            system=system_prompt,
            messages=bedrock_messages,
            inferenceConfig={"temperature": temperature, "maxTokens": max_tokens},
            toolConfig={"tools": tools} if tools else None,
        )
        openai_response = self._convert_bedrock_response_to_openai_format(response)
        return openai_response

    async def _invoke_bedrock_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        tools: Optional[List[dict]] = None,
        tool_choice: Literal["none", "auto", "required"] = "auto",
        **kwargs,
    ) -> OpenAIResponse:
        # Streaming invocation of Bedrock model
        (
            system_prompt,
            bedrock_messages,
        ) = self._convert_openai_messages_to_bedrock_format(messages)
        response = self.client.converse_stream(
            modelId=model,
            system=system_prompt,
            messages=bedrock_messages,
            inferenceConfig={"temperature": temperature, "maxTokens": max_tokens},
            toolConfig={"tools": tools} if tools else None,
        )

        # Initialize response structure
        bedrock_response = {
            "output": {"message": {"role": "", "content": []}},
            "stopReason": "",
            "usage": {},
            "metrics": {},
        }
        bedrock_response_text = ""
        bedrock_response_tool_input = ""

        # Process streaming response
        stream = response.get("stream")
        if stream:
            for event in stream:
                if event.get("messageStart", {}).get("role"):
                    bedrock_response["output"]["message"]["role"] = event[
                        "messageStart"
                    ]["role"]
                if event.get("contentBlockDelta", {}).get("delta", {}).get("text"):
                    bedrock_response_text += event["contentBlockDelta"]["delta"]["text"]
                    print(
                        event["contentBlockDelta"]["delta"]["text"], end="", flush=True
                    )
                if event.get("contentBlockStop", {}).get("contentBlockIndex") == 0:
                    bedrock_response["output"]["message"]["content"].append(
                        {"text": bedrock_response_text}
                    )
                if event.get("contentBlockStart", {}).get("start", {}).get("toolUse"):
                    bedrock_tool_use = event["contentBlockStart"]["start"]["toolUse"]
                    tool_use = {
                        "toolUseId": bedrock_tool_use["toolUseId"],
                        "name": bedrock_tool_use["name"],
                    }
                    bedrock_response["output"]["message"]["content"].append(
                        {"toolUse": tool_use}
                    )
                    global CURRENT_TOOLUSE_ID
                    CURRENT_TOOLUSE_ID = bedrock_tool_use["toolUseId"]
                if event.get("contentBlockDelta", {}).get("delta", {}).get("toolUse"):
                    bedrock_response_tool_input += event["contentBlockDelta"]["delta"][
                        "toolUse"
                    ]["input"]
                    print(
                        event["contentBlockDelta"]["delta"]["toolUse"]["input"],
                        end="",
                        flush=True,
                    )
                if event.get("contentBlockStop", {}).get("contentBlockIndex") == 1:
                    bedrock_response["output"]["message"]["content"][1]["toolUse"][
                        "input"
                    ] = json.loads(bedrock_response_tool_input)
        print()
        openai_response = self._convert_bedrock_response_to_openai_format(
            bedrock_response
        )
        return openai_response

    def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        stream: Optional[bool] = True,
        tools: Optional[List[dict]] = None,
        tool_choice: Literal["none", "auto", "required"] = "auto",
        **kwargs,
    ) -> OpenAIResponse:
        # Main entry point for chat completion
        bedrock_tools = []
        if tools is not None:
            bedrock_tools = self._convert_openai_tools_to_bedrock_format(tools)
        if stream:
            return self._invoke_bedrock_stream(
                model,
                messages,
                max_tokens,
                temperature,
                bedrock_tools,
                tool_choice,
                **kwargs,
            )
        else:
            return self._invoke_bedrock(
                model,
                messages,
                max_tokens,
                temperature,
                bedrock_tools,
                tool_choice,
                **kwargs,
            )
