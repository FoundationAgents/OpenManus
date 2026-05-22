import urllib.parse
from typing import List


try:
    from cloakbrowser import launch as cloak_launch
except Exception:  # pragma: no cover - optional dependency runtime probe
    cloak_launch = None

from playwright.sync_api import sync_playwright

from app.logger import logger
from app.tool.search.base import SearchItem, WebSearchEngine


ABSTRACT_MAX_LENGTH = 300


class BingSearchEngine(WebSearchEngine):
    def _search_with_cloakbrowser(
        self, query: str, num_results: int
    ) -> List[SearchItem]:
        if cloak_launch is None:
            return []
        list_result: List[SearchItem] = []
        browser = None
        try:
            browser = cloak_launch(humanize=True)
            page = browser.new_page()
            encoded_query = urllib.parse.quote(query)
            # Force English results regardless of container IP geolocation
            page.goto(f"https://www.bing.com/search?q={encoded_query}&setlang=en&cc=US&mkt=en-US")
            try:
                page.wait_for_selector("li.b_algo", timeout=8000)
            except Exception:
                pass
            results = page.query_selector_all("li.b_algo")
            for r in results:
                if len(list_result) >= num_results:
                    break
                try:
                    a = r.query_selector("h2 a")
                    desc = r.query_selector("p")
                    if not a:
                        continue
                    title = a.text_content().strip() if a.text_content() else ""
                    url = a.get_attribute("href") or ""
                    abstract = (
                        desc.text_content().strip()
                        if desc and desc.text_content()
                        else ""
                    )
                    if ABSTRACT_MAX_LENGTH and len(abstract) > ABSTRACT_MAX_LENGTH:
                        abstract = abstract[:ABSTRACT_MAX_LENGTH]
                    if title and url:
                        list_result.append(
                            SearchItem(title=title, url=url, description=abstract)
                        )
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Error performing Bing CloakBrowser search: {e}")
            return []
        finally:
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
        return list_result

    def perform_search(
        self, query: str, num_results: int = 10, *args, **kwargs
    ) -> List[SearchItem]:
        """
        Bing search engine using Playwright to bypass scraping blocks.
        """
        if not query:
            return []

        # Prefer CloakBrowser when available, fallback to Playwright.
        cloak_results = self._search_with_cloakbrowser(query, num_results)
        if cloak_results:
            return cloak_results

        list_result: List[SearchItem] = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                # Create context with a realistic user agent
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()

                # Load search page — force English results regardless of container IP
                encoded_query = urllib.parse.quote(query)
                page.goto(f"https://www.bing.com/search?q={encoded_query}&setlang=en&cc=US&mkt=en-US")

                # Wait for results or timeout
                try:
                    page.wait_for_selector("li.b_algo", timeout=8000)
                except Exception:
                    pass  # Continue even if no selector, maybe there are no results

                results = page.query_selector_all("li.b_algo")

                for r in results:
                    if len(list_result) >= num_results:
                        break

                    try:
                        a = r.query_selector("h2 a")
                        desc = r.query_selector("p")

                        if not a:
                            continue

                        title = a.text_content().strip() if a.text_content() else ""
                        url = a.get_attribute("href") or ""
                        abstract = (
                            desc.text_content().strip()
                            if desc and desc.text_content()
                            else ""
                        )

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

                browser.close()
        except Exception as e:
            logger.warning(f"Error performing Bing Playwright search: {e}")

        return list_result
