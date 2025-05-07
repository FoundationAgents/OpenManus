import pytest

from app.schema import Function, Memory, Message, Role, ToolCall


def test_message_creation():
    user_msg = Message.user_message("Hello, how are you?")
    assert user_msg.role == Role.USER
    assert user_msg.content == "Hello, how are you?"
    assert user_msg.tool_calls is None
    assert user_msg.name is None
    assert user_msg.tool_call_id is None
    assert user_msg.base64_image is None

    system_msg = Message.system_message("System is ready.")
    assert system_msg.role == Role.SYSTEM
    assert system_msg.content == "System is ready."
    assert system_msg.tool_calls is None
    assert system_msg.name is None
    assert system_msg.tool_call_id is None
    assert system_msg.base64_image is None

    assistant_msg = Message.assistant_message(
        "I am an assistant.", base64_image="image_data"
    )
    assert assistant_msg.role == Role.ASSISTANT
    assert assistant_msg.content == "I am an assistant."
    assert assistant_msg.tool_calls is None
    assert assistant_msg.name is None
    assert assistant_msg.tool_call_id is None
    assert assistant_msg.base64_image == "image_data"

    tool_msg = Message.tool_message("Tool is running.", "tool_name", "tool_id")
    assert tool_msg.role == Role.TOOL
    assert tool_msg.content == "Tool is running."
    assert tool_msg.name == "tool_name"
    assert tool_msg.tool_call_id == "tool_id"
    assert tool_msg.base64_image is None


def test_message_addition():
    msg1 = Message(role=Role.USER, content="Hello")
    msg2 = Message(role=Role.USER, content="World")
    combined = msg1 + msg2
    assert len(combined) == 2
    assert combined[0].content == "Hello"
    assert combined[1].content == "World"

    msg_list = [
        Message(role=Role.USER, content="Hello"),
        Message(role=Role.USER, content="World"),
    ]
    combined = msg1 + msg_list
    assert len(combined) == 3
    assert combined[0].content == "Hello"
    assert combined[1].content == "Hello"
    assert combined[2].content == "World"

    combined = msg_list + msg2
    assert len(combined) == 3
    assert combined[0].content == "Hello"
    assert combined[1].content == "World"
    assert combined[2].content == "World"


def test_message_to_dict():
    msg = Message(
        role=Role.USER,
        content="Hello",
        base64_image="image_data",
    )
    msg_dict = msg.to_dict()
    assert msg_dict == {
        "role": "user",
        "content": "Hello",
        "base64_image": "image_data",
    }


def test_memory_operations():
    memory = Memory()
    msg1 = Message.user_message("Hello")
    msg2 = Message.system_message("World")

    memory.add_message(msg1)
    assert len(memory.messages) == 1
    assert memory.messages[0].content == "Hello"

    memory.add_message(msg2)
    assert len(memory.messages) == 2
    assert memory.messages[1].content == "World"

    memory.clear()
    assert len(memory.messages) == 0

    memory.add_messages([msg1, msg2])
    assert len(memory.messages) == 2
    assert memory.messages[0].content == "Hello"
    assert memory.messages[1].content == "World"


def test_memory_recent_messages():
    memory = Memory()
    messages = [Message.user_message(f"Message {i}") for i in range(10)]
    memory.add_messages(messages)

    recent = memory.get_recent_messages(5)
    assert len(recent) == 5
    assert [msg.content for msg in recent] == [f"Message {i}" for i in range(5, 10)]

    recent = memory.get_recent_messages(20)
    assert len(recent) == 10
    assert [msg.content for msg in recent] == [f"Message {i}" for i in range(10)]


def test_memory_max_messages():
    memory = Memory(max_messages=5)
    messages = [Message.user_message(f"Message {i}") for i in range(10)]
    memory.add_messages(messages)

    assert len(memory.messages) == 5
    assert [msg.content for msg in memory.messages] == [
        f"Message {i}" for i in range(5, 10)
    ]


def test_memory_max_messages_1by1():
    memory = Memory(max_messages=5)
    messages = [Message.user_message(f"Message {i}") for i in range(10)]
    # memory.add_messages(messages)
    for msg in messages:
        memory.add_message(msg)

    assert len(memory.messages) == 5
    assert [msg.content for msg in memory.messages] == [
        f"Message {i}" for i in range(5, 10)
    ]


def test_memory_export_to_dict_list():
    memory = Memory(max_messages=5)
    messages = [Message.user_message(f"Message {i}") for i in range(3)]
    memory.add_messages(messages)

    dict_list = memory.to_dict_list()
    assert len(dict_list) == 3
    for i, msg_dict in enumerate(dict_list):
        assert msg_dict == {
            "role": "user",
            "content": f"Message {i}",
        }


def test_message_export_to_dict():
    msg = Message(role=Role.USER, content="Hello", base64_image="image_data")
    msg2 = Message(role=Role.SYSTEM, content="World")
    msg3 = Message(role=Role.TOOL, name="tool_name", tool_call_id="tool_id")
    msg4 = Message(
        role=Role.ASSISTANT,
        content="Assistant",
        tool_calls=[
            ToolCall(
                id="1",
                type="function",
                function=Function(name="test_function", arguments="test_args"),
            )
        ],
    )

    assert msg.to_dict() == {
        "role": "user",
        "content": "Hello",
        "base64_image": "image_data",
    }
    assert msg2.to_dict() == {
        "role": "system",
        "content": "World",
    }
    assert msg3.to_dict() == {
        "role": "tool",
        "name": "tool_name",
        "tool_call_id": "tool_id",
    }
    assert msg4.to_dict() == {
        "role": "assistant",
        "content": "Assistant",
        "tool_calls": [
            {
                "id": "1",
                "type": "function",
                "function": {
                    "name": "test_function",
                    "arguments": "test_args",
                },
            }
        ],
    }


def test_message_from_tool_calls():
    function = Function(name="test_function", arguments="test_args")
    tool_call = ToolCall(id="1", function=function)
    msg = Message.from_tool_calls([tool_call], content="Function call made.")
    assert msg.role == Role.ASSISTANT
    assert msg.content == "Function call made."

    assert isinstance(msg.tool_calls, list)
    first = msg.tool_calls[0]
    assert first.id == "1"
    assert first.type == "function"
    assert isinstance(first.function, Function)
    assert first.function.name == "test_function"
    assert first.function.arguments == "test_args"


def test_message_invalid_addition():
    msg = Message.user_message("Hello")
    with pytest.raises(TypeError):
        _ = msg + "invalid_type"

    with pytest.raises(TypeError):
        _ = "invalid_type" + msg


def test_memory_invalid_recent_messages():
    memory = Memory()
    with pytest.raises(ValueError):
        _ = memory.get_recent_messages(-1)

    with pytest.raises(ValueError):
        _ = memory.get_recent_messages(0)
