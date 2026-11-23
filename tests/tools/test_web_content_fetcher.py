import asyncio
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from bs4 import BeautifulSoup


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.tool import web_search
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


def response(html, status=200):
    result = requests.Response()
    result.status_code = status
    result.encoding = "utf-8"
    result._content = html.encode("utf-8")
    return result


@pytest.mark.asyncio
async def test_event_loop_can_service_callbacks_while_html_is_parsed(monkeypatch):
    loop = asyncio.get_running_loop()
    serviced = threading.Event()
    responsiveness = []

    def parse(*args, **kwargs):
        # A bounded rendezvous exposes loop blocking without a timing benchmark.
        loop.call_soon_threadsafe(serviced.set)
        responsiveness.append(serviced.wait(timeout=2))
        return BeautifulSoup(*args, **kwargs)

    monkeypatch.setattr(web_search, "BeautifulSoup", parse)
    monkeypatch.setattr(
        web_search.requests,
        "get",
        Mock(
            return_value=response(
                "<header>Menu</header><article><h1>Title</h1><p>hello   world</p>"
                "<script>secret()</script><style>.hidden{}</style></article>"
            )
        ),
    )

    content = await web_search.WebContentFetcher.fetch_content("https://example.test")

    assert content == "Title hello world"
    assert responsiveness == [True]


@pytest.mark.asyncio
async def test_content_still_has_its_existing_size_limit(monkeypatch):
    monkeypatch.setattr(
        web_search.requests,
        "get",
        Mock(return_value=response("<p>" + "x" * 11000 + "</p>")),
    )
    content = await web_search.WebContentFetcher.fetch_content("https://example.test")
    assert content == "x" * 10000


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [response("unavailable", 503), requests.Timeout("offline")]
)
async def test_fetch_failures_still_return_none(monkeypatch, failure):
    get = (
        Mock(side_effect=failure)
        if isinstance(failure, Exception)
        else Mock(return_value=failure)
    )
    monkeypatch.setattr(web_search.requests, "get", get)
    assert (
        await web_search.WebContentFetcher.fetch_content("https://example.test") is None
    )
