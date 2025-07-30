import argparse
import asyncio
import logging
from typing import Optional

import httpx
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from dotenv import load_dotenv

from app.tool.browser_use_tool import _BROWSER_DESCRIPTION
from app.tool.str_replace_editor import _STR_REPLACE_EDITOR_DESCRIPTION
from app.tool.terminate import _TERMINATE_DESCRIPTION

from .agent import A2AManus
from .agent_executor import ManusExecutor


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main(host: str = "localhost", port: int = 10000):
    """Starts the Manus Agent server."""
    try:
        capabilities = AgentCapabilities(streaming=False, pushNotifications=True)
        skills = [
            AgentSkill(
                id="Python Execute",
                name="Python Execute Tool",
                description="Executes Python code string. Note: Only print outputs are visible, function return values are not captured. Use print statements to see results.",
                tags=["Execute Python Code"],
                examples=[
                    "Execute Python code:'''python \n Print('Hello World') \n '''"
                ],
            ),
            AgentSkill(
                id="Browser use",
                name="Browser use Tool",
                description=_BROWSER_DESCRIPTION,
                tags=["Use Browser"],
                examples=["go_to 'https://www.google.com'"],
            ),
            AgentSkill(
                id="Replace String",
                name="Str_replace Tool",
                description=_STR_REPLACE_EDITOR_DESCRIPTION,
                tags=["Operate Files"],
                examples=["Replace 'old' with 'new' in 'file.txt'"],
            ),
            AgentSkill(
                id="Ask human",
                name="Ask human Tool",
                description="Use this tool to ask human for help.",
                tags=["Ask human for help"],
                examples=["Ask human: 'What time is it?'"],
            ),
            AgentSkill(
                id="terminate",
                name="terminate Tool",
                description=_TERMINATE_DESCRIPTION,
                tags=["terminate task"],
                examples=["terminate"],
            ),
            # Add more skills as needed
        ]

        agent_card = AgentCard(
            name="Manus Agent",
            description="A versatile agent that can solve various tasks using multiple tools including MCP-based tools",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            defaultInputModes=A2AManus.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=A2AManus.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=skills,
        )

        httpx_client = httpx.AsyncClient()
        request_handler = DefaultRequestHandler(
            agent_executor=ManusExecutor(
                agent_factory=lambda: A2AManus.create(max_steps=3)
            ),
            task_store=InMemoryTaskStore(),
            push_notifier=InMemoryPushNotifier(httpx_client),
        )

        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        logger.info(f"Starting server on {host}:{port}")
        return server.build()
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


def run_server(host: Optional[str] = "localhost", port: Optional[int] = 10000):
    try:
        import uvicorn

        app = asyncio.run(main(host, port))
        config = uvicorn.Config(
            app=app, host=host, port=port, loop="asyncio", proxy_headers=True
        )
        uvicorn.Server(config=config).run()
        logger.info(f"Server started on {host}:{port}")
    except Exception as e:
        logger.error(f"An error occurred while starting the server: {e}")


if __name__ == "__main__":
    # Parse command line arguments for host and port, with default values
    parser = argparse.ArgumentParser(description="Start Manus Agent service")
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Server host address, default is localhost",
    )
    parser.add_argument(
        "--port", type=int, default=10000, help="Server port, default is 10000"
    )
    args = parser.parse_args()
    # Start the server with the specified or default host and port
    run_server(args.host, args.port)
