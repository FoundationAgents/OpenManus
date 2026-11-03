"""Regression tests for completion-token accounting in LLM.ask_with_images.

The LLM instance is built without running __init__ so the tests stay offline:
no tiktoken download and no API client are involved.
"""

import asyncio
from pathlib import Path


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.llm import LLM, TokenCounter
    from app.schema import Message
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class _StubTokenizer:
    """Deterministic tokenizer stand-in: one token per whitespace word."""

    def encode(self, text: str, *args, **kwargs) -> list:
        return text.split()


class _FakeUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, message: _FakeMessage) -> None:
        self.message = message


class _FakeResponse:
    def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.choices = [_FakeChoice(_FakeMessage("assistant reply"))]
        self.usage = _FakeUsage(prompt_tokens, completion_tokens)


class _Delta:
    def __init__(self, content: str) -> None:
        self.content = content


class _StreamChoice:
    def __init__(self, content: str) -> None:
        self.delta = _Delta(content)


class _StreamChunk:
    def __init__(self, content: str) -> None:
        self.choices = [_StreamChoice(content)]


class _FakeStream:
    def __init__(self, chunks: list) -> None:
        self._chunks = chunks

    def __aiter__(self):
        self._iterator = iter(self._chunks)
        return self

    async def __anext__(self) -> _StreamChunk:
        try:
            return next(self._iterator)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class _FakeCompletions:
    def __init__(self, response) -> None:
        self._response = response

    async def create(self, **params):
        return self._response


class _FakeChat:
    def __init__(self, response) -> None:
        self.completions = _FakeCompletions(response)


class _FakeClient:
    def __init__(self, response) -> None:
        self.chat = _FakeChat(response)


def _make_llm(response) -> LLM:
    """Build an LLM instance with stubbed tokenizer and client (offline)."""
    llm = object.__new__(LLM)
    llm.model = "gpt-4o"
    llm.max_tokens = 100
    llm.temperature = 0.7
    llm.max_input_tokens = None
    llm.total_input_tokens = 0
    llm.total_completion_tokens = 0
    llm.tokenizer = _StubTokenizer()
    llm.token_counter = TokenCounter(llm.tokenizer)
    llm.client = _FakeClient(response)
    return llm


def _ask(llm: LLM, stream: bool) -> str:
    return asyncio.run(
        llm.ask_with_images(
            messages=[Message.user_message("describe this image")],
            images=["data:image/png;base64,abc"],
            stream=stream,
        )
    )


def test_ask_with_images_counts_completion_tokens_non_streaming():
    llm = _make_llm(_FakeResponse(prompt_tokens=10, completion_tokens=7))
    answer = _ask(llm, stream=False)

    assert answer == "assistant reply"
    assert llm.total_input_tokens == 10
    assert llm.total_completion_tokens == 7


def test_ask_with_images_counts_completion_tokens_streaming():
    stream = _FakeStream([_StreamChunk("Hello"), _StreamChunk(" world")])
    llm = _make_llm(stream)
    answer = _ask(llm, stream=True)

    assert answer == "Hello world"
    assert llm.total_input_tokens > 0
    assert llm.total_completion_tokens == llm.count_tokens("Hello world")
    assert llm.total_completion_tokens > 0
