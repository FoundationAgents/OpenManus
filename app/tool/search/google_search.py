from googlesearch import search

from app.tool.search.base import WebSearchEngine


class GoogleSearchEngine(WebSearchEngine):
    def perform_search(
        self, query: str, num_results: int = 10, *args, **kwargs
    ) -> list[str]:
        """Returns a list of unique URLs from a Google search for the given query.

        Args:
            query: The search query.
            num_results: Number of results to return. Defaults to 10.

        Returns:
            List of unique URLs.
        """
        return list(search(query, num_results=num_results, unique=True))
