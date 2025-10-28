import json
import os
from typing import Any, Dict, List

from agentbay import AgentBay
from agentbay.exceptions import AgentBayError
from agentbay.session_params import CreateSessionParams
from agentbay.ui import KeyCode


def main():
    # Get API key from environment variable or use a default value for testing
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        api_key = "akm-xxx"  # Replace with your actual API key

    session = None
    try:
        agent_bay = AgentBay(api_key=api_key)

        # Create a new session with default parameters
        print("\nCreating a new mobile session...")
        params = CreateSessionParams(
            image_id="mobile_latest",
        )
        session_result = agent_bay.create(params)
        session = session_result.session
        print(f"Session created with ID: {session.session_id}")
        print(f"Request ID: {session_result.request_id}")

        # Get installed applications
        print("\nGetting installed applications...")
        apps_result = session.mobile.get_installed_apps(
            start_menu=True, desktop=False, ignore_system_apps=True
        )

        if apps_result.success:
            print(f"\nInstalled Applications: {apps_result.data}")
            print(f"Request ID: {apps_result.request_id}")
        else:
            print(f"Error getting applications: {apps_result.error_message}")

        # Start the application
        print(f"\nStarting the application...")
        start_result = session.mobile.start_app(
            "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1"
        )
        print(f"Started Application successfully: {start_result.success}")
        print(f"Request ID: {start_result.request_id}")

        # Stop the application
        print("\nStopping the application...")
        stop_result = session.mobile.stop_app_by_cmd(
            "am force-stop com.sankuai.meituan"
        )
        print(f"Application stopped: {stop_result.success}")
        print(f"Request ID: {stop_result.request_id}")

        # Get clickable ui elements
        print("\nGetting clickable UI elements...")
        elements_result = session.mobile.get_clickable_ui_elements()
        if elements_result.success:
            print(f"Clickable UI Elements: {elements_result.elements}")
            print(f"Request ID: {elements_result.request_id}")
        else:
            print(f"Error getting clickable elements: {elements_result.error_message}")

        # Get all ui elements
        print("\nGetting all UI elements...")

        def print_ui_element(element: Dict[str, Any], indent: int = 1):
            prefix = "  " * indent
            print(f"{prefix}- {element['className']} ",
                  f"(text: '{element['text']}'",
                  f"resourceId: '{element['resourceId']}')"
            )

            children = element.get("children", [])
            for child in children:
                print_ui_element(child, indent + 1)

        def print_all_ui_elements(elements: List[Dict[str, Any]]):
            print("\nUI Element Tree:")
            for element in elements:
                print_ui_element(element)

        all_elements_result = session.mobile.get_all_ui_elements(timeout_ms=3000)
        if all_elements_result.success:
            elements = json.loads(all_elements_result.elements) if isinstance(all_elements_result.elements, str) else all_elements_result.elements
            print_all_ui_elements(elements)
            print(f"Request ID: {all_elements_result.request_id}")
        else:
            print(f"Error getting all UI elements: {all_elements_result.error_message}")

        # Send key event
        print("\nSending key event...")
        key_result = session.mobile.send_key(KeyCode.HOME)
        print(f"Key event sent successfully: {key_result.success}")
        print(f"Request ID: {key_result.request_id}")

        # Input text
        print("\nInput text...")
        input_result = session.mobile.input_text("Hello, AgentBay!")
        print(f"Text input successfully: {input_result.success}")
        print(f"Request ID: {input_result.request_id}")

        # Swipe screen
        print("\nSwiping screen...")
        swipe_result = session.mobile.swipe(
            start_x=100,  # Starting X coordinate
            start_y=800,  # Starting Y coordinate
            end_x=900,  # Ending X coordinate
            end_y=200,  # Ending Y coordinate
            duration_ms=500,  # Swipe duration in milliseconds
        )
        print(f"Screen swiped successfully: {swipe_result.success}")
        print(f"Request ID: {swipe_result.request_id}")

        # Tap event (mobile touch)
        print("\nTapping screen...")
        tap_result = session.mobile.tap(
            x=500,  # X coordinate for tap
            y=800,  # Y coordinate for tap
        )
        print(f"Screen tapped successfully: {tap_result.success}")
        print(f"Request ID: {tap_result.request_id}")

        # Screenshot
        print("\nTaking screenshot...")
        screenshot_result = session.mobile.screenshot()
        print(f"Screenshot taken successfully: {screenshot_result.success}")
        if screenshot_result.success and screenshot_result.data:
            print(f"Screenshot data length: {len(screenshot_result.data)} bytes")
        print(f"Request ID: {screenshot_result.request_id}")

        # Start application with specific activity
        print("\nStarting application with specific activity...")
        app_package = "com.xingin.xhs"
        app_activity = "com.xingin.outside.activity.OppoOutsideFeedActivity"
        start_cmd = f"monkey -p {app_package} -c android.intent.category.LAUNCHER 1"

        start_result = session.mobile.start_app(
            start_cmd=start_cmd, activity=app_activity
        )
        print(f"Start app with activity success: {start_result.success}")
        if start_result.success and start_result.data:
            print("Started processes:")
            for process in start_result.data:
                print(f"  - {process.pname} (PID: {process.pid})")
        print(f"Request ID: {start_result.request_id}")

        # Delete session
        print("\nDeleting session...")
        delete_result = agent_bay.delete(session)
        session = None  # Clear session variable to avoid using it after deletion
        print(f"Session deleted successfully: {delete_result.success}")
        print(f"Request ID: {delete_result.request_id}")

    except Exception as e:
        print(f"Failed to test ui api: {e}")
        if session:
            try:
                delete_result = agent_bay.delete(session)
                print(f"Session deleted after error: {delete_result.success}")
            except AgentBayError as delete_error:
                print(f"Error deleting session after error: {delete_error}")


if __name__ == "__main__":
    main()
