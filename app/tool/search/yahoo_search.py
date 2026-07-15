from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from app.logger import logger
from app.tool.search.base import SearchItem, WebSearchEngine


ABSTRACT_MAX_LENGTH = 300

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
]

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "User-Agent": USER_AGENTS[0],
    "Referer": "https://search.yahoo.com/",
    "Accept-Language": "en-US,en;q=0.9",
}


class YahooSearchEngine(WebSearchEngine):
    session: Optional[requests.Session] = None

    def __init__(self, **data):
        super().__init__(**data)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def perform_search(
        self, query: str, num_results: int = 10, *args, **kwargs
    ) -> List[SearchItem]:
        """Yahoo search engine."""
        if not query:
            return []

        list_result = []
        try:
            res = self.session.get(
                url=f"https://search.yahoo.com/search?p={query}", timeout=10
            )
            res.raise_for_status()
            root = BeautifulSoup(res.text, "html.parser")

            for div in root.find_all("div", class_="compTitle"):
                try:
                    title_elem = div.find("h3")
                    if not title_elem:
                        continue

                    a_elem = title_elem.find("a")
                    if not a_elem:
                        continue

                    title = a_elem.text.strip()
                    url = a_elem.get("href", "").strip()

                    # Try to find the abstract by looking at the parent or next sibling
                    abstract = ""
                    parent_li = div.find_parent("li")
                    if parent_li:
                        desc_div = parent_li.find("div", class_="compText")
                        if desc_div:
                            abstract = desc_div.text.strip()

                    if ABSTRACT_MAX_LENGTH and len(abstract) > ABSTRACT_MAX_LENGTH:
                        abstract = abstract[:ABSTRACT_MAX_LENGTH]

                    if title and url:
                        list_result.append(
                            SearchItem(
                                title=title,
                                url=url,
                                description=abstract,
                            )
                        )
                except Exception:
                    continue

                if len(list_result) >= num_results:
                    break

            return list_result
        except Exception as e:
            logger.warning(f"Error parsing Yahoo HTML: {e}")
            return []
