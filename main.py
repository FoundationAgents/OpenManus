import argparse
import asyncio

from app.agent.manus import Manus
from app.config import config
from app.logger import logger
from app.skill_manager import skill_manager


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run Manus agent with a prompt")
    parser.add_argument(
        "--prompt", type=str, required=False, help="Input prompt for the agent"
    )
    parser.add_argument(
        "--list-skills",
        action="store_true",
        help="List all available skills",
    )
    args = parser.parse_args()

    # Initialize skill manager
    if config.skills_config.enabled:
        try:
            await skill_manager.initialize(skills_paths=config.skills_config.paths)
            logger.info(
                f"🎯 Skills initialized: {len(skill_manager.get_all_skills())} skills loaded"
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize skills: {e}")
    else:
        logger.info("Skills system is disabled")

    # List skills if requested
    if args.list_skills:
        skills = skill_manager.list_skills()
        print(f"\n📋 Available Skills ({len(skills)}):")
        print("-" * 60)
        for skill in skills:
            print(f"  • {skill['name']}")
            print(f"    {skill['description'][:78]}")
            print()
        return

    # Create and initialize Manus agent
    agent = await Manus.create()
    try:
        # Use command line prompt if provided, otherwise ask for input
        prompt = args.prompt if args.prompt else input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        result = await agent.run(prompt)
        logger.info("Request processing completed.")

        # Log active skills that were used
        if agent.active_skills:
            logger.info(
                f"🎯 Active skills used: {', '.join(agent.list_active_skills())}"
            )
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
    finally:
        # Ensure agent resources are cleaned up before exiting
        await agent.cleanup()
        await skill_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
