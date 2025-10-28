import os
import requests
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.browser.browser import BrowserOption
from agentbay.browser.browser_agent import ActOptions
from playwright.async_api import async_playwright


class FormFiller:
    """Core form filling functionality that can be used across different frameworks"""
    
    def __init__(self, api_key=None):
        """
        Initialize the FormFiller
        
        Args:
            api_key (str): Agent-Bay API key. If not provided, will be read from environment variables.
        """
        self.api_key = api_key or os.getenv("AGENTBAY_API_KEY")
        self.agent_bay = None
        self.session = None
        self.browser = None
        self.playwright = None
        self.page = None
    
    async def create_session(self, image_id="browser_latest", labels=None):
        """
        Create an Agent-Bay session
        
        Args:
            image_id (str): The image ID for the session
            labels (dict): Labels to attach to the session
            
        Returns:
            tuple: (agent_bay_instance, session_instance)
        """
        if labels is None:
            labels = {"project": "form-filling-agent", "version": "1.0"}
            
        # Initialize AgentBay
        self.agent_bay = AgentBay(api_key=self.api_key)
        
        # Create session parameters
        session_params = CreateSessionParams(
            image_id=image_id,
            labels=labels,
        )
        
        # Create session
        print("Creating session...")
        session_result = self.agent_bay.create(session_params)
        
        if not session_result.success:
            raise Exception(f"Failed to create session: {session_result.error_message}")
        
        self.session = session_result.session
        print(f"Session created: {self.session.session_id}")
        
        return self.agent_bay, self.session
    
    def upload_form_file(self, local_file_path, remote_file_path="/tmp/form.html"):
        """
        Upload the form HTML file to the Agent-Bay session
        
        Args:
            local_file_path (str): Path to the local form file
            remote_file_path (str): Path where the file should be stored in the session
            
        Returns:
            str: The remote file path
        """
        print(f"Uploading form file: {local_file_path}")
        
        # Read the file content
        with open(local_file_path, 'r') as f:
            content = f.read()
        
        # Upload file to Agent-Bay
        upload_result = self.session.file_system.write_file(
            remote_file_path,
            content
        )
        
        if not upload_result.success:
            raise Exception(f"Failed to upload file: {upload_result.error_message}")
        
        print("Form file uploaded successfully")
        return remote_file_path
    
    async def open_form_in_browser(self, form_path):
        """
        Open the form in a browser using Agent-Bay SDK
        
        Args:
            form_path (str): Path to the form file in the session
            
        Returns:
            tuple: (browser, page, playwright) instances
        """
        print("Initializing browser...")
        
        # Initialize browser
        init_result = await self.session.browser.initialize_async(BrowserOption())
        if not init_result:
            raise Exception("Failed to initialize browser")
        
        print("Browser initialized")
        
        # Get browser endpoint
        endpoint_url = self.session.browser.get_endpoint_url()
        print(f"Browser endpoint: {endpoint_url}")
        
        # Connect to browser using playwright with async context manager
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.connect_over_cdp(endpoint_url)
        self.page = await self.browser.new_page()
        
        # Navigate to the form file
        file_url = f"file://{form_path}"
        print(f"Navigating to: {file_url}")
        await self.page.goto(file_url)
        print("Form page loaded successfully")
        
        return self.browser, self.page, self.playwright
    
    async def fill_form_fields(self, field_instructions):
        """
        Fill the form using the BrowserAgent with provided instructions
        
        Args:
            field_instructions (list): List of instructions for filling form fields
            
        Returns:
            bool: True if all operations were successful
        """
        if not self.session or not self.page:
            raise Exception("Session or page not initialized")
        
        print("Filling form using BrowserAgent...")
        browser_agent = self.session.browser.agent
        
        results = []
        for instruction in field_instructions:
            result = await browser_agent.act_async(
                self.page,
                ActOptions(action=instruction)
            )
            if result.success:
                print(f"Instruction executed successfully: {instruction}")
            else:
                print(f"Failed to execute instruction '{instruction}': {result.message}")
            results.append(result.success)
        
        return all(results)
    
    def capture_screenshot(self, file_path: str) -> bool:
        """
        Capture a screenshot of the mobile screen and save it to the specified path.
        
        Args:
            session: The Agent Bay session
            file_path (str): Path to save the screenshot
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Capture screenshot using Agent Bay SDK
            session = self.session
            screenshot_result = session.ui.screenshot()
            if not screenshot_result.success:
                print(f"Warning: Failed to capture screenshot: {screenshot_result.error_message}")
                return False
            
            # Save the screenshot data to a file
            # The screenshot data is returned as a URL
            if screenshot_result.data:
                # Directly download the screenshot from the URL
                response = requests.get(screenshot_result.data)
                if response.status_code == 200:
                    # Save the screenshot content to local file
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    print(f"Screenshot saved to: {file_path}")
                    return True
                else:
                    print(f"Warning: Failed to download screenshot from {screenshot_result.data}, status code: {response.status_code}")
                    return False
            else:
                print("Warning: Screenshot captured but no data returned")
                return False
        except Exception as e:
            # If screenshot capture fails, log the error but don't stop the process
            print(f"Warning: Failed to capture screenshot {file_path}: {e}")
            return False
    async def close(self):
        """Clean up resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        if self.agent_bay and self.session:
            self.agent_bay.delete(self.session)
            
        print("Resources cleaned up successfully")


def get_default_form_instructions():
    """
    Get default form filling instructions
    
    Returns:
        list: List of default instructions for filling the sample form
    """
    return [
        "Enter 'John' in the input field with id firstName",
        "Enter 'Doe' in the input field with id lastName",
        "Enter 'john.doe@example.com' in the input field with id email",
        "Enter '+1-555-123-4567' in the input field with id phone",
        "Select 'support' in the dropdown with id subject",
        "Enter 'This is a test message from the form-filling agent.' in the textarea with id message",
        "Click the checkbox with id newsletter",
        "Click the submit button"
    ]
