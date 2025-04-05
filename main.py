# main.py - Original Simple CLI Entry Point (Adapted for async generator)

import asyncio

from app.agent.manus import Manus
from app.logger import logger
from app.schema import AgentState # Import needed for state checks if any

# Import sandbox client for direct cleanup if agent lacks a method
from app.sandbox.client import SANDBOX_CLIENT

async def main():
    # Initialize agent - ensure it's fresh for this single run
    logger.info("Initializing Manus agent for CLI run...")
    agent = None # Define agent outside try block for finally clause
    try:
        agent = Manus()
        agent.state = AgentState.IDLE # Ensure initial state
        logger.info("Manus agent initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Manus agent: {e}", exc_info=True)
        print(f"\nFATAL: Failed to initialize Manus agent: {e}\n")
        return # Exit if initialization fails

    try:
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        print("Agent < Thinking...", end="", flush=True)

        final_output = ""
        # Consume the async generator from agent.run
        async for update in agent.run(request=prompt):
            final_output = update # Keep track of the latest full output

        # Print the final result after the generator is exhausted
        # Use \r to move cursor to beginning, add spaces to overwrite "Thinking..."
        print(f"\rAgent Response:\n{final_output}         ")

        logger.info("Request processing completed.")

    except KeyboardInterrupt:
        logger.warning("Operation interrupted by user.")
        print("\nOperation interrupted.")
    except Exception as e:
         logger.error(f"An error occurred during agent execution: {e}", exc_info=True)
         print(f"\nAn error occurred: {e}")
    finally:
        # Attempt to clean up resources only if agent was initialized
        if agent:
            # Check if agent has a specific cleanup method first
            if hasattr(agent, 'cleanup') and callable(agent.cleanup):
                 try:
                     logger.info("Cleaning up agent resources...")
                     await agent.cleanup()
                     logger.info("Agent resources cleaned up.")
                 except Exception as e:
                      logger.error(f"Error during agent cleanup: {e}", exc_info=True)
            else:
                 # Fallback to cleaning up the sandbox directly if agent lacks cleanup
                 try:
                     logger.info("Cleaning up sandbox resources directly...")
                     await SANDBOX_CLIENT.cleanup()
                     logger.info("Sandbox resources cleaned up.")
                 except Exception as e:
                      logger.error(f"Error during direct sandbox cleanup: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Already handled within main's try/except/finally
        pass
    print("\nExiting.")
