import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from openai import APIError
from tenacity import wait_none


pytestmark = pytest.mark.asyncio


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.exceptions import TokenLimitExceeded
    from app.llm import LLM
    from app.tool.search.base import SearchItem
    from app.tool.web_search import WebSearch
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


@pytest.fixture
def llm():
    # Exercise the real public methods without constructing a tokenizer or client.
    instance = object.__new__(LLM)
    instance.model = "gpt-4o"
    instance.max_tokens = 32
    instance.temperature = 0
    instance.count_message_tokens = Mock(return_value=10)
    instance.count_tokens = Mock(return_value=1)
    instance.check_token_limit = Mock(return_value=True)
    instance.get_limit_error_message = Mock(return_value="input budget exhausted")
    instance.update_token_count = Mock()
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=1),
        )
    )
    instance.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    return instance


def invoke(llm, entrypoint):
    # Clone retry settings per call: no real backoff and no global policy changes.
    method = getattr(LLM, entrypoint).retry_with(wait=wait_none())
    arguments = {"messages": [{"role": "user", "content": "hello"}]}
    if entrypoint == "ask_with_images":
        arguments["images"] = ["https://images.example.test/image.png"]
    if entrypoint != "ask_tool":
        arguments["stream"] = False
    return method(llm, **arguments)


@pytest.mark.parametrize("entrypoint", ["ask", "ask_with_images", "ask_tool"])
async def test_input_budget_exhaustion_is_not_retried(llm, entrypoint):
    llm.check_token_limit.return_value = False

    with pytest.raises(TokenLimitExceeded, match="input budget exhausted"):
        await invoke(llm, entrypoint)

    llm.check_token_limit.assert_called_once()
    llm.client.chat.completions.create.assert_not_awaited()


@pytest.mark.parametrize("entrypoint", ["ask", "ask_with_images", "ask_tool"])
@pytest.mark.parametrize("error_kind", ["api", "runtime", "value"])
async def test_other_errors_keep_the_existing_retry_behavior(
    llm, entrypoint, error_kind
):
    if error_kind == "api":
        error = APIError(
            "temporary failure",
            request=httpx.Request("POST", "https://api.example.test/messages"),
            body=None,
        )
    elif error_kind == "runtime":
        error = RuntimeError("temporary failure")
    else:
        error = ValueError("temporary failure")
    create = llm.client.chat.completions.create
    create.side_effect = [error, create.return_value]

    result = await invoke(llm, entrypoint)

    assert (result.content if entrypoint == "ask_tool" else result) == "answer"
    assert create.await_count == 2


@pytest.mark.parametrize("entrypoint", ["ask", "ask_with_images", "ask_tool"])
async def test_cancellation_is_not_retried(llm, entrypoint):
    create = llm.client.chat.completions.create
    create.side_effect = asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await invoke(llm, entrypoint)

    assert create.await_count == 1


@pytest.fixture
def search(monkeypatch):
    instance = WebSearch.model_construct()
    instance._search_engine = {"first": Mock(), "second": Mock()}
    monkeypatch.setattr(
        WebSearch, "_get_engine_order", lambda self: ["first", "second"]
    )
    return instance


@pytest.mark.parametrize("first_outcome", ["error", "empty", "success"])
async def test_search_uses_fallback_only_when_needed(
    search, monkeypatch, first_outcome
):
    calls = []
    item = SearchItem(
        title="Result", url="https://example.test/result", description="text"
    )
    params = {"lang": "en", "country": "us"}

    async def perform(self, engine, query, count, search_params):
        calls.append(engine)
        assert query == "test query"
        assert count == 2
        assert search_params is params
        if engine is self._search_engine["first"]:
            if first_outcome == "error":
                raise RuntimeError("first engine unavailable")
            if first_outcome == "empty":
                return []
        return [item]

    monkeypatch.setattr(WebSearch, "_perform_search_with_engine", perform)
    result = await search._try_all_engines("test query", 2, params)

    expected = "first" if first_outcome == "success" else "second"
    assert result[0].source == expected
    assert result[0].url == item.url
    assert result[0].position == 1
    assert calls == [
        search._search_engine[name]
        for name in (["first"] if expected == "first" else ["first", "second"])
    ]


async def test_search_returns_empty_when_every_engine_fails(search, monkeypatch):
    calls = []

    async def perform(self, engine, *args):
        calls.append(engine)
        raise RuntimeError("engine unavailable")

    monkeypatch.setattr(WebSearch, "_perform_search_with_engine", perform)
    assert await search._try_all_engines("test query", 2, {}) == []
    assert calls == list(search._search_engine.values())


async def test_search_does_not_swallow_cancellation(search, monkeypatch):
    calls = []

    async def perform(self, engine, *args):
        calls.append(engine)
        raise asyncio.CancelledError

    monkeypatch.setattr(WebSearch, "_perform_search_with_engine", perform)
    with pytest.raises(asyncio.CancelledError):
        await search._try_all_engines("test query", 2, {})

    assert calls == [search._search_engine["first"]]
