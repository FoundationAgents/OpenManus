import argparse
import asyncio

from app.logger import logger


async def main():
    """Placeholder entry point.

    The CLI no longer instantiates or runs agents directly. Use the library
    APIs or dedicated launcher scripts to start agents or services.
    """

    parser = argparse.ArgumentParser(
        description="OpenManus entry point (agent execution disabled)"
    )
    parser.add_argument("--prompt", type=str, required=False, help="No-op placeholder")
    _ = parser.parse_args()

    logger.info(
        "OpenManus CLI placeholder: agent execution is intentionally disabled in"
        " this entry script."
    )


if __name__ == "__main__":
    asyncio.run(main())
