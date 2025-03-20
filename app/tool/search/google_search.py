from googlesearch import search

from app.tool.search.base import WebSearchEngine


class GoogleSearchEngine(WebSearchEngine):
    def perform_search(self, query, num_results=10, *args, **kwargs):
        """Google search engine."""
        try:
            # Ensure num_results is an integer
            num_results_int = int(num_results)
            # Add default parameters to avoid errors
            results = list(
                search(query, num_results=num_results_int, lang="fr", advanced=False)
            )
            # Convert to expected format - list of dictionaries with at least a URL
            formatted_results = []
            for url in results:
                formatted_results.append({"href": url, "title": url})
            return formatted_results
        except Exception as e:
            # Display error for debugging
            print(f"Google search error: {str(e)}")
            return []
