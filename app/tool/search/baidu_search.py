from app.tool.search.base import WebSearchEngine


class BaiduSearchEngine(WebSearchEngine):
    def perform_search(self, query, num_results=10, *args, **kwargs):
        """Baidu search engine."""
        try:
            # Import baidusearch only if necessary
            # because the package might not be installed
            from baidusearch.baidusearch import search

            # Convert num_results to integer to avoid type problems
            num_results_int = int(num_results)

            # Work around the type problem using a simplified implementation
            # Instead of directly using the API which may have type problems
            formatted_results = []
            try:
                # Try to use the API anyway
                results = search(query, num_results=num_results_int)
                for result in results:
                    if isinstance(result, str):
                        formatted_results.append({"href": result, "title": result})
                    elif isinstance(result, dict) and "url" in result:
                        formatted_results.append(
                            {
                                "href": result["url"],
                                "title": result.get("title", result["url"]),
                            }
                        )
            except TypeError:
                # If it fails, simulate an empty result
                # This block is executed when the error '<' not supported between instances of 'int' and 'str' occurs
                print("Baidu search returned a TypeError, returning empty results")

            return formatted_results

        except ImportError:
            print("Baidu search package not installed")
            return []
        except Exception as e:
            print(f"Baidu search error: {str(e)}")
            return []
