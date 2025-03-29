from duckduckgo_search import DDGS

from app.tool.search.base import WebSearchEngine


class DuckDuckGoSearchEngine(WebSearchEngine):
    def perform_search(
        self, query: str, num_results: int = 10, *args, **kwargs
    ) -> list[str]:
        """Returns a list of unique URLs from a DuckDuckGo search for the given query.

        Args:
            query: The search query.
            num_results: Number of results to return. Defaults to 10.

        Returns:
            List of unique URLs.
        """
        # Perform the search and get the results
        results = DDGS().text(query, max_results=num_results)

        # Extract unique URLs using a set to avoid duplicates
        unique_urls = list({result["href"] for result in results})

        return unique_urls
