import json

from app.llm import LLM


def test_is_anthropic_base_url_detects_native_endpoint():
    assert LLM._is_anthropic_base_url("https://api.anthropic.com/v1/")
    assert not LLM._is_anthropic_base_url("https://api.openai.com/v1")


def test_messages_to_anthropic_converts_tool_calls_and_results():
    llm = object.__new__(LLM)
    messages = [
        {"role": "user", "content": "Find the weather"},
        {
            "role": "assistant",
            "content": "Checking now.",
            "tool_calls": [
                {
                    "id": "toolu_1",
                    "type": "function",
                    "function": {
                        "name": "weather",
                        "arguments": json.dumps({"city": "Paris"}),
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "toolu_1",
            "name": "weather",
            "content": "Sunny",
        },
    ]

    anthropic_messages = llm._messages_to_anthropic(messages)

    assert anthropic_messages[0] == {
        "role": "user",
        "content": [{"type": "text", "text": "Find the weather"}],
    }
    assert anthropic_messages[1]["role"] == "assistant"
    assert anthropic_messages[1]["content"][0] == {
        "type": "text",
        "text": "Checking now.",
    }
    assert anthropic_messages[1]["content"][1] == {
        "type": "tool_use",
        "id": "toolu_1",
        "name": "weather",
        "input": {"city": "Paris"},
    }
    assert anthropic_messages[2] == {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_1",
                "content": "Sunny",
            }
        ],
    }


def test_anthropic_response_to_message_extracts_tool_calls():
    response = {
        "content": [
            {"type": "text", "text": "Need to call a tool."},
            {
                "type": "tool_use",
                "id": "toolu_1",
                "name": "weather",
                "input": {"city": "Paris"},
            },
        ]
    }

    message = LLM._anthropic_response_to_message(response)

    assert message.content == "Need to call a tool."
    assert message.tool_calls is not None
    assert len(message.tool_calls) == 1
    assert message.tool_calls[0].id == "toolu_1"
    assert message.tool_calls[0].function.name == "weather"
    assert json.loads(message.tool_calls[0].function.arguments) == {"city": "Paris"}
