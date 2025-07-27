"""
Crawl4AI Web Crawler Tool for OpenManus

This tool integrates Crawl4AI, a high-performance web crawler designed for LLMs and AI agents,
providing fast, precise, and AI-ready data extraction with clean Markdown generation.
"""

import asyncio
from typing import List, Union
from urllib.parse import urlparse

from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class Crawl4aiTool(BaseTool):
    """
    Web crawler tool powered by Crawl4AI.

    Provides clean markdown extraction optimized for AI processing.
    """

    name: str = "crawl4ai"
    description: str = """Web crawler that extracts clean, AI-ready content from web pages.

    Features:
    - Extracts clean markdown content optimized for LLMs
    - Handles JavaScript-heavy sites and dynamic content
    - Supports multiple URLs in a single request
    - Fast and reliable with built-in error handling

    Perfect for content analysis, research, and feeding web content to AI models."""

    parameters: dict = {
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "(required) List of URLs to crawl. Can be a single URL or multiple URLs.",
                "minItems": 1,
            },
            "timeout": {
                "type": "integer",
                "description": "(optional) Timeout in seconds for each URL. Default is 30.",
                "default": 30,
                "minimum": 5,
                "maximum": 120,
            },
            "bypass_cache": {
                "type": "boolean",
                "description": "(optional) Whether to bypass cache and fetch fresh content. Default is false.",
                "default": False,
            },
            "word_count_threshold": {
                "type": "integer",
                "description": "(optional) Minimum word count for content blocks. Default is 10.",
                "default": 10,
                "minimum": 1,
            },
        },
        "required": ["urls"],
    }

    async def execute(
        self,
        urls: Union[str, List[str]],
        timeout: int = 30,
        bypass_cache: bool = False,
        word_count_threshold: int = 10,
    ) -> ToolResult:
        """
        Execute web crawling for the specified URLs.

        Args:
            urls: Single URL string or list of URLs to crawl
            timeout: Timeout in seconds for each URL
            bypass_cache: Whether to bypass cache
            word_count_threshold: Minimum word count for content blocks

        Returns:
            ToolResult with crawl results
        """
        # Normalize URLs to list
        if isinstance(urls, str):
            url_list = [urls]
        else:
            url_list = urls

        # Validate URLs
        valid_urls = []
        for url in url_list:
            if self._is_valid_url(url):
                valid_urls.append(url)
            else:
                logger.warning(f"Invalid URL skipped: {url}")

        if not valid_urls:
            return ToolResult(error="No valid URLs provided")

        try:
            # Import crawl4ai components
            from crawl4ai import (
                AsyncWebCrawler,
                BrowserConfig,
                CacheMode,
                CrawlerRunConfig,
            )

            # Configure browser settings
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
                browser_type="chromium",
                ignore_https_errors=True,
                java_script_enabled=True,
            )

            # Configure crawler settings
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS if bypass_cache else CacheMode.ENABLED,
                word_count_threshold=word_count_threshold,
                process_iframes=True,
                remove_overlay_elements=True,
                excluded_tags=["script", "style"],
                page_timeout=timeout * 1000,  # Convert to milliseconds
                verbose=False,
                wait_until="domcontentloaded",
            )

            results = []
            successful_count = 0
            failed_count = 0

            # Process each URL
            async with AsyncWebCrawler(config=browser_config) as crawler:
                for url in valid_urls:
                    try:
                        logger.info(f"🕷️ Crawling URL: {url}")
                        start_time = asyncio.get_event_loop().time()

                        result = await crawler.arun(url=url, config=run_config)

                        end_time = asyncio.get_event_loop().time()
                        execution_time = end_time - start_time

                        if result.success:
                            # Count words in markdown
                            word_count = 0
                            if hasattr(result, "markdown") and result.markdown:
                                word_count = len(result.markdown.split())

                            # Count links
                            links_count = 0
                            if hasattr(result, "links") and result.links:
                                internal_links = result.links.get("internal", [])
                                external_links = result.links.get("external", [])
                                links_count = len(internal_links) + len(external_links)

                            # Count images
                            images_count = 0
                            if hasattr(result, "media") and result.media:
                                images = result.media.get("images", [])
                                images_count = len(images)

                            results.append(
                                {
                                    "url": url,
                                    "success": True,
                                    "status_code": getattr(result, "status_code", 200),
                                    "title": result.metadata.get("title")
                                    if result.metadata
                                    else None,
                                    "markdown": result.markdown
                                    if hasattr(result, "markdown")
                                    else None,
                                    "word_count": word_count,
                                    "links_count": links_count,
                                    "images_count": images_count,
                                    "execution_time": execution_time,
                                }
                            )
                            successful_count += 1
                            logger.info(
                                f"✅ Successfully crawled {url} in {execution_time:.2f}s"
                            )

                        else:
                            results.append(
                                {
                                    "url": url,
                                    "success": False,
                                    "error_message": getattr(
                                        result, "error_message", "Unknown error"
                                    ),
                                    "execution_time": execution_time,
                                }
                            )
                            failed_count += 1
                            logger.warning(f"❌ Failed to crawl {url}")

                    except Exception as e:
                        error_msg = f"Error crawling {url}: {str(e)}"
                        logger.error(error_msg)
                        results.append(
                            {"url": url, "success": False, "error_message": error_msg}
                        )
                        failed_count += 1

            # Format output
            output_lines = [f"🕷️ Crawl4AI Results Summary:"]
            output_lines.append(f"📊 Total URLs: {len(valid_urls)}")
            output_lines.append(f"✅ Successful: {successful_count}")
            output_lines.append(f"❌ Failed: {failed_count}")
            output_lines.append("")

            for i, result in enumerate(results, 1):
                output_lines.append(f"{i}. {result['url']}")

                if result["success"]:
                    output_lines.append(
                        f"   ✅ Status: Success (HTTP {result.get('status_code', 'N/A')})"
                    )
                    if result.get("title"):
                        output_lines.append(f"   📄 Title: {result['title']}")

                    if result.get("markdown"):
                        # Show first 300 characters of markdown content
                        content_preview = result["markdown"]
                        if len(result["markdown"]) > 300:
                            content_preview += "..."
                        output_lines.append(f"   📝 Content: {content_preview}")

                    output_lines.append(
                        f"   📊 Stats: {result.get('word_count', 0)} words, {result.get('links_count', 0)} links, {result.get('images_count', 0)} images"
                    )

                    if result.get("execution_time"):
                        output_lines.append(
                            f"   ⏱️ Time: {result['execution_time']:.2f}s"
                        )
                else:
                    output_lines.append(f"   ❌ Status: Failed")
                    if result.get("error_message"):
                        output_lines.append(f"   🚫 Error: {result['error_message']}")

                output_lines.append("")

            return ToolResult(output="\n".join(output_lines))

        except ImportError as e:
            error_msg = "Crawl4AI is not installed. Please install it with: pip install crawl4ai"
            logger.error(error_msg)
            return ToolResult(error=error_msg)
        except Exception as e:
            error_msg = f"Crawl4AI execution failed: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)

    def _is_valid_url(self, url: str) -> bool:
        """Validate if a URL is properly formatted."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in [
                "http",
                "https",
            ]
        except Exception:
            return False
