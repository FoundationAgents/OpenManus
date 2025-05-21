from A2A.common.server import A2AServer
from A2A.common.types import AgentCard, AgentCapabilities, AgentSkill, MissingAPIKeyError
from A2A.common.utils.push_notification_auth import PushNotificationSenderAuth
from A2A.Manus.task_manager import AgentTaskManager
from A2A.Manus.agent import A2AManus
from app.tool.browser_use_tool import _BROWSER_DESCRIPTION
from app.tool.str_replace_editor import _STR_REPLACE_EDITOR_DESCRIPTION
from app.tool.terminate import _TERMINATE_DESCRIPTION
import click
import os
import logging
from dotenv import load_dotenv
import asyncio
from typing import Optional

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main(host:str = "localhost", port:int = 10000):
    """Starts the Manus Agent server."""
    try:
        capabilities = AgentCapabilities(streaming=False, pushNotifications=True)
        skills=[
            AgentSkill(
            id="Python Execute",
            name="Python Execute Tool",
            description="Executes Python code string. Note: Only print outputs are visible, function return values are not captured. Use print statements to see results.",
            tags=["Execute Python Code"],
            examples=["Execute Python code:'''python \n Print('Hello World') \n '''"],
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
            )
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

        notification_sender_auth = PushNotificationSenderAuth()
        notification_sender_auth.generate_jwk()
        server = A2AServer(
            agent_card=agent_card,
            task_manager=AgentTaskManager(
                agent_factory=lambda:A2AManus.create(max_steps=3), notification_sender_auth=notification_sender_auth),
            host=host,
            port=port,
        )

        server.app.add_route(
            "/.well-known/jwks.json", notification_sender_auth.handle_jwks_endpoint, methods=["GET"]
        )

        logger.info(f"Starting server on {host}:{port}")
        return server
    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)

def run_server(host: Optional[str] = "localhost", port: Optional[int] = 10000):
    try:
        import uvicorn
        server = asyncio.run(main(host, port))
        config = uvicorn.Config(app=server.app, host=host, port=port, loop="asyncio", proxy_headers=True)
        uvicorn.Server(config=config).run()
        logger.info(f"Server started on {host}:{port}")
    except Exception as e:
        logger.error(f"An error occurred while starting the server: {e}")
if __name__ == "__main__":
    import sys
    host = "localhost"  # 默认值
    port = 10000        # 默认值
    for i in range(1, len(sys.argv)):
        if sys.argv[i] == "--host":
            host = sys.argv[i + 1]
        elif sys.argv[i] == "--port":
            port = int(sys.argv[i + 1])
    run_server(host, port)
