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
    from app.tool.search import specstream_search
    from app.tool.search.specstream_search import SpecStreamSearchEngine
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.ok = status_code < 400

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


PAYLOAD = {
    "data": {
        "kind": "answer",
        "answer": {
            "value": "42",
            "page": "https://example.com/answer",
            "seen_at": "2026-11-01",
        },
        "rows": [],
        "sources": [
            {"url": "https://a.example/1", "title": "A", "snippet": "first"},
            {"url": "https://b.example/2", "title": "", "snippet": None},
            {"url": "", "title": "no url"},
            {"url": "https://c.example/3", "title": "C", "snippet": "third"},
        ],
    }
}


@pytest.fixture
def calls(monkeypatch):
    recorded = []

    def install(response=None, error=None):
        def fake_get(url, params=None, headers=None, timeout=None):
            recorded.append(
                {"url": url, "params": params, "headers": headers, "timeout": timeout}
            )
            if error:
                raise error
            return response

        monkeypatch.setattr(specstream_search.requests, "get", fake_get)
        return recorded

    return install


def test_maps_answer_and_sources_and_sends_request(calls):
    recorded = calls(FakeResponse(payload=PAYLOAD))
    engine = SpecStreamSearchEngine(api_key="test-key")

    items = engine.perform_search("what is x", num_results=10)

    assert [i.url for i in items] == [
        "https://example.com/answer",
        "https://a.example/1",
        "https://b.example/2",
        "https://c.example/3",
    ]
    assert items[0].title == "SpecStream answer"
    assert items[0].description == "42"
    assert items[1].description == "first"
    assert items[2].title == "https://b.example/2"
    assert recorded[0]["url"] == "https://api.specstream.ai/v1/web-search"
    assert recorded[0]["params"] == {"q": "what is x"}
    assert recorded[0]["headers"] == {"Authorization": "Bearer test-key"}


def test_trims_to_num_results(calls):
    calls(FakeResponse(payload=PAYLOAD))
    items = SpecStreamSearchEngine(api_key="test-key").perform_search(
        "q", num_results=2
    )
    assert len(items) == 2


def test_null_answer_returns_sources_only(calls):
    payload = {"data": {**PAYLOAD["data"], "answer": None}}
    calls(FakeResponse(payload=payload))
    items = SpecStreamSearchEngine(api_key="test-key").perform_search("q")
    assert items[0].url == "https://a.example/1"


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(status_code=401),
        FakeResponse(status_code=402),
        FakeResponse(status_code=503, headers={"Retry-After": "5"}),
        FakeResponse(status_code=500),
        FakeResponse(status_code=200, payload=None),
    ],
)
def test_error_responses_return_empty_list(calls, response):
    calls(response)
    assert SpecStreamSearchEngine(api_key="test-key").perform_search("q") == []


def test_network_error_returns_empty_list(calls):
    calls(error=requests.ConnectionError("down"))
    assert SpecStreamSearchEngine(api_key="test-key").perform_search("q") == []


def test_missing_key_skips_request(calls, monkeypatch):
    recorded = calls(FakeResponse(payload=PAYLOAD))
    monkeypatch.setattr(SpecStreamSearchEngine, "_resolve_api_key", lambda self: None)
    assert SpecStreamSearchEngine().perform_search("q") == []
    assert recorded == []


def test_key_read_from_environment(calls, monkeypatch):
    recorded = calls(FakeResponse(payload=PAYLOAD))
    monkeypatch.setenv("SPECSTREAM_API_KEY", "env-key")
    SpecStreamSearchEngine().perform_search("q")
    assert recorded[0]["headers"] == {"Authorization": "Bearer env-key"}
