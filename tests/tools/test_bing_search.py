from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from requests.adapters import BaseAdapter


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.tool.search.bing_search import BingSearchEngine
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class SearchResponseAdapter(BaseAdapter):
    def __init__(self):
        super().__init__()
        self.requests = []

    def send(self, request, **kwargs):
        self.requests.append(request)
        response = requests.Response()
        response.status_code = 200
        response.request = request
        response.url = request.url
        response._content = (
            b'<ol id="b_results"><li class="b_algo"><h2>'
            b'<a href="https://example.com/docs">Documentation</a></h2>'
            b"<p>A search result.</p></li></ol>"
        )
        return response

    def close(self):
        pass


@pytest.mark.parametrize("query", ["python", "C++ & C#", '中文 "file?.py"'])
def test_bing_preserves_the_query_in_the_prepared_request(query):
    engine = BingSearchEngine()
    adapter = SearchResponseAdapter()
    engine.session.mount("https://www.bing.com/", adapter)

    try:
        results = engine.perform_search(query, num_results=1)
    finally:
        engine.session.close()

    assert len(adapter.requests) == 1
    assert parse_qs(urlsplit(adapter.requests[0].url).query)["q"] == [query]
    assert [item.url for item in results] == ["https://example.com/docs"]
