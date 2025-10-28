"""
Screenshot Download Example

This example demonstrates how to take a screenshot from a session
and download it to a local file.

Expected output:
    Creating a new mobile session...
    Session created with ID: session-xxxxxxxxxxxxxx
    Request ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX

    Taking screenshot...
    Screenshot taken successfully
    Screenshot URL: https://***.oss-cn-hangzhou.aliyuncs.com/mcp/***/screenshot_***.png?Expires=***&OSSAccessKeyId=***&Signature=***
    Request ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX

    Downloading screenshot from URL...
    Screenshot downloaded successfully
    Saved to: /path/to/downloads/screenshot_session-xxxxxxxxxxxxxx.png
    File size: 111252 bytes

    Deleting session...
    Session deleted successfully: True
    Request ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
"""

import os
import requests
from agentbay import AgentBay
from agentbay.exceptions import AgentBayError
from agentbay.session_params import CreateSessionParams


def main():
    # Get API key from environment variable
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        raise ValueError("AGENTBAY_API_KEY environment variable is required")

    session = None
    try:
        agent_bay = AgentBay(api_key=api_key)

        # Create a new mobile session
        print("\nCreating a new mobile session...")
        params = CreateSessionParams(
            image_id="mobile_latest",
        )
        session_result = agent_bay.create(params)
        session = session_result.session
        print(f"Session created with ID: {session.session_id}")
        print(f"Request ID: {session_result.request_id}")

        # Take screenshot and get URL
        print("\nTaking screenshot...")
        screenshot_result = session.mobile.screenshot()
        
        if not screenshot_result.success:
            print(f"Failed to take screenshot: {screenshot_result.error_message}")
            return
            
        print(f"Screenshot taken successfully")
        print(f"Screenshot URL: {screenshot_result.data}")
        print(f"Request ID: {screenshot_result.request_id}")

        # Download screenshot to local file
        if screenshot_result.data:
            print("\nDownloading screenshot from URL...")
            
            # Create downloads directory if it doesn't exist
            download_dir = "downloads"
            os.makedirs(download_dir, exist_ok=True)
            
            # Define local file path
            local_file_path = os.path.join(download_dir, f"screenshot_{session.session_id}.png")
            
            # Download the image
            response = requests.get(screenshot_result.data, timeout=30)
            response.raise_for_status()
            
            # Save to local file
            with open(local_file_path, "wb") as f:
                f.write(response.content)
            
            print(f"Screenshot downloaded successfully")
            print(f"Saved to: {os.path.abspath(local_file_path)}")
            print(f"File size: {len(response.content)} bytes")
        else:
            print("No screenshot URL available")

        # Clean up: Delete session
        print("\nDeleting session...")
        delete_result = agent_bay.delete(session)
        session = None
        print(f"Session deleted successfully: {delete_result.success}")
        print(f"Request ID: {delete_result.request_id}")

    except requests.RequestException as e:
        print(f"Failed to download screenshot: {e}")
        if session:
            try:
                agent_bay.delete(session)
                print("Session deleted after error")
            except AgentBayError as delete_error:
                print(f"Error deleting session: {delete_error}")
    except Exception as e:
        print(f"Failed to execute screenshot download example: {e}")
        if session:
            try:
                agent_bay.delete(session)
                print("Session deleted after error")
            except AgentBayError as delete_error:
                print(f"Error deleting session: {delete_error}")


if __name__ == "__main__":
    main()
