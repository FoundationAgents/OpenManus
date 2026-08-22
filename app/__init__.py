# Python version check: 3.11-3.13
import sys


if sys.version_info < (3, 11) or sys.version_info > (3, 13):
    print(
        "Warning: Unsupported Python version {ver}, please use 3.11-3.13".format(
            ver=".".join(map(str, sys.version_info))
        )
    )


def main():
    """Entry point for the openmanus CLI."""
    import asyncio
    import argparse
    from app.agent.manus import Manus
    from app.logger import logger

    async def _main():
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Run Manus agent with a prompt")
        parser.add_argument(
            "--prompt", type=str, required=False, help="Input prompt for the agent"
        )
        args = parser.parse_args()

        # Create and initialize Manus agent
        agent = await Manus.create()
        try:
            # Use command line prompt if provided, otherwise ask for input
            prompt = args.prompt if args.prompt else input("Enter your prompt: ")
            if not prompt.strip():
                logger.warning("Empty prompt provided.")
                return

            logger.warning("Processing your request...")
            await agent.run(prompt)
            logger.info("Request processing completed.")
        except KeyboardInterrupt:
            logger.warning("Operation interrupted.")
        finally:
            # Ensure agent resources are cleaned up before exiting
            await agent.cleanup()

    asyncio.run(_main())
