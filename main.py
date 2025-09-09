import argparse
import asyncio
import os
from pathlib import Path

from app.agent.manus import Manus
from app.logger import logger


def load_prompt_from_file(file_path: str) -> str:
    """Load prompt content from a file."""
    try:
        # Convert to absolute path if it's relative
        if not os.path.isabs(file_path):
            # Make path relative to the current working directory
            file_path = os.path.join(os.getcwd(), file_path)

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            raise ValueError(f"File is empty: {file_path}")

        logger.info(f"Successfully loaded prompt from file: {file_path}")
        return content

    except Exception as e:
        logger.error(f"Failed to load prompt from file '{file_path}': {e}")
        raise


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run Manus agent with a prompt")
    parser.add_argument(
        "--prompt",
        type=str,
        required=False,
        help="Input prompt for the agent. Use 'file:path/to/file' to load prompt from a file.",
    )
    args = parser.parse_args()

    # Create and initialize Manus agent
    agent = await Manus.create()
    try:
        # Use command line prompt if provided, otherwise ask for input
        prompt_input = args.prompt if args.prompt else input("Enter your prompt (or file:path/to/file): ")
        if not prompt_input.strip():
            logger.warning("Empty prompt provided.")
            return

        # Check if prompt starts with 'file:' prefix
        if prompt_input.startswith("file:"):
            file_path = prompt_input[5:]  # Remove 'file:' prefix
            prompt = load_prompt_from_file(file_path)
        else:
            prompt = prompt_input

        logger.warning("Processing your request...")
        await agent.run(prompt)
        logger.info("Request processing completed.")
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
    except Exception as e:
        logger.error(f"Error processing request: {e}")
    finally:
        # Ensure agent resources are cleaned up before exiting
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
