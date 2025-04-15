import asyncio
import re
from typing import ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field

from app.config import config
from app.exceptions import ToolError
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.search.patents import GooglePatentsSearchEngine
from app.tool.web_search import SearchResponse, SearchResult


class PatentSearchResult(BaseModel):
    """Model representing a patent search result"""
    title: str = Field(description="Title of the patent")
    url: str = Field(description="URL to the patent")
    description: str = Field(description="Description or abstract of the patent")
    patent_number: Optional[str] = Field(None, description="Patent publication number if available")
    inventors: Optional[List[str]] = Field(None, description="List of inventors if available")
    filing_date: Optional[str] = Field(None, description="Patent filing date if available")


class PatentSearchResponse(ToolResult):
    """Structured response from the patent search tool"""
    query: str = Field(description="The search query that was executed")
    results: List[PatentSearchResult] = Field(
        default_factory=list, description="List of patent search results"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._format_output()

    def _format_output(self):
        """Format search results as a readable string output"""
        if self.error:
            return

        result_text = [f"Patent search results for '{self.query}':"]

        for i, result in enumerate(self.results, 1):
            # Add title with position number
            title = result.title.strip() or "Untitled Patent"
            result_text.append(f"\n{i}. {title}")

            # Add URL with indentation
            result_text.append(f"   URL: {result.url}")

            # Add patent number if available
            if result.patent_number:
                result_text.append(f"   Patent Number: {result.patent_number}")

            # Add inventors if available
            if result.inventors and len(result.inventors) > 0:
                inventors = ", ".join(result.inventors)
                result_text.append(f"   Inventors: {inventors}")

            # Add filing date if available
            if result.filing_date:
                result_text.append(f"   Filing Date: {result.filing_date}")

            # Add description with indentation
            if result.description:
                description = result.description[:500]
                if len(result.description) > 500:
                    description += "..."
                result_text.append(f"   Description: {description}")

        self.output = "\n".join(result_text)


class PatentSearch(BaseTool):
    """Tool for searching patents on Google Patents"""

    name: str = "patent_search"
    description: str = """
    Search for patents on Google Patents database.
    This tool returns comprehensive patent search results with relevant information including titles,
    URLs, patent numbers, inventors, filing dates, and descriptions/abstracts.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) The search query to submit to Google Patents.",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) The number of patent results to return. Default is 5.",
                "default": 5,
            },
            "lang": {
                "type": "string",
                "description": "(optional) Language code for search results (default: en).",
                "default": "en",
            },
        },
        "required": ["query"],
    }

    search_engine: ClassVar[GooglePatentsSearchEngine] = GooglePatentsSearchEngine()

    async def execute(
        self,
        query: str,
        num_results: int = 5,
        lang: str = "en",
    ) -> PatentSearchResponse:
        """
        Execute a patent search on Google Patents.

        Args:
            query: The search query for patents
            num_results: Number of results to return (default: 5)
            lang: Language code for search results (default: en)

        Returns:
            A structured response containing patent search results
        """
        try:
            # Run the search in a thread pool to prevent blocking
            raw_results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.search_engine.perform_search(
                    query=query,
                    num_results=num_results,
                    lang=lang
                )
            )

            # Convert raw search items to patent search results
            patent_results = []
            for result in raw_results:
                # Parse additional information from description if possible
                patent_number = None
                filing_date = None
                inventors = None

                description = result.description

                # Try to extract patent number from description
                if description:
                    # Common patterns in patent numbers
                    patent_patterns = [
                        r'(US\d+[A-Z]\d*)',  # US patent format
                        r'(EP\d+[A-Z]\d*)',  # European patent format
                        r'(WO\d+/\d+)',      # WIPO patent format
                        r'(CN\d+[A-Z]?)',    # Chinese patent format
                        r'(JP\d+[A-Z]\d*)',  # Japanese patent format
                    ]

                    for pattern in patent_patterns:
                        match = re.search(pattern, description)
                        if match:
                            patent_number = match.group(1)
                            break

                patent_results.append(
                    PatentSearchResult(
                        title=result.title,
                        url=result.url,
                        description=description,
                        patent_number=patent_number,
                        inventors=inventors,
                        filing_date=filing_date
                    )
                )

            return PatentSearchResponse(
                query=query,
                results=patent_results
            )

        except Exception as e:
            logger.error(f"Patent search failed: {str(e)}")
            return PatentSearchResponse(
                query=query,
                error=f"Patent search failed: {str(e)}",
                results=[]
            )
