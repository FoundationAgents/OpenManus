import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from web_router import UnsupportedParameterError


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.config import SearchSettings, config
    from app.tool import web_search
    from app.tool.search.webrouter_search import WebRouterSearchEngine
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


def result(url, title="", description=""):
    return SimpleNamespace(url=url, title=title, description=description)


RESULTS = [
    result("https://a.example/1", "A", "first"),
    result("https://b.example/2"),
    result("", "no url"),
    result("https://c.example/3", "C", "third"),
]


class FakeRouter:
    def __init__(self, results=RESULTS, error=None, errors=()):
        self.results = results
        self.errors = [error] if error else list(errors)
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append({"query": query, **kwargs})
        if self.errors:
            raise self.errors.pop(0)
        return SimpleNamespace(results=self.results)


def engine_with(router, **fields):
    engine = WebRouterSearchEngine(**fields)
    engine._router = router
    return engine


@pytest.fixture
def search_config(monkeypatch):
    def install(**settings):
        monkeypatch.setattr(
            config._config,
            "search_config",
            SearchSettings(**settings) if settings else None,
        )

    install()
    return install


def test_maps_results_and_sends_request(search_config):
    router = FakeRouter()

    items = engine_with(router).perform_search(
        "what is x", num_results=10, lang="en", country="us"
    )

    assert [i.url for i in items] == [
        "https://a.example/1",
        "https://b.example/2",
        "https://c.example/3",
    ]
    assert items[0].title == "A"
    assert items[0].description == "first"
    assert items[1].title == "https://b.example/2"
    assert items[1].description is None
    assert router.calls == [
        {
            "query": "what is x",
            "provider": None,
            "max_results": 10,
            "country": "us",
            "locale": "en",
            "data_apis": False,
        }
    ]


def test_trims_to_num_results(search_config):
    items = engine_with(FakeRouter()).perform_search("q", num_results=2)
    assert len(items) == 2


def test_provider_read_from_config(search_config):
    search_config(webrouter_provider="tavily")
    router = FakeRouter()
    engine_with(router).perform_search("q")
    assert router.calls[0]["provider"] == "tavily"


def test_explicit_provider_wins_over_config(search_config):
    search_config(webrouter_provider="tavily")
    router = FakeRouter()
    engine_with(router, provider="exa").perform_search("q")
    assert router.calls[0]["provider"] == "exa"


def test_search_error_returns_empty_list(search_config):
    router = FakeRouter(error=RuntimeError("no backend answered"))
    assert engine_with(router).perform_search("q") == []


def test_retries_without_lang_and_country_a_backend_does_not_map(search_config):
    unsupported = UnsupportedParameterError("exa-mcp", ["locale"])
    router = FakeRouter(errors=[unsupported])

    items = engine_with(router, provider="exa-mcp").perform_search(
        "q", lang="en", country="us"
    )

    assert len(items) == 3
    assert router.calls[0]["locale"] == "en"
    assert "locale" not in router.calls[1]
    assert "country" not in router.calls[1]
    assert router.calls[1]["provider"] == "exa-mcp"


def test_other_unsupported_parameter_returns_empty_list(search_config):
    unsupported = UnsupportedParameterError("exa-mcp", ["max_results"])
    router = FakeRouter(errors=[unsupported])
    assert engine_with(router).perform_search("q") == []
    assert len(router.calls) == 1


def test_empty_query_skips_request(search_config):
    router = FakeRouter()
    assert engine_with(router).perform_search("") == []
    assert router.calls == []


def test_router_built_once(search_config, monkeypatch):
    import web_router

    built = []

    def fake_router():
        built.append(1)
        return FakeRouter()

    monkeypatch.setattr(web_router, "WebRouter", fake_router)
    engine = WebRouterSearchEngine()
    engine.perform_search("q")
    engine.perform_search("q")
    assert built == [1]


def test_missing_package_returns_empty_list(search_config, monkeypatch):
    monkeypatch.setitem(sys.modules, "web_router", None)
    assert WebRouterSearchEngine().perform_search("q") == []


@pytest.mark.parametrize(
    "settings, expected",
    [
        ({}, ["google", "baidu", "duckduckgo", "bing", "webrouter"]),
        ({"engine": "Google"}, ["google", "duckduckgo", "baidu", "bing", "webrouter"]),
        (
            {"engine": "Bing", "fallback_engines": ["DuckDuckGo"]},
            ["bing", "duckduckgo", "google", "baidu", "webrouter"],
        ),
    ],
)
def test_last_in_default_engine_order(search_config, settings, expected):
    search_config(**settings)
    assert web_search.WebSearch()._get_engine_order() == expected


def test_used_when_set_as_engine(search_config):
    search_config(engine="WebRouter")
    assert web_search.WebSearch()._get_engine_order()[0] == "webrouter"


def test_used_when_listed_as_fallback(search_config):
    search_config(engine="Google", fallback_engines=["WebRouter", "Bing"])
    order = web_search.WebSearch()._get_engine_order()
    assert order[:3] == ["google", "webrouter", "bing"]
