"""
This example demonstrates how to create a session with context synchronization in AgentBay.
"""

import os
import time
from typing import Dict, Optional

from agentbay import AgentBay
from agentbay.context_sync import ContextSync, SyncPolicy
from agentbay.session_params import CreateSessionParams, BrowserContext
from agentbay.api.models import ExtraConfigs, MobileExtraConfig, AppManagerRule


def create_session_with_default_params() -> None:
    """Create a session with default parameters."""
    # Initialize the AgentBay client
    api_key = os.environ.get("AGENTBAY_API_KEY", "")
    agent_bay = AgentBay(api_key=api_key)

    # Create a session with default parameters
    result = agent_bay.create()

    if result.success and result.session:
        session = result.session
        print(f"Session created successfully with ID: {session.session_id}")
        print(f"Request ID: {result.request_id}")

        # Clean up
        delete_result = agent_bay.delete(session)
        if delete_result.success:
            print("Session deleted successfully")
        else:
            print(f"Failed to delete session: {delete_result.error_message}")
    else:
        print(f"Failed to create session: {result.error_message}")


def create_session_with_labels() -> None:
    """Create a session with labels."""
    # Initialize the AgentBay client
    api_key = os.environ.get("AGENTBAY_API_KEY", "")
    agent_bay = AgentBay(api_key=api_key)

    # Define labels
    labels: Dict[str, str] = {
        "environment": "development",
        "project": "example",
        "owner": "user123"
    }

    # Create session parameters with labels
    params = CreateSessionParams(labels=labels)

    # Create a session with the parameters
    result = agent_bay.create(params)

    if result.success and result.session:
        session = result.session
        print(f"Session with labels created successfully with ID: {session.session_id}")
        print(f"Request ID: {result.request_id}")

        # Verify the labels were set
        label_result = session.get_labels()
        if label_result.success:
            retrieved_labels = label_result.data
            print("Retrieved labels:")
            for key, value in retrieved_labels.items():
                print(f"  {key}: {value}")

        # Clean up
        delete_result = agent_bay.delete(session)
        if delete_result.success:
            print("Session deleted successfully")
        else:
            print(f"Failed to delete session: {delete_result.error_message}")
    else:
        print(f"Failed to create session with labels: {result.error_message}")


def create_session_with_context() -> None:
    """Create a session with context synchronization."""
    # Initialize the AgentBay client
    api_key = os.environ.get("AGENTBAY_API_KEY", "")
    agent_bay = AgentBay(api_key=api_key)

    # Create or get a persistent context
    context_result = agent_bay.context.get("example-context", create=True)

    if context_result.success and context_result.context:
        context = context_result.context
        print(f"Using context with ID: {context.id}")

        # Create a session with context synchronization
        context_sync = ContextSync.new(
            context_id=context.id,
            path="/tmp/data",
            policy=SyncPolicy.default()
        )
        session_params = CreateSessionParams()
        session_params.context_syncs = [context_sync]
        session_result = agent_bay.create(session_params)

        if session_result.success and session_result.session:
            session = session_result.session
            print(f"Session with context created successfully with ID: {session.session_id}")
            print(f"Request ID: {session_result.request_id}")

            # Clean up
            delete_result = agent_bay.delete(session)
            if delete_result.success:
                print("Session deleted successfully")
            else:
                print(f"Failed to delete session: {delete_result.error_message}")
        else:
            print(f"Failed to create session with context: {session_result.error_message}")
    else:
        print(f"Failed to get or create context: {context_result.error_message}")


def create_session_with_context_sync() -> None:
    """Create a session with context synchronization."""
    # Initialize the AgentBay client
    api_key = os.environ.get("AGENTBAY_API_KEY", "")
    agent_bay = AgentBay(api_key=api_key)

    # Create or get a persistent context
    context_result = agent_bay.context.get("example-sync-context", create=True)

    if context_result.success and context_result.context:
        context = context_result.context
        print(f"Using context with ID: {context.id}")

        # Create a context sync configuration with default policy
        context_sync = ContextSync.new(
            context_id=context.id,
            path="/mnt/persistent",
            policy=SyncPolicy.default()
        )

        # Create a session with context synchronization
        session_params = CreateSessionParams()
        session_params.context_syncs = [context_sync]
        session_result = agent_bay.create(session_params)

        if session_result.success and session_result.session:
            session = session_result.session
            print(f"Session with context sync created successfully with ID: {session.session_id}")
            print(f"Request ID: {session_result.request_id}")

            # List the synchronized contexts
            time.sleep(2)  # Wait for context to be synchronized
            list_result = agent_bay.context.list()
            if list_result.success and list_result.contexts:
                contexts = list_result.contexts
                print(f"Found {len(contexts)} synchronized contexts:")
                for ctx in contexts:
                    print(f"  Context ID: {ctx.id}, Name: {ctx.name}, State: {ctx.state}")

            # Clean up
            delete_result = agent_bay.delete(session)
            if delete_result.success:
                print("Session deleted successfully")
            else:
                print(f"Failed to delete session: {delete_result.error_message}")
        else:
            print(f"Failed to create session with context sync: {session_result.error_message}")
    else:
        print(f"Failed to get or create context: {context_result.error_message}")


