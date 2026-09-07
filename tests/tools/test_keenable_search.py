from pathlib import Path

import pytest
import requests


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.config import SearchSettings, config
    from app.tool.search.base import SearchItem, WebSearchEngine
    from app.tool.search.keenable_search import (
        KEENABLE_APP_TITLE,
        KEENABLE_MAX_RESULTS,
        KEENABLE_PUBLIC_SEARCH_URL,
        KEENABLE_SEARCH_URL,
        KeenableSearchEngine,
    )
    from app.tool.web_search import WebSearch
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


def make_engine(monkeypatch, response, api_key=None):
    """Return an engine whose session.post records the call and returns `response`."""
    engine = KeenableSearchEngine(api_key=api_key)
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return response

    monkeypatch.setattr(engine.session, "post", fake_post)
    return engine, calls


RESULTS_PAYLOAD = {
    "results": [
        {
            "url": "https://example.com/a",
            "title": "Page A",
            "snippet": "Snippet text for A",
            "description": "",
        },
        {
            "url": "https://example.com/b",
            "title": "Page B",
            "snippet": "",
            "description": "Description for B",
        },
        {"url": "https://example.com/c", "title": "", "snippet": "", "description": ""},
        {"url": "", "title": "No URL", "snippet": "dropped"},
    ]
}


def test_keyless_request_uses_public_endpoint_and_title_header(monkeypatch):
    engine, calls = make_engine(monkeypatch, FakeResponse(200, RESULTS_PAYLOAD))

    results = engine.perform_search("open source agents", num_results=5)

    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == KEENABLE_PUBLIC_SEARCH_URL
    assert call["headers"]["X-Keenable-Title"] == KEENABLE_APP_TITLE
    assert "X-API-Key" not in call["headers"]
    assert call["json"]["query"] == "open source agents"
    assert call["json"]["max_results"] == 5
    assert call["timeout"]

    assert [r.url for r in results] == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]
    assert all(isinstance(r, SearchItem) for r in results)


def test_snippet_is_preferred_over_description(monkeypatch):
    engine, _ = make_engine(monkeypatch, FakeResponse(200, RESULTS_PAYLOAD))

    a, b, c = engine.perform_search("q", num_results=3)

    assert a.description == "Snippet text for A"
    assert b.description == "Description for B"
    assert c.description is None
    assert c.title == "Keenable Result 3"


def test_explicit_api_key_uses_keyed_endpoint(monkeypatch):
    engine, calls = make_engine(
        monkeypatch, FakeResponse(200, {"results": []}), api_key="k-123"
    )

    assert engine.perform_search("q") == []
    assert calls[0]["url"] == KEENABLE_SEARCH_URL
    assert calls[0]["headers"]["X-API-Key"] == "k-123"
    assert calls[0]["headers"]["X-Keenable-Title"] == KEENABLE_APP_TITLE


def test_api_key_is_read_from_search_config(monkeypatch):
    engine, calls = make_engine(monkeypatch, FakeResponse(200, {"results": []}))
    monkeypatch.setattr(
        config._config, "search_config", SearchSettings(keenable_api_key="cfg-key")
    )

    engine.perform_search("q")

    assert calls[0]["url"] == KEENABLE_SEARCH_URL
    assert calls[0]["headers"]["X-API-Key"] == "cfg-key"


def test_empty_config_key_stays_keyless(monkeypatch):
    engine, calls = make_engine(monkeypatch, FakeResponse(200, {"results": []}))
    monkeypatch.setattr(
        config._config, "search_config", SearchSettings(keenable_api_key="")
    )

    engine.perform_search("q")

    assert calls[0]["url"] == KEENABLE_PUBLIC_SEARCH_URL
    assert "X-API-Key" not in calls[0]["headers"]


def test_num_results_is_clamped_to_api_range(monkeypatch):
    engine, calls = make_engine(monkeypatch, FakeResponse(200, {"results": []}))

    engine.perform_search("q", num_results=500)
    engine.perform_search("q", num_results=0)

    assert calls[0]["json"]["max_results"] == KEENABLE_MAX_RESULTS
    assert calls[1]["json"]["max_results"] == 1


def test_empty_query_does_not_call_api(monkeypatch):
    engine, calls = make_engine(monkeypatch, FakeResponse(200, RESULTS_PAYLOAD))

    assert engine.perform_search("") == []
    assert calls == []


def test_rate_limit_raises(monkeypatch):
    engine, _ = make_engine(
        monkeypatch, FakeResponse(429, {}, headers={"Retry-After": "60"})
    )

    with pytest.raises(requests.HTTPError, match="rate limit.*60s"):
        engine.perform_search("q")


def test_server_error_raises(monkeypatch):
    engine, _ = make_engine(monkeypatch, FakeResponse(503, {}))

    with pytest.raises(requests.HTTPError):
        engine.perform_search("q")


def test_engine_is_registered_and_tried_last_by_default(monkeypatch):
    monkeypatch.setattr(config._config, "search_config", None)
    tool = WebSearch()

    assert isinstance(tool._search_engine["keenable"], KeenableSearchEngine)
    order = tool._get_engine_order()
    assert order[0] == "google"
    assert order[-1] == "keenable"

    monkeypatch.setattr(
        config._config,
        "search_config",
        SearchSettings(fallback_engines=["Keenable", "DuckDuckGo", "Baidu", "Bing"]),
    )
    assert tool._get_engine_order() == [
        "google",
        "keenable",
        "duckduckgo",
        "baidu",
        "bing",
    ]


class RaisingEngine(WebSearchEngine):
    def perform_search(self, query, num_results=10, *args, **kwargs):
        raise requests.HTTPError("HTTP 429")


class StaticEngine(WebSearchEngine):
    def perform_search(self, query, num_results=10, *args, **kwargs):
        return [SearchItem(title="Hit", url="https://example.com", description="d")]


@pytest.mark.asyncio
async def test_failing_engine_falls_back_to_next_engine(monkeypatch):
    async def run_engine(self, engine, query, num_results, search_params):
        return list(engine.perform_search(query, num_results=num_results))

    # Bypass the tenacity retry wrapper so the test does not sleep.
    monkeypatch.setattr(WebSearch, "_perform_search_with_engine", run_engine)
    monkeypatch.setattr(
        WebSearch, "_get_engine_order", lambda self: ["first", "second"]
    )
    monkeypatch.setattr(config._config, "search_config", None)

    tool = WebSearch()
    tool._search_engine = {"first": RaisingEngine(), "second": StaticEngine()}

    results = await tool._try_all_engines("q", 1, {"lang": "en", "country": "us"})

    assert len(results) == 1
    assert results[0].source == "second"
    assert results[0].description == "d"
