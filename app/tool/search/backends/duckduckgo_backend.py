"""
DuckDuckGo backend implementation with HTTP/2 support.
"""

import json
import re
from typing import Any, Dict, List

import httpx

from app.logger import logger
from app.tool.search.backends.base import ModernSearchBackend, StructuredSearchResult


class DuckDuckGoBackend(ModernSearchBackend):
    """DuckDuckGo backend with modern HTTP/2 support."""
    
    BASE_URL = "https://duckduckgo.com/html/"
    INSTANT_ANSWERS_URL = "https://api.duckduckgo.com/"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # DuckDuckGo doesn't require API key for basic search
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        lang: str = "en",
        country: str = "us",
        **kwargs
    ) -> List[StructuredSearchResult]:
        """Search using DuckDuckGo with HTTP/2."""
        results = []
        
        # Try instant answers first (structured data)
        try:
            instant_results = await self._search_instant_answers(query, lang)
            results.extend(instant_results)
        except Exception as e:
            logger.debug(f"DuckDuckGo instant answers failed: {e}")
        
        # Then get regular web results
        try:
            web_results = await self._search_web(query, num_results, lang, country)
            results.extend(web_results)
        except Exception as e:
            logger.error(f"DuckDuckGo web search failed: {e}")
        
        # Limit results to requested number
        results = results[:num_results]
        
        logger.info(f"DuckDuckGo returned {len(results)} results for query: {query}")
        return results
    
    async def _search_instant_answers(self, query: str, lang: str) -> List[StructuredSearchResult]:
        """Search DuckDuckGo instant answers API."""
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }
        
        if lang != "en":
            params["kl"] = f"{lang}-{lang.upper()}"
        
        response = await self._make_request("GET", self.INSTANT_ANSWERS_URL, params=params)
        return self._parse_instant_answers_response(response, query)
    
    def _parse_response(
        self, 
        response: httpx.Response, 
        query: str, 
        num_results: int
    ) -> List[StructuredSearchResult]:
        """Parse DuckDuckGo response (abstract method implementation)."""
        # For DuckDuckGo, we primarily use instant answers and web parsing
        # This method is called by the base class but we handle parsing differently
        return []
    
    async def _search_web(
        self, 
        query: str, 
        num_results: int, 
        lang: str, 
        country: str
    ) -> List[StructuredSearchResult]:
        """Search DuckDuckGo web results."""
        params = {
            "q": query,
            "kl": f"{lang}-{country.upper()}" if lang != "en" else "us-en",
        }
        
        # Use custom headers to avoid being blocked
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": f"{lang}-{country.upper()},{lang};q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        response = await self._make_request("GET", self.BASE_URL, params=params, headers=headers)
        return self._parse_web_response(response, query, num_results)
    
    def _parse_instant_answers_response(
        self, 
        response: httpx.Response, 
        query: str
    ) -> List[StructuredSearchResult]:
        """Parse instant answers response."""
        try:
            data = response.json()
            results = []
            
            # Abstract (instant answer)
            if data.get("Abstract"):
                results.append(StructuredSearchResult(
                    position=1,
                    url=data.get("AbstractURL", ""),
                    title=data.get("AbstractSource", "Instant Answer"),
                    description=data.get("Abstract", ""),
                    source=self.name,
                    structured_data={"instant_answer": data},
                    rich_snippet=data.get("Abstract"),
                    result_type="instant_answer",
                    relevance_score=1.0,
                    cache_key=f"ddg:instant:{query}",
                    query_hash=self._hash_query(query),
                ))
            
            # Answer (direct answer)
            if data.get("Answer"):
                results.append(StructuredSearchResult(
                    position=len(results) + 1,
                    url=data.get("AbstractURL", ""),
                    title="Direct Answer",
                    description=data.get("Answer", ""),
                    source=self.name,
                    structured_data={"direct_answer": data},
                    rich_snippet=data.get("Answer"),
                    result_type="direct_answer",
                    relevance_score=0.95,
                    cache_key=f"ddg:answer:{query}",
                    query_hash=self._hash_query(query),
                ))
            
            # Definition
            if data.get("Definition"):
                results.append(StructuredSearchResult(
                    position=len(results) + 1,
                    url=data.get("DefinitionURL", ""),
                    title=data.get("DefinitionSource", "Definition"),
                    description=data.get("Definition", ""),
                    source=self.name,
                    structured_data={"definition": data},
                    rich_snippet=data.get("Definition"),
                    result_type="definition",
                    relevance_score=0.9,
                    cache_key=f"ddg:def:{query}",
                    query_hash=self._hash_query(query),
                ))
            
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse DuckDuckGo instant answers JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing DuckDuckGo instant answers: {e}")
            return []
    
    def _parse_web_response(
        self, 
        response: httpx.Response, 
        query: str, 
        num_results: int
    ) -> List[StructuredSearchResult]:
        """Parse HTML web response."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Find result divs
            result_divs = soup.find_all('div', class_='result')
            
            for i, div in enumerate(result_divs[:num_results]):
                result = self._parse_web_result_div(div, query, i)
                if result:
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error parsing DuckDuckGo HTML response: {e}")
            return []
    
    def _parse_web_result_div(
        self, 
        div, 
        query: str, 
        position: int
    ) -> StructuredSearchResult:
        """Parse a single web result div."""
        try:
            # Extract title and URL
            title_link = div.find('a', class_='result__a')
            if not title_link:
                return None
            
            title = title_link.get_text(strip=True)
            url = title_link.get('href', '')
            
            # Clean DuckDuckGo redirect URLs
            if url.startswith('/l/?uddg='):
                import urllib.parse
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                url = parsed.get('uddg', [''])[0]
            
            # Extract description
            snippet_div = div.find('a', class_='result__snippet')
            description = snippet_div.get_text(strip=True) if snippet_div else ""
            
            # Extract structured data if available
            structured_data = {}
            
            # Look for favicon or site info
            favicon = div.find('img', class_='result__icon')
            if favicon and favicon.get('src'):
                structured_data["favicon"] = favicon["src"]
            
            return StructuredSearchResult(
                position=position + 1,
                url=url,
                title=title,
                description=description,
                source=self.name,
                structured_data=structured_data if structured_data else None,
                result_type="web",
                cache_key=f"ddg:web:{url}",
                query_hash=self._hash_query(query),
            )
            
        except Exception as e:
            logger.debug(f"Error parsing DuckDuckGo result div: {e}")
            return None
    
    def _hash_query(self, query: str) -> str:
        """Create a simple hash for the query."""
        import hashlib
        return hashlib.md5(query.encode()).hexdigest()[:16]