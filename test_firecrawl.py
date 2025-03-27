import asyncio
import sys

from app.logger import logger
from app.tool.firecrawl_scrape import FirecrawlScrape


async def test_firecrawl():
    """
    Simple test script to test the Firecrawl integration.
    
    Usage:
        python test_firecrawl.py [url]
        
    If no URL is provided, it will use https://firecrawl.dev as the default.
    """
    # Get URL from command line arguments or use default
    url = sys.argv[1] if len(sys.argv) > 1 else "https://firecrawl.dev"
    
    logger.info(f"Testing Firecrawl scrape with URL: {url}")
    
    # Create the tool
    firecrawl_tool = FirecrawlScrape()
    
    try:
        # Execute the tool
        result = await firecrawl_tool.execute(
            url=url,
            formats=["markdown"],
        )
        
        # Print the result
        logger.info("Scrape successful!")
        logger.info(f"Result formats: {list(result.keys())}")
        
        # Print a preview of the markdown content
        if "markdown" in result:
            markdown_content = result["markdown"]
            preview_length = min(500, len(markdown_content))
            logger.info(f"Markdown content preview (first {preview_length} chars):")
            logger.info(markdown_content[:preview_length] + "...")
        
        return True
    except Exception as e:
        logger.error(f"Error testing Firecrawl scrape: {str(e)}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_firecrawl())
    sys.exit(0 if success else 1) 