def create_session_with_browser_context() -> None:
    """Create a session with browser context for cookie persistence."""
    # Initialize the AgentBay client
    api_key = os.environ.get("AGENTBAY_API_KEY", "")
    agent_bay = AgentBay(api_key=api_key)

    # Create or get a persistent context for browser data
    context_result = agent_bay.context.get("example-browser-context", create=True)

    if context_result.success and context_result.context:
        context = context_result.context
        print(f"Using browser context with ID: {context.id}")

        # Create a Browser Context configuration
        browser_context = BrowserContext(
            context_id=context.id,
            auto_upload=True  # Automatically upload browser data when session ends
        )

        # Create session parameters with Browser Context
        session_params = CreateSessionParams(
            image_id="browser_latest",  # Browser image ID required
            browser_context=browser_context
        )
        session_result = agent_bay.create(session_params)

        if session_result.success and session_result.session:
            session = session_result.session
            print(f"Session with browser context created successfully with ID: {session.session_id}")
            print(f"Request ID: {session_result.request_id}")
            print("Browser context will persist cookies and other browser data across sessions")

            # Clean up with context synchronization (important for browser data)
            delete_result = agent_bay.delete(session, sync_context=True)
            if delete_result.success:
                print("Session deleted successfully with context synchronization")
            else:
                print(f"Failed to delete session: {delete_result.error_message}")
        else:
            print(f"Failed to create session with browser context: {session_result.error_message}")
    else:
        print(f"Failed to get or create browser context")


def create_session_with_mobile_config() -> None:
    """Create a session with mobile configuration for app management and resolution control."""
    # Initialize the AgentBay client
    api_key = os.environ.get("AGENTBAY_API_KEY", "")
    agent_bay = AgentBay(api_key=api_key)

    # Create app whitelist rule
    app_whitelist_rule = AppManagerRule(
        rule_type="White",
        app_package_name_list=[
            "com.example.allowed.app",
            "com.company.trusted.app",
            "com.system.essential.service",
            "com.android.settings"
        ]
    )

    # Configure mobile settings
    mobile_config = MobileExtraConfig(
        lock_resolution=True,  # Lock screen resolution for consistent testing
        app_manager_rule=app_whitelist_rule
    )

    # Create extra configs
    extra_configs = ExtraConfigs(mobile=mobile_config)

    # Create session parameters with mobile configuration
    session_params = CreateSessionParams(
        image_id="mobile_latest",
        labels={
            "project": "mobile-testing",
            "environment": "development",
            "config_type": "whitelist"
        },
        extra_configs=extra_configs
    )

    session_result = agent_bay.create(session_params)

    if session_result.success and session_result.session:
        session = session_result.session
        print(f"Mobile session with whitelist created successfully with ID: {session.session_id}")
        print(f"Request ID: {session_result.request_id}")
        print("Mobile configuration applied:")
        print("- Resolution locked for consistent testing")
        print("- App whitelist enabled with allowed packages:")
        for package in app_whitelist_rule.app_package_name_list or []:
            print(f"  - {package}")

        # Clean up
        delete_result = agent_bay.delete(session)
        if delete_result.success:
            print("Mobile session deleted successfully")
        else:
            print(f"Failed to delete mobile session: {delete_result.error_message}")
    else:
        print(f"Failed to create mobile session: {session_result.error_message}")


def main() -> None:
    """Run all examples."""
    print("1. Creating session with default parameters...")
    create_session_with_default_params()
    print("\n2. Creating session with labels...")
    create_session_with_labels()
    print("\n3. Creating session with context...")
    create_session_with_context()
    print("\n4. Creating session with context synchronization...")
    create_session_with_context_sync()
    print("\n5. Creating session with browser context...")
    create_session_with_browser_context()
    print("\n6. Creating session with mobile configuration (whitelist)...")
    create_session_with_mobile_config()


if __name__ == "__main__":
    main()
