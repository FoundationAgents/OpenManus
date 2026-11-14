import json

from app.bedrock import ChatCompletions


def _conversation_with_two_tool_calls():
    return [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "read both files"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_a",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": "a.txt"}),
                    },
                },
                {
                    "id": "call_b",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": "b.txt"}),
                    },
                },
            ],
        },
        {"role": "tool", "name": "read_file", "tool_call_id": "call_a", "content": "A"},
        {"role": "tool", "name": "read_file", "tool_call_id": "call_b", "content": "B"},
    ]


def _convert(messages):
    return ChatCompletions(client=None)._convert_openai_messages_to_bedrock_format(
        messages
    )


def test_parallel_tool_calls_become_tool_use_blocks():
    _, bedrock_messages = _convert(_conversation_with_two_tool_calls())

    assistant_content = bedrock_messages[1]["content"]
    tool_uses = [block["toolUse"] for block in assistant_content if "toolUse" in block]

    assert [tool_use["toolUseId"] for tool_use in tool_uses] == ["call_a", "call_b"]
    assert [tool_use["name"] for tool_use in tool_uses] == ["read_file", "read_file"]
    assert [tool_use["input"] for tool_use in tool_uses] == [
        {"path": "a.txt"},
        {"path": "b.txt"},
    ]


def test_tool_results_reference_their_own_tool_use_id():
    _, bedrock_messages = _convert(_conversation_with_two_tool_calls())

    tool_result_ids = [
        block["toolResult"]["toolUseId"]
        for message in bedrock_messages[2:]
        for block in message["content"]
        if "toolResult" in block
    ]

    assert tool_result_ids == ["call_a", "call_b"]


def test_empty_assistant_content_is_not_sent_as_a_text_block():
    _, bedrock_messages = _convert(_conversation_with_two_tool_calls())

    assistant_content = bedrock_messages[1]["content"]
    text_blocks = [block["text"] for block in assistant_content if "text" in block]

    assert text_blocks == []
