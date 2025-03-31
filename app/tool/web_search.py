import asyncio
from typing import List

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import config
from app.logger import logger
from app.tool.base import BaseTool
from app.tool.search import (
    BaiduSearchEngine,
    BingSearchEngine,
    DuckDuckGoSearchEngine,
    GoogleSearchEngine,
    WebSearchEngine,
)


class WebSearch(BaseTool):
    name: str = "web_search"
    description: str = """Perform a web search and return a list of relevant links.
    This function attempts to use the primary search engine API to get up-to-date results.
    If an error occurs, it falls back to an alternative search engine."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) The search query to submit to the search engine.",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) The number of search results to return. Default is 10.",
                "default": 10,
            },
        },
        "required": ["query"],
    }
    _search_engine: dict[str, WebSearchEngine] = {
        "google": GoogleSearchEngine(),
        "baidu": BaiduSearchEngine(),
        "duckduckgo": DuckDuckGoSearchEngine(),
        "bing": BingSearchEngine(),
    }

    async def execute(self, query: str, num_results: int = 10) -> List[str]:
        """
        Execute a Web search and return a list of URLs.
        Tries engines in order based on configuration, falling back if an engine fails with errors.
        If all engines fail, it will wait and retry up to the configured number of times.

        Args:
            query (str): The search query to submit to the search engine.
            num_results (int, optional): The number of search results to return. Default is 10.

        Returns:
            List[str]: A list of URLs matching the search query.
        """
        # Get retry settings from config
        retry_delay = 60  # Default to 60 seconds
        max_retries = 3  # Default to 3 retries

        if config.search_config:
            retry_delay = getattr(config.search_config, "retry_delay", 60)
            max_retries = getattr(config.search_config, "max_retries", 3)

        # Try searching with retries when all engines fail
        for retry_count in range(
            max_retries + 1
        ):  # +1 because first try is not a retry
            links = await self._try_all_engines(query, num_results)
            if links:
                return links

            if retry_count < max_retries:
                # All engines failed, wait and retry
                logger.warning(
                    f"All search engines failed. Waiting {retry_delay} seconds before retry {retry_count + 1}/{max_retries}..."
                )
                await asyncio.sleep(retry_delay)
            else:
                logger.error(
                    f"All search engines failed after {max_retries} retries. Giving up."
                )

        return []

    async def _try_all_engines(self, query: str, num_results: int) -> List[str]:
        """
        Try all search engines in the configured order.

        Args:
            query (str): The search query to submit to the search engine.
            num_results (int): The number of search results to return.

        Returns:
            List[str]: A list of URLs matching the search query, or empty list if all engines fail.
        """
        engine_order = self._get_engine_order()
        failed_engines = []

        for engine_name in engine_order:
            engine = self._search_engine[engine_name]
            try:
                logger.info(f"🔎 Attempting search with {engine_name.capitalize()}...")
                links = await self._perform_search_with_engine(
                    engine, query, num_results
                )
                if links:
                    if failed_engines:
                        logger.info(
                            f"Search successful with {engine_name.capitalize()} after trying: {', '.join(failed_engines)}"
                        )
                    return links
            except Exception as e:
                failed_engines.append(engine_name.capitalize())
                is_rate_limit = "429" in str(e) or "Too Many Requests" in str(e)

                if is_rate_limit:
                    logger.warning(
                        f"⚠️ {engine_name.capitalize()} search engine rate limit exceeded, trying next engine..."
                    )
                else:
                    logger.warning(
                        f"⚠️ {engine_name.capitalize()} search failed with error: {e}"
                    )

        if failed_engines:
            logger.error(f"All search engines failed: {', '.join(failed_engines)}")
        return []

    def _get_engine_order(self) -> List[str]:
        """
        Determines the order in which to try search engines.
        Preferred engine is first (based on configuration), followed by fallback engines,
        and then the remaining engines.

        Returns:
            List[str]: Ordered list of search engine names.
        """
        preferred = "google"
        fallbacks = []

        if config.search_config:
            if config.search_config.engine:
                preferred = config.search_config.engine.lower()
            if config.search_config.fallback_engines:
                fallbacks = [
                    engine.lower() for engine in config.search_config.fallback_engines
                ]

        engine_order = []
        # Add preferred engine first
        if preferred in self._search_engine:
            engine_order.append(preferred)

        # Add configured fallback engines in order
        for fallback in fallbacks:
            if fallback in self._search_engine and fallback not in engine_order:
                engine_order.append(fallback)

        return engine_order

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _perform_search_with_engine(
        self,
        engine: WebSearchEngine,
        query: str,
        num_results: int,
    ) -> List[str]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: list(engine.perform_search(query, num_results=num_results))
        )
