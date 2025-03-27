import asyncio
import os
from typing import Dict, List, Optional, Union, Any

from firecrawl import FirecrawlApp

from app.config import config
from app.tool.base import BaseTool


class FirecrawlScrape(BaseTool):
    name: str = "firecrawl_scrape"
    description: str = """Scrape a website using Firecrawl.
Use this tool when you need to extract content from a webpage, analyze website structure, or gather information from the web.
The tool returns the scraped content in the requested format (markdown, HTML, etc.).
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "(required) The URL of the website to scrape.",
            },
            "formats": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["markdown", "html", "rawHtml", "screenshot", "links", "screenshot@fullPage"],
                },
                "description": "(optional) The formats to return the scraped content in. Default is ['markdown'].",
                "default": ["markdown"],
            },
            "wait_for": {
                "type": "integer",
                "description": "(optional) Time in milliseconds to wait for dynamic content to load. Default is 0.",
                "default": 0,
            },
            "only_main_content": {
                "type": "boolean",
                "description": "(optional) Extract only the main content, filtering out navigation, footers, etc. Default is True.",
                "default": True,
            },
            "mobile": {
                "type": "boolean",
                "description": "(optional) Use mobile viewport. Default is False.",
                "default": False,
            },
            "api_key": {
                "type": "string",
                "description": "(optional) Firecrawl API key. If not provided, will use the one from config or environment variable.",
            },
        },
        "required": ["url"],
    }

    async def execute(
        self,
        url: str,
        formats: List[str] = ["markdown"],
        wait_for: int = 0,
        only_main_content: bool = True,
        mobile: bool = False,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a Firecrawl scrape and return the scraped content.

        Args:
            url (str): The URL of the website to scrape.
            formats (List[str], optional): The formats to return the scraped content in. Default is ['markdown'].
            wait_for (int, optional): Time in milliseconds to wait for dynamic content to load. Default is 0.
            only_main_content (bool, optional): Extract only the main content. Default is True.
            mobile (bool, optional): Use mobile viewport. Default is False.
            api_key (str, optional): Firecrawl API key. If not provided, will use the one from config or environment variable.

        Returns:
            Dict[str, Any]: The scraped content in the requested formats.
        """
        # Get API key from config if not provided
        if api_key is None:
            # Try to get from config.toml directly
            try:
                # Load the config file directly to access non-LLM settings
                from pathlib import Path
                import tomllib
                
                config_path = Path(__file__).resolve().parent.parent.parent / "config" / "config.toml"
                if config_path.exists():
                    with open(config_path, "rb") as f:
                        config_data = tomllib.load(f)
                        api_key = config_data.get("tools", {}).get("firecrawl", {}).get("api_key")
            except Exception:
                # If any error occurs, continue to try environment variable
                pass
            
        # Fall back to environment variable if still not found
        if api_key is None:
            api_key = os.environ.get("FIRECRAWL_API_KEY")
            
        if api_key is None:
            raise ValueError(
                "Firecrawl API key not found. Please provide it as a parameter, "
                "in the config file under [tools.firecrawl].api_key, "
                "or as an environment variable FIRECRAWL_API_KEY."
            )

        # Run the scrape in a thread pool to prevent blocking
        loop = asyncio.get_event_loop()
        
        def scrape():
            app = FirecrawlApp(api_key=api_key)
            params = {
                "formats": formats,
                "waitFor": wait_for,
                "onlyMainContent": only_main_content,
                "mobile": mobile,
            }
            return app.scrape_url(url, params=params)
        
        result = await loop.run_in_executor(None, scrape)
        return result 