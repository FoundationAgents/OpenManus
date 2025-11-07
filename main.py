import argparse
import asyncio
import sys

from app.agent.manus import Manus
from app.config import config
from app.logger import logger
from app.gui import run_gui
from app.webui import web_ui


async def run_cli_mode(prompt: str, mode: str = "chat"):
    """Run the agent in CLI mode."""
    try:
        if mode == "chat":
            agent = await Manus.create()
            try:
                logger.warning(f"Processing your request in {mode} mode...")
                result = await agent.run(prompt)
                logger.info("Request processing completed.")
                print(f"\nAgent Response:\n{result}")
            finally:
                await agent.cleanup()
        elif mode in ["agent_flow", "ade"]:
            from app.flow.flow_factory import FlowFactory, FlowType
            from app.agent.data_analysis import DataAnalysis
            
            agents = {"manus": await Manus.create()}
            if config.run_flow_config.use_data_analysis_agent:
                agents["data_analysis"] = DataAnalysis()
                
            flow = FlowFactory.create_flow(
                flow_type=FlowType.PLANNING,
                agents=agents,
            )
            
            logger.warning(f"Processing your request in {mode} mode...")
            result = await flow.execute(prompt)
            logger.info("Request processing completed.")
            print(f"\nAgent Flow Response:\n{result}")
        else:
            logger.error(f"Unknown mode: {mode}")
            return
            
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
    except Exception as e:
        logger.error(f"Error in {mode} mode: {e}")


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="OpenManus - Advanced Agent Framework")
    parser.add_argument(
        "--prompt", type=str, required=False, help="Input prompt for the agent"
    )
    parser.add_argument(
        "--mode", type=str, choices=["chat", "agent_flow", "ade"], 
        default=config.run_flow_config.default_mode,
        help="Agent mode: chat, agent_flow, or ade"
    )
    parser.add_argument(
        "--gui", action="store_true", help="Launch PyQt6 GUI interface"
    )
    parser.add_argument(
        "--webui", action="store_true", help="Launch Web UI interface"
    )
    parser.add_argument(
        "--webui-host", type=str, default=config.ui.webui_host,
        help=f"Web UI host (default: {config.ui.webui_host})"
    )
    parser.add_argument(
        "--webui-port", type=int, default=config.ui.webui_port,
        help=f"Web UI port (default: {config.ui.webui_port})"
    )
    parser.add_argument(
        "--no-gui", action="store_true", help="Disable GUI even if enabled in config"
    )
    parser.add_argument(
        "--no-webui", action="store_true", help="Disable Web UI even if enabled in config"
    )
    
    args = parser.parse_args()

    # Check for GUI/Web UI modes
    if args.gui:
        if config.ui.enable_gui and not args.no_gui:
            logger.info("Launching PyQt6 GUI...")
            run_gui()
            return
        else:
            logger.warning("GUI is disabled in configuration or via --no-gui flag")
    
    if args.webui:
        if config.ui.enable_webui and not args.no_webui:
            logger.info(f"Launching Web UI on {args.webui_host}:{args.webui_port}...")
            web_ui.run(host=args.webui_host, port=args.webui_port)
            return
        else:
            logger.warning("Web UI is disabled in configuration or via --no-webui flag")

    # Default to CLI mode if no GUI requested
    prompt = args.prompt
    if not prompt:
        try:
            prompt = input("Enter your prompt: ")
        except (EOFError, KeyboardInterrupt):
            logger.info("No prompt provided. Exiting.")
            return
    
    if not prompt.strip():
        logger.warning("Empty prompt provided.")
        return

    await run_cli_mode(prompt, args.mode)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
