import re
import urllib.parse
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from app.logger import logger
from app.tool.search.base import SearchItem, WebSearchEngine


class GooglePatentsSearchEngine(WebSearchEngine):
    """Search engine for Google Patents."""

    def perform_search(
        self, query: str, num_results: int = 5, lang: str = "en", country: str = "us", **kwargs
    ) -> List[SearchItem]:
        """
        Perform a search on Google Patents and return a list of patent results.

        Args:
            query: The search query
            num_results: Number of results to return (max 10)
            lang: Language code for search results
            country: Country code for search results

        Returns:
            List of SearchItem objects with patent information
        """
        try:
            # Format the search URL for Google Patents
            encoded_query = urllib.parse.quote(query)
            url = f"https://patents.google.com/?q={encoded_query}&oq={encoded_query}"

            # Add language parameter if provided
            if lang:
                url += f"&hl={lang}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": f"{lang},{lang}-{country};q=0.9,en-US;q=0.8,en;q=0.7",
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                logger.warning(f"Google Patents search failed with status code {response.status_code}")
                return []

            # Parse the response HTML
            return self._parse_results(response.text, num_results)

        except Exception as e:
            logger.error(f"Google Patents search failed: {e}")
            return []

    def _parse_results(self, html: str, num_results: int) -> List[SearchItem]:
        """
        Parse HTML content from Google Patents and extract patent information.

        Args:
            html: HTML content from Google Patents search page
            num_results: Maximum number of results to return

        Returns:
            List of SearchItem objects with patent information
        """
        results = []
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Find patent result elements
            result_elements = soup.select("search-result, .search-result")

            for element in result_elements[:num_results]:
                try:
                    # Extract patent title
                    title_elem = element.select_one(".patent-title, .result-title")
                    title = title_elem.get_text(strip=True) if title_elem else "Untitled Patent"

                    # Extract patent URL
                    link_elem = element.select_one("a[href]") or title_elem
                    if link_elem and link_elem.has_attr("href"):
                        link = link_elem["href"]
                        if link.startswith("/"):
                            link = f"https://patents.google.com{link}"
                    else:
                        continue  # Skip patents without links

                    # Extract patent description/abstract
                    desc_elem = element.select_one(".patent-result-abstract, .result-abstract")
                    description = desc_elem.get_text(strip=True) if desc_elem else ""

                    # Extract publication info if available
                    pub_info_elem = element.select_one(".publication-info, .result-patent-number")
                    pub_info = pub_info_elem.get_text(strip=True) if pub_info_elem else ""
                    if pub_info:
                        description = f"{pub_info}. {description}"

                    results.append(
                        SearchItem(
                            title=title,
                            url=link,
                            description=description,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse Google Patents result: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to parse Google Patents HTML: {e}")

        return results
