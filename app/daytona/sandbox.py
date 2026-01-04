import time
from typing import Optional

from daytona import (
    CreateSandboxFromImageParams,
    Daytona,
    DaytonaConfig,
    Resources,
    Sandbox,
    SandboxState,
    SessionExecuteRequest,
)

from app.config import config
from app.utils.logger import logger


daytona_settings = config.daytona
daytona: Optional[Daytona] = None
daytona_config: Optional[DaytonaConfig] = None

if daytona_settings.use_daytona:
    logger.info("Daytona is enabled. Initializing Daytona sandbox configuration.")

    if not daytona_settings.daytona_api_key:
        logger.error(
            "Daytona is enabled, but no Daytona API key is configured. Daytona features will be unavailable."
        )
    else:
        daytona_config = DaytonaConfig(
            api_key=daytona_settings.daytona_api_key,
            server_url=daytona_settings.daytona_server_url,
            target=daytona_settings.daytona_target,
        )
        logger.info("Daytona API key configured successfully")
        if daytona_config.server_url:
            logger.info(f"Daytona server URL set to: {daytona_config.server_url}")
        if daytona_config.target:
            logger.info(f"Daytona target set to: {daytona_config.target}")

        daytona = Daytona(daytona_config)
        logger.info("Daytona client initialized")
else:
    logger.info("Daytona is disabled. Skipping Daytona client initialization.")


async def get_or_start_sandbox(sandbox_id: str):
    """Retrieve a sandbox by ID, check its state, and start it if needed."""
    if not daytona:
        logger.warning("Daytona is not enabled. Cannot get or start sandbox.")
        return None

    logger.info(f"Getting or starting sandbox with ID: {sandbox_id}")

    try:
        sandbox = daytona.get(sandbox_id)

        # Check if sandbox needs to be started
        if (
            sandbox.state == SandboxState.ARCHIVED
            or sandbox.state == SandboxState.STOPPED
        ):
            logger.info(f"Sandbox is in {sandbox.state} state. Starting...")
            try:
                daytona.start(sandbox)
                # Wait a moment for the sandbox to initialize
                # sleep(5)
                # Refresh sandbox state after starting
                sandbox = daytona.get(sandbox_id)

                # Start supervisord in a session when restarting
                start_supervisord_session(sandbox)
            except Exception as e:
                logger.error(f"Error starting sandbox: {e}")
                raise e

        logger.info(f"Sandbox {sandbox_id} is ready")
        return sandbox

    except Exception as e:
        logger.error(f"Error retrieving or starting sandbox: {str(e)}")
        raise e


def start_supervisord_session(sandbox: Sandbox):
    """Start supervisord in a session."""
    if not daytona:
        logger.warning("Daytona is not enabled. Cannot start supervisord session.")
        return

    session_id = "supervisord-session"
    try:
        logger.info(f"Creating session {session_id} for supervisord")
        sandbox.process.create_session(session_id)

        # Execute supervisord command
        sandbox.process.execute_session_command(
            session_id,
            SessionExecuteRequest(
                command="exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf",
                var_async=True,
            ),
        )
        time.sleep(25)  # Wait a bit to ensure supervisord starts properly
        logger.info(f"Supervisord started in session {session_id}")
    except Exception as e:
        logger.error(f"Error starting supervisord session: {str(e)}")
        raise e


def create_sandbox(password: str, project_id: str = None):
    """Create a new sandbox with all required services configured and running."""
    if not daytona:
        logger.warning("Daytona is not enabled. Cannot create sandbox.")
        return None

    logger.info("Creating new Daytona sandbox environment")
    logger.info("Configuring sandbox with browser-use image and environment variables")

    labels = None
    if project_id:
        logger.info(f"Using sandbox_id as label: {project_id}")
        labels = {"id": project_id}

    params = CreateSandboxFromImageParams(
        image=daytona_settings.sandbox_image_name,
        public=True,
        labels=labels,
        env_vars={
            "CHROME_PERSISTENT_SESSION": "true",
            "RESOLUTION": "1024x768x24",
            "RESOLUTION_WIDTH": "1024",
            "RESOLUTION_HEIGHT": "768",
            "VNC_PASSWORD": password,
            "ANONYMIZED_TELEMETRY": "false",
            "CHROME_PATH": "",
            "CHROME_USER_DATA": "",
            "CHROME_DEBUGGING_PORT": "9222",
            "CHROME_DEBUGGING_HOST": "localhost",
            "CHROME_CDP": "",
        },
        resources=Resources(
            cpu=2,
            memory=4,
            disk=5,
        ),
        auto_stop_interval=15,
        auto_archive_interval=24 * 60,
    )

    # Create the sandbox
    sandbox = daytona.create(params)
    logger.info(f"Sandbox created with ID: {sandbox.id}")

    # Start supervisord in a session for new sandbox
    start_supervisord_session(sandbox)

    logger.info(f"Sandbox environment successfully initialized")
    return sandbox


async def delete_sandbox(sandbox_id: str):
    """Delete a sandbox by its ID."""
    if not daytona:
        logger.warning("Daytona is not enabled. Cannot delete sandbox.")
        return False

    logger.info(f"Deleting sandbox with ID: {sandbox_id}")

    try:
        # Get the sandbox
        sandbox = daytona.get(sandbox_id)

        # Delete the sandbox
        daytona.delete(sandbox)

        logger.info(f"Successfully deleted sandbox {sandbox_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting sandbox {sandbox_id}: {str(e)}")
        raise e
