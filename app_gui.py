import gradio as gr
import asyncio
import time
import sys
import io
import os

# Ensure the app module can be found
# This might be needed if app_gui.py is run directly from the root
# and the app directory is not automatically in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from app.agent.data_analysis import DataAnalysis
    from app.agent.manus import Manus
    from app.config import config # This will load the config, including API key
    from app.flow.flow_factory import FlowFactory, FlowType
    from app.logger import logger, define_log_level
except ImportError as e:
    print(f"Error importing application modules: {e}")
    print("Please ensure that the application structure is correct and all dependencies are installed.")
    print("If running from the root, ensure 'config/config.toml' exists or is creatable by the launcher.")
    sys.exit(1)

# Define log level (e.g., "INFO" or "DEBUG")
# This should ideally be configured via config or environment variable
# For now, let's ensure it's called. It might be called by importing logger too.
define_log_level(config.log_level)

# Global variable to ensure asyncio.run is not called recursively if Gradio uses its own loop
# However, for standard Gradio usage where handlers are sync, asyncio.run() is the way.
# If Gradio internally uses an asyncio loop and calls handlers in it, then we'd need
# to get the existing loop. For now, assume standard sync handler.

def run_openmanus_flow(prompt_text: str):
    """
    Handles the Gradio interaction: takes a prompt, runs the OpenManus flow,
    and returns the output.
    """
    logger.info(f"Received prompt from GUI: '{prompt_text[:50]}...'")

    if not prompt_text or not prompt_text.strip():
        logger.warning("Empty prompt received.")
        return "Please enter a prompt."

    # Redirect stdout to capture print statements from the flow
    old_stdout = sys.stdout
    sys.stdout = captured_output_io = io.StringIO()

    status_messages = []
    final_result_text = ""
    full_log_output = ""

    try:
        status_messages.append("Initializing agents and flow...")
        logger.info("Initializing agents and flow for GUI request...")

        # Create agents and flow inside the function for statelessness between calls
        current_agents = {"manus": Manus()}
        if config.run_flow_config.use_data_analysis_agent:
            current_agents["data_analysis"] = DataAnalysis()
            logger.info("DataAnalysis agent enabled.")
        else:
            logger.info("DataAnalysis agent disabled.")

        current_flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,  # Or allow selection if needed
            agents=current_agents
        )
        logger.info(f"Flow type '{FlowType.PLANNING.value}' created.")
        status_messages.append(f"Flow '{FlowType.PLANNING.value}' created. Processing your request...")

        start_time = time.time()

        # Running the async function using asyncio.run()
        # This is suitable if Gradio calls this handler in a separate thread.
        # If Gradio has its own event loop, nest_asyncio might be needed,
        # or using loop.run_until_complete(current_flow.execute(prompt_text)).
        # For simplicity and common Gradio usage, asyncio.run() is the first choice.
        logger.info(f"Executing flow with prompt: {prompt_text}")

        # asyncio.run() cannot be called when another asyncio event loop is running in the same thread.
        # Gradio itself might be running an asyncio event loop.
        # A common pattern for Gradio is to run the async code in a separate thread
        # or use `asyncio.get_event_loop().run_until_complete()`.
        # Let's try with `asyncio.new_event_loop()` and `run_until_complete` for better compatibility.

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            flow_result = loop.run_until_complete(current_flow.execute(prompt_text))
        finally:
            loop.close()
            asyncio.set_event_loop(None) # Clean up

        elapsed_time = time.time() - start_time

        status_messages.append(f"Request processed in {elapsed_time:.2f} seconds.")
        logger.info(f"Request processed in {elapsed_time:.2f} seconds. Result: {flow_result}")

        final_result_text = str(flow_result) if flow_result is not None else "No explicit result returned from flow."

    except asyncio.TimeoutError:
        error_msg = "Error: Request processing timed out."
        status_messages.append(error_msg)
        logger.error(error_msg)
        final_result_text = "Timeout occurred."
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        status_messages.append(error_msg)
        logger.exception(f"An error occurred in GUI flow: {e}")
        final_result_text = f"Error: {e}"
    finally:
        sys.stdout = old_stdout  # Restore stdout
        full_log_output = captured_output_io.getvalue()
        captured_output_io.close()

    # Combine status messages, captured stdout, and final result for display
    combined_output = "# Status\n" + "\n".join(f"- {msg}" for msg in status_messages) + "\n\n"

    if full_log_output:
        combined_output += "## Captured Output (stdout)\n```\n" + full_log_output + "\n```\n\n"

    if final_result_text:
        combined_output += "## Final Result\n" + final_result_text

    logger.info("GUI interaction finished. Returning combined output.")
    return combined_output


if __name__ == "__main__":
    logger.info("Starting Gradio interface for OpenManus AI Agent.")

    iface = gr.Interface(
        fn=run_openmanus_flow,
        inputs=gr.Textbox(
            lines=7,
            label="Your Prompt",
            placeholder="Enter your idea, task, or question for OpenManus...\n\nExample: 'Develop a comprehensive marketing strategy for a new eco-friendly toothbrush brand. Consider online and offline channels, target audience, and key messaging.'"
        ),
        outputs=gr.Markdown(
            label="Output",
            show_copy_button=True,
        ),
        title="OpenManus AI Agent",
        description="""
        Welcome to OpenManus!
        Enter your prompt below to have the AI agent plan and (eventually) execute tasks.
        The output will show status updates, any captured logs, and the final result from the agent's process.
        """,
        allow_flagging='never', # Disable flagging/sharing for local app
        examples=[
            ["Outline a plan to write a short sci-fi story about AI discovering music."],
            ["Suggest three innovative features for a new project management tool."],
            ["What are the key considerations when launching a small e-commerce business?"],
        ]
    )

    # Launch the interface
    # You can specify server_name="0.0.0.0" to make it accessible on your local network
    # share=True would create a public link (requires Gradio account for long-term links)
    print("Launching Gradio interface... Access it at http://127.0.0.1:7860 (or the address shown below)")
    iface.launch()
    logger.info("Gradio interface stopped.")
