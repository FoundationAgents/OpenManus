from typing import Any, Dict, List, Optional

import requests

from app.config import config
from app.tool.search.base import SearchItem, WebSearchEngine


KEENABLE_SEARCH_URL = "https://api.keenable.ai/v1/search"
KEENABLE_PUBLIC_SEARCH_URL = "https://api.keenable.ai/v1/search/public"
# Identifies the calling application on the keyless public endpoint.
KEENABLE_APP_TITLE = "openmanus"
# Upper bound the API accepts for max_results.
KEENABLE_MAX_RESULTS = 50
# Requested snippet length; long enough that the LLM usually does not need fetch_content.
SNIPPET_MAX_LENGTH = 1000
REQUEST_TIMEOUT = 30


class KeenableSearchEngine(WebSearchEngine):
    """Keenable search API (https://keenable.ai).

    Unlike the other engines this queries a search API instead of scraping a
    results page, and it needs no account: without a key, requests go to the
    public endpoint, which is rate limited per IP. Setting `keenable_api_key`
    under `[search]` in config.toml switches to the keyed endpoint and lifts
    those limits.
    """

    api_key: Optional[str] = None
    session: Optional[requests.Session] = None

    def __init__(self, **data):
        """Initialize the Keenable engine with a requests session."""
        super().__init__(**data)
        self.session = requests.Session()

    def _resolve_api_key(self) -> Optional[str]:
        """Explicit key first, then `[search] keenable_api_key` from config."""
        if self.api_key:
            return self.api_key
        if config.search_config:
            return getattr(config.search_config, "keenable_api_key", None) or None
        return None

    def perform_search(
        self, query: str, num_results: int = 10, *args, **kwargs
    ) -> List[SearchItem]:
        """
        Keenable search engine.

        Returns results formatted according to SearchItem model. Raises on
        HTTP errors (including 429 rate limits) so the caller can retry or
        fall back to another engine instead of treating it as "no results".
        """
        if not query:
            return []

        api_key = self._resolve_api_key()
        headers = {"X-Keenable-Title": KEENABLE_APP_TITLE}
        if api_key:
            url = KEENABLE_SEARCH_URL
            headers["X-API-Key"] = api_key
        else:
            url = KEENABLE_PUBLIC_SEARCH_URL

        payload: Dict[str, Any] = {
            "query": query,
            "max_results": max(1, min(num_results, KEENABLE_MAX_RESULTS)),
            "snippet_max_length": SNIPPET_MAX_LENGTH,
        }

        response = self.session.post(
            url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            hint = f", retry after {retry_after}s" if retry_after else ""
            raise requests.HTTPError(
                f"Keenable rate limit reached (HTTP 429{hint}). "
                "Set keenable_api_key under [search] to lift the public limits.",
                response=response,
            )
        response.raise_for_status()

        results = []
        for i, item in enumerate(response.json().get("results") or []):
            url = item.get("url")
            if not url:
                continue
            # `snippet` carries the page text; `description` is usually empty.
            description = item.get("snippet") or item.get("description") or None
            results.append(
                SearchItem(
                    title=item.get("title") or f"Keenable Result {i + 1}",
                    url=url,
                    description=description,
                )
            )

        return results
