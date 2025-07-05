import argparse
import asyncio

from app.agent.manus import Manus
from app.logger import logger
from app.config import config
from app.i18n import initialize_i18n_from_config, msg, err
from app.rule import apply_rules_to_prompt, validate_rule_configuration


async def main():
    # Initialize internationalization from configuration
    initialize_i18n_from_config(config)

    # Validate rule configuration if enabled
    is_valid, error_msg = validate_rule_configuration()
    if not is_valid:
        logger.warning(f"Rule configuration issue: {error_msg}")

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
        prompt = args.prompt if args.prompt else input(msg("enter_prompt"))
        if not prompt.strip():
            logger.warning(msg("empty_prompt"))
            return

        # Apply rules to the prompt if rule system is enabled
        final_prompt = apply_rules_to_prompt(prompt)
        if final_prompt != prompt:
            logger.info("Rules applied to user prompt")

        logger.warning(msg("processing"))
        await agent.run(final_prompt)
        logger.info(msg("completed"))
    except KeyboardInterrupt:
        logger.warning(msg("interrupted"))
    finally:
        # Ensure agent resources are cleaned up before exiting
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
