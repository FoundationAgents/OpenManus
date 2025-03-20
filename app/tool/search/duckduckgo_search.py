from duckduckgo_search import DDGS

from app.tool.search.base import WebSearchEngine


class DuckDuckGoSearchEngine(WebSearchEngine):
    def perform_search(self, query, num_results=10, *args, **kwargs):
        """DuckDuckGo search engine."""
        try:
            # Convert num_results to integer to avoid type problems
            max_results = int(num_results)

            with DDGS() as ddgs:
                # Use basic parameters and ensure max_results is an integer
                results = list(
                    ddgs.text(
                        keywords=query,
                        region="fr-fr",
                        safesearch="moderate",
                        max_results=max_results,
                    )
                )

                # Format results correctly
                formatted_results = []
                for result in results:
                    if isinstance(result, dict) and "href" in result:
                        formatted_results.append(result)
                    elif isinstance(result, dict) and "url" in result:
                        formatted_results.append(
                            {
                                "href": result["url"],
                                "title": result.get("title", result["url"]),
                            }
                        )
                return formatted_results
        except Exception as e:
            print(f"DuckDuckGo search error: {str(e)}")
            return []
