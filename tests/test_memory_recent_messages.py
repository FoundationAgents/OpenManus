from app.schema import Memory, Message


def _memory_with_messages(count: int) -> Memory:
    memory = Memory()
    for index in range(count):
        memory.add_message(Message.user_message(f"message {index}"))
    return memory


def test_get_recent_messages_returns_the_requested_window():
    memory = _memory_with_messages(3)

    assert [m.content for m in memory.get_recent_messages(2)] == [
        "message 1",
        "message 2",
    ]
    assert [m.content for m in memory.get_recent_messages(10)] == [
        "message 0",
        "message 1",
        "message 2",
    ]


def test_get_recent_messages_returns_nothing_for_non_positive_counts():
    memory = _memory_with_messages(3)

    assert memory.get_recent_messages(0) == []
    assert memory.get_recent_messages(-1) == []


def test_get_recent_messages_on_empty_memory():
    memory = Memory()

    assert memory.get_recent_messages(0) == []
    assert memory.get_recent_messages(5) == []
