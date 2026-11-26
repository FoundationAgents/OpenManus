from functools import partial
from typing import Any, Dict, List, Optional

from pydantic import Field, PrivateAttr

from app.logger import logger
from app.tool.search.base import SearchItem, WebSearchEngine


class WebRouterSearchEngine(WebSearchEngine):
    """Web search through WebRouter (https://docs.webrouter.net).

    WebRouter puts one interface in front of many search APIs and falls back
    across them. It needs no API key: with none set it uses its keyless route.
    A provider key in the process environment (for example TAVILY_API_KEY or
    EXA_API_KEY) adds that backend. `webrouter_provider` in the `[search]`
    config section pins one backend by name.
    """

    provider: Optional[str] = Field(
        default=None,
        description="WebRouter backend to use; read from config if unset, "
        "and WebRouter picks one when neither is set",
    )
    _router: Any = PrivateAttr(default=None)

    def _resolve_provider(self) -> Optional[str]:
        if self.provider:
            return self.provider
        # Imported here so the engine can be built without a config file.
        from app.config import config

        return getattr(config.search_config, "webrouter_provider", None) or None

    def _get_router(self) -> Any:
        if self._router is None:
            # Imported on first use, so OpenManus does not load it until a search
            # reaches this engine.
            from web_router import WebRouter

            self._router = WebRouter()
        return self._router

    def _search(
        self, query: str, num_results: int, regional: Dict[str, Optional[str]]
    ) -> Any:
        from web_router import UnsupportedParameterError

        search = partial(
            self._get_router().search,
            query,
            provider=self._resolve_provider(),
            max_results=num_results,
            data_apis=False,
        )
        try:
            return search(**regional)
        except UnsupportedParameterError as e:
            # Some backends take no language or country. Both come from the
            # [search] defaults, so search without them rather than fail.
            if not set(e.parameters) <= set(regional):
                raise
            logger.info(
                f"WebRouter backend {e.provider} ignores {', '.join(e.parameters)}"
            )
            return search()

    def perform_search(
        self, query: str, num_results: int = 10, *args, **kwargs
    ) -> List[SearchItem]:
        """
        WebRouter search engine.

        Returns results formatted according to SearchItem model.
        """
        if not query:
            return []

        regional = {"country": kwargs.get("country"), "locale": kwargs.get("lang")}
        try:
            response = self._search(query, num_results, regional)
        except Exception as e:
            logger.warning(f"WebRouter search failed: {e}")
            return []

        return [
            SearchItem(
                title=result.title or result.url,
                url=result.url,
                description=result.description or None,
            )
            for result in response.results
            if result.url
        ][:num_results]
