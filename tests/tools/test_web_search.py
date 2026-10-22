"""Regression tests for numeric-string web-search arguments (issue #656)."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import googlesearch
import pytest
from tenacity import wait_none


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n',
        encoding="utf-8",
    )

try:
    from app.config import SearchSettings
    from app.tool import web_search as web_search_module
    from app.tool.search.google_search import GoogleSearchEngine
    from app.tool.tool_collection import ToolCollection
    from app.tool.web_search import WebSearch
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


@pytest.fixture
def search_tool(monkeypatch):
    tool = WebSearch()
    monkeypatch.setattr(
        web_search_module,
        "config",
        SimpleNamespace(search_config=SearchSettings(max_retries=0)),
    )
    monkeypatch.setattr(tool, "_search_engine", {"google": GoogleSearchEngine()})
    monkeypatch.setattr(
        WebSearch._perform_search_with_engine.retry, "wait", wait_none()
    )
    html = "".join(
        f'<div class="ezO2md"><a href="https://example.com/{index}">'
        f'<span class="CVA68e">Result {index}</span></a><span class="FrIlee">Description</span></div>'
        for index in range(5)
    )
    request = Mock(return_value=SimpleNamespace(text=html))
    monkeypatch.setattr(googlesearch, "_req", request)
    return tool, request


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments,expected_count",
    [
        ({}, 5),
        ({"num_results": 2}, 2),
        ({"num_results": "2"}, 2),
        ({"num_results": " 3 "}, 3),
    ],
)
async def test_search_count_through_tool_collection(
    search_tool, arguments, expected_count
):
    tool, request = search_tool

    response = await ToolCollection(tool).execute(
        name="web_search", tool_input={"query": "test query", **arguments}
    )

    assert response.error is None
    assert len(response.results) == expected_count
    assert response.metadata.total_results == expected_count
    assert [item.url for item in response.results] == [
        f"https://example.com/{index}" for index in range(expected_count)
    ]
    assert all(item.source == "google" for item in response.results)
    request.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("num_results", ["five", "2.5", "", "None"])
async def test_invalid_count_returns_error_without_searching(
    search_tool, monkeypatch, num_results
):
    tool, request = search_tool
    search = AsyncMock()
    monkeypatch.setattr(tool, "_try_all_engines", search)

    response = await ToolCollection(tool).execute(
        name="web_search",
        tool_input={"query": "test query", "num_results": num_results},
    )

    assert response.query == "test query"
    assert response.error and "num_results" in response.error
    assert response.results == []
    search.assert_not_awaited()
    request.assert_not_called()
