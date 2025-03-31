from baidusearch.baidusearch import search

from app.tool.search.base import WebSearchEngine


class BaiduSearchEngine(WebSearchEngine):
    def perform_search(self, query, num_results=10, *args, **kwargs):
        """Baidu search engine."""
        return search(query, num_results=num_results)
