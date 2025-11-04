import argparse
import asyncio
import os
import time
from pathlib import Path

from app.agent.data_analysis import DataAnalysis
from app.agent.manus import Manus
from app.config import config
from app.flow.flow_factory import FlowFactory, FlowType
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


async def run_flow():
    agents = {
        "manus": Manus(),
    }
    if config.run_flow_config.use_data_analysis_agent:
        agents["data_analysis"] = DataAnalysis()
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Run flow with prompt template")
        parser.add_argument(
            "--prompt",
            type=str,
            required=False,
            help="Input prompt for the flow. Use 'file:path/to/file' to load prompt from a file.",
        )
        args = parser.parse_args()

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

        if prompt.strip().isspace() or not prompt:
            logger.warning("Empty prompt provided.")
            return

        flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,
            agents=agents,
        )
        logger.warning("Processing your request...")

        try:
            start_time = time.time()
            result = await asyncio.wait_for(
                flow.execute(prompt),
                timeout=3600,  # 60 minute timeout for the entire execution
            )
            elapsed_time = time.time() - start_time
            logger.info(f"Request processed in {elapsed_time:.2f} seconds")
            logger.info(result)
        except asyncio.TimeoutError:
            logger.error("Request processing timed out after 1 hour")
            logger.info("Operation terminated due to timeout. Please try a simpler request.")

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(run_flow())
