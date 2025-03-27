import asyncio
import os

from app.agent.manus import Manus
from app.logger import logger
from app.tool.firecrawl_scrape import FirecrawlScrape


async def firecrawl_example():
    """
    Example demonstrating how to use the Firecrawl scrape tool.
    
    This example shows how to:
    1. Create a Manus agent with the FirecrawlScrape tool
    2. Use the FirecrawlScrape tool directly
    3. Run the agent with a prompt that will use the FirecrawlScrape tool
    """
    # Example 1: Using the tool directly
    logger.info("Example 1: Using the FirecrawlScrape tool directly")
    
    # Create the tool
    firecrawl_tool = FirecrawlScrape()
    
    # Set your API key (or use environment variable)
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    
    # Execute the tool
    try:
        result = await firecrawl_tool.execute(
            url="https://firecrawl.dev",
            formats=["markdown"],
            api_key=api_key
        )
        logger.info(f"Scraped content (first 500 chars): {str(result)[:500]}...")
    except Exception as e:
        logger.error(f"Error using FirecrawlScrape tool directly: {str(e)}")
    
    # Example 2: Using the tool through the Manus agent
    logger.info("\nExample 2: Using the FirecrawlScrape tool through the Manus agent")
    
    # Create the agent
    agent = Manus()
    
    # Run the agent with a prompt that will use the FirecrawlScrape tool
    prompt = "Scrape the Firecrawl website (https://firecrawl.dev) and summarize its main features."
    
    try:
        await agent.run(prompt)
    except Exception as e:
        logger.error(f"Error using FirecrawlScrape tool through Manus agent: {str(e)}")


if __name__ == "__main__":
    asyncio.run(firecrawl_example()) 