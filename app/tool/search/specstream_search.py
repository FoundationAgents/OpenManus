import os
from typing import List, Optional

import requests
from pydantic import Field

from app.logger import logger
from app.tool.search.base import SearchItem, WebSearchEngine


SPECSTREAM_SEARCH_URL = "https://api.specstream.ai/v1/web-search"
SPECSTREAM_API_KEY_ENV = "SPECSTREAM_API_KEY"
REQUEST_TIMEOUT_SECONDS = 30


class SpecStreamSearchEngine(WebSearchEngine):
    """SpecStream Search API (https://specstream.ai/docs/search-api).

    The API key comes from the `specstream_api_key` field of the `[search]`
    config section, or from the SPECSTREAM_API_KEY environment variable.
    """

    api_key: Optional[str] = Field(
        default=None, description="SpecStream API key; read from config or env if unset"
    )

    def _resolve_api_key(self) -> Optional[str]:
        if self.api_key:
            return self.api_key
        # Imported here so the engine can be built without a config file.
        from app.config import config

        search_config = config.search_config
        configured = getattr(search_config, "specstream_api_key", None)
        return configured or os.environ.get(SPECSTREAM_API_KEY_ENV)

    def perform_search(
        self, query: str, num_results: int = 10, *args, **kwargs
    ) -> List[SearchItem]:
        """
        SpecStream search engine.

        Returns results formatted according to SearchItem model. The API has no
        result count parameter, so the list is trimmed to num_results here.
        """
        api_key = self._resolve_api_key()
        if not api_key:
            logger.warning(
                "SpecStream search skipped: set specstream_api_key in [search] "
                f"or the {SPECSTREAM_API_KEY_ENV} environment variable."
            )
            return []

        try:
            response = requests.get(
                SPECSTREAM_SEARCH_URL,
                params={"q": query},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as e:
            logger.warning(f"SpecStream search request failed: {e}")
            return []

        if response.status_code == 401:
            logger.warning("SpecStream search rejected the API key (401).")
            return []
        if response.status_code == 402:
            logger.warning("SpecStream search balance is empty (402).")
            return []
        if response.status_code == 503:
            retry_after = response.headers.get("Retry-After")
            logger.warning(
                f"SpecStream search unavailable (503), Retry-After: {retry_after}."
            )
            return []
        if not response.ok:
            logger.warning(
                f"SpecStream search failed with status {response.status_code}."
            )
            return []

        try:
            data = response.json().get("data") or {}
        except ValueError:
            logger.warning("SpecStream search returned a body that is not JSON.")
            return []

        results: List[SearchItem] = []

        answer = data.get("answer")
        if answer and answer.get("page") and answer.get("value") is not None:
            results.append(
                SearchItem(
                    title="SpecStream answer",
                    url=answer["page"],
                    description=str(answer["value"]),
                )
            )

        for source in data.get("sources") or []:
            url = source.get("url")
            if not url:
                continue
            results.append(
                SearchItem(
                    title=source.get("title") or url,
                    url=url,
                    description=source.get("snippet"),
                )
            )

        return results[:num_results]
