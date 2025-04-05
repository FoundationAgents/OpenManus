# cli_main.py - Command Line Interface entry point for OpenManus

import asyncio
from app.agent.manus import Manus
from app.logger import logger
from app.schema import AgentState # Import AgentState if needed for checks

# --- Agent Initialization ---
# We still need the agent instance
agent_instance: Manus | None = None

async def initialize_agent_cli():
    """Initializes the Manus agent for CLI use."""
    global agent_instance
    if agent_instance is None:
        logger.info("Initializing Manus agent for CLI...")
        try:
            agent_instance = Manus()
            agent_instance.state = AgentState.IDLE # Ensure initial state
            logger.info("Manus agent initialized for CLI.")
        except Exception as e:
            logger.error(f"Failed to initialize Manus agent: {e}", exc_info=True)
            print(f"\nFATAL: Failed to initialize Manus agent: {e}\n")
            exit(1)
    # Reset state if agent was left in a non-idle state from previous run (if script is run multiple times)
    elif agent_instance.state != AgentState.IDLE:
         agent_instance.state = AgentState.IDLE
         agent_instance.current_step = 0
         # Decide if memory should be cleared for CLI. Let's clear it for distinct runs.
         agent_instance.memory.clear()
         logger.info("Resetting agent state and memory for new CLI run.")

    return agent_instance

async def cli_loop():
    """Main loop for CLI interaction."""
    agent = await initialize_agent_cli()

    print("\nWelcome to OpenManus CLI!")
    print("Enter your request below. Press Ctrl+C to exit.")

    while True:
        try:
            # Get user input
            prompt = input("Enter your prompt: ")
            if not prompt.strip():
                continue # Ignore empty input

            # Ensure agent is ready (might be redundant if init handles it)
            agent.state = AgentState.IDLE
            agent.current_step = 0
            # Clear memory for each new prompt in CLI for stateless interaction
            agent.memory.clear()
            logger.info("Cleared agent memory for new CLI prompt.")


            print("Agent < Thinking...", end="", flush=True) # Print thinking message without newline

            final_output = ""
            # Stream the agent's response
            async for update in agent.run(request=prompt):
                # Simple streaming: clear previous output (crude) and print new one
                # A more sophisticated CLI might use libraries like 'rich' or handle cursor movements
                # Let's just accumulate and print at the end for cleaner CLI output for now.
                final_output = update # Keep track of the latest full output

            # Print the final accumulated output after streaming finishes, overwrite "Thinking..."
            # Use carriage return \r to move cursor to beginning of line
            print(f"\rAgent < {final_output}         ") # Add spaces to clear previous "Thinking..."

            # Check final state (optional)
            if agent.state == AgentState.FINISHED:
                print("\n✅ Task Finished.")
            elif agent.state == AgentState.ERROR:
                 # Error details should be in the final_output from the agent's run method
                 print("\n❌ An error occurred during execution.")
            elif agent.current_step >= agent.max_steps:
                 print("\n⚠️ Reached maximum steps.")


        except KeyboardInterrupt:
            print("\nExiting OpenManus CLI. Goodbye!")
            break
        except EOFError: # Handle Ctrl+D or end of input stream
             print("\nExiting OpenManus CLI. Goodbye!")
             break
        except Exception as e:
            logger.error(f"An error occurred in the CLI loop: {e}", exc_info=True)
            print(f"\nAn unexpected error occurred: {e}")
            # Decide whether to break or continue after an error
            # break # Let's allow continuing for now

async def main():
    # Initialize agent once before starting the loop
    # await initialize_agent_cli() # Initialization now happens inside the loop start
    await cli_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle Ctrl+C during asyncio.run if needed, though cli_loop handles it internally
        print("\nCLI execution interrupted.")
        pass
