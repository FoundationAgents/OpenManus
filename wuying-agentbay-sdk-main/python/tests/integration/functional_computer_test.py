"""
Computer module functional validation tests.
These tests validate that operations actually work by checking their effects.
"""

import os
import time
import unittest
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from functional_helpers import (
    default_functional_test_config,
    FunctionalTestResult,
    validate_cursor_position,
    validate_screenshot_changed,
    validate_screen_size,
    safe_screenshot
)


class TestComputerFunctionalValidation(unittest.TestCase):
    """Computer module functional validation tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Skip if no API key provided
        api_key = os.environ.get("AGENTBAY_API_KEY")
        if not api_key:
            self.skipTest("AGENTBAY_API_KEY environment variable not set")
        
        # Create AgentBay client and session
        self.agent_bay = AgentBay(api_key)
        session_params = CreateSessionParams(image_id="linux_latest")
        
        session_result = self.agent_bay.create(session_params)
        if session_result.session is None:
            error_msg = f"Session creation failed. Error: {session_result.error_message}, Success: {session_result.success}, Request ID: {session_result.request_id}"
            self.fail(error_msg)
        self.assertIsNotNone(session_result.session, "Session should be created")
        
        self.session = session_result.session
        self.config = default_functional_test_config()
        
        print(f"Created Computer functional validation session: {self.session.session_id}")
        
        # Wait for session to be ready
        time.sleep(5)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'session') and self.session:
            try:
                delete_result = self.session.delete()
                if delete_result and hasattr(delete_result, 'request_id') and delete_result.request_id:
                    print(f"Session {self.session.session_id} deleted successfully")
                # Wait for session to be fully deleted before next test
                time.sleep(3)
            except Exception as e:
                print(f"Error deleting session: {e}")

    def test_mouse_movement_validation(self):
        """Test mouse movement functionality through cursor position changes."""
        result = FunctionalTestResult("MouseMovementValidation")
        start_time = time.time()
        
        try:
            # Step 1: Get initial cursor position
            initial_cursor = self.session.computer.get_cursor_position()
            if initial_cursor.error_message:
                result.set_failure(f"Failed to get initial cursor position: {initial_cursor.error_message}")
            
            # Parse cursor data if it's JSON string
            import json
            cursor_data = initial_cursor.data
            try:
                if isinstance(cursor_data, str):
                    cursor_data = json.loads(cursor_data)
                elif cursor_data is None:
                    result.set_failure("No cursor position data received")
            except json.JSONDecodeError:
                result.set_failure(f"Failed to parse cursor position data: {cursor_data}")
            
            if not result.message:  # No error yet
                result.add_detail("initial_cursor", {
                    "x": cursor_data.get('x') if isinstance(cursor_data, dict) else None, 
                    "y": cursor_data.get('y') if isinstance(cursor_data, dict) else None
                })
            
            # Step 2: Get screen size for safe movement
            if result.message:  # Has error
                pass
            else:
                screen = self.session.computer.get_screen_size()
                if screen.error_message or not validate_screen_size(screen):
                    result.set_failure("Invalid screen size")
            
            # Parse screen data if it's JSON string
            if not result.message:
                screen_data = screen.data
                try:
                    if isinstance(screen_data, str):
                        screen_data = json.loads(screen_data)
                    elif screen_data is None:
                        result.set_failure("No screen size data received")
                except json.JSONDecodeError:
                    result.set_failure(f"Failed to parse screen size data: {screen_data}")
            
            if not result.message:
                result.add_detail("screen_size", {
                    "width": screen_data.get('width') if isinstance(screen_data, dict) else None,
                    "height": screen_data.get('height') if isinstance(screen_data, dict) else None,
                    "dpi": screen_data.get('dpiScalingFactor') if isinstance(screen_data, dict) else None
                })
                
                # Step 3: Move mouse to center of screen
                target_x = screen_data.get('width') // 2
                target_y = screen_data.get('height') // 2
                move_result = self.session.computer.move_mouse(target_x, target_y)
                if not move_result.success:
                    result.set_failure(f"Mouse move operation failed: {move_result.error_message}")
            
            # Wait for movement to complete
            if not result.message:
                time.sleep(self.config.wait_time_after_action)
                
                # Step 4: Verify cursor position changed
                new_cursor = self.session.computer.get_cursor_position()
                if new_cursor.error_message:
                    result.set_failure(f"Failed to get new cursor position: {new_cursor.error_message}")
                
                # Parse new cursor data
                if not result.message:
                    new_cursor_data = new_cursor.data
                    try:
                        if isinstance(new_cursor_data, str):
                            new_cursor_data = json.loads(new_cursor_data)
                    except json.JSONDecodeError:
                        result.set_failure(f"Failed to parse new cursor position data: {new_cursor_data}")
            
            if not result.message:
                result.add_detail("new_cursor", {
                    "x": new_cursor_data.get('x') if isinstance(new_cursor_data, dict) else None,
                    "y": new_cursor_data.get('y') if isinstance(new_cursor_data, dict) else None
                })
                result.add_detail("target_position", {"x": target_x, "y": target_y})
                
                # Validate cursor movement
                if validate_cursor_position(new_cursor, screen, target_x, target_y, self.config.cursor_position_tolerance):
                    result.set_success("Mouse movement validated successfully")
                    print(f"✅ Mouse moved from ({cursor_data.get('x')},{cursor_data.get('y')}) "
                          f"to ({new_cursor_data.get('x')},{new_cursor_data.get('y')}), "
                          f"target was ({target_x},{target_y})")
                else:
                    result.set_failure("Cursor position validation failed")
                    print(f"❌ Mouse movement failed: expected ({target_x},{target_y}), "
                          f"got ({new_cursor.data.get('x')},{new_cursor.data.get('y')})")
                
        finally:
            result.duration = time.time() - start_time
            print(f"Test Result: {result}")
            self.assertTrue(result.success, result.message)

    def test_screenshot_content_validation(self):
        """Test screenshot functionality through content changes."""
        result = FunctionalTestResult("ScreenshotContentValidation")
        start_time = time.time()
        
        try:
            # Step 1: Take initial screenshot
            screenshot1, error1 = safe_screenshot(self.session.computer, "initial")
            if error1 or not screenshot1:
                result.set_failure("Failed to take initial screenshot")
            else:
                result.add_detail("screenshot1_url", screenshot1)
                
                # Step 2: Perform a visible action (move mouse to corner)
                screen = self.session.computer.get_screen_size()
                if screen.error_message:
                    result.set_failure("Failed to get screen size")
                else:
                    # Move to top-left corner
                    move_result = self.session.computer.move_mouse(50, 50)
                    if not move_result.success:
                        result.set_failure(f"Failed to move mouse: {move_result.error_message}")
                    else:
                        # Wait for action to complete
                        time.sleep(self.config.wait_time_after_action)
                        
                        # Step 3: Take second screenshot
                        screenshot2, error2 = safe_screenshot(self.session.computer, "after_move")
                        if error2 or not screenshot2:
                            result.set_failure("Failed to take second screenshot")
                        else:
                            result.add_detail("screenshot2_url", screenshot2)
                            
                            # Validate screenshot change
                            if validate_screenshot_changed(screenshot1, screenshot2):
                                result.set_success("Screenshot content validation successful")
                                print(f"✅ Screenshots changed: {screenshot1} → {screenshot2}")
                            else:
                                result.set_failure("Screenshots did not change as expected")
                                print(f"❌ Screenshots unchanged: {screenshot1} = {screenshot2}")
                
        finally:
            result.duration = time.time() - start_time
            print(f"Test Result: {result}")
            self.assertTrue(result.success, result.message)

    def test_keyboard_input_validation(self):
        """Test keyboard input functionality by verifying API returns success.
        
        Note: Visual validation of keyboard input requires an active text input field.
        This test validates that keyboard operations execute successfully via the API.
        """
        import json
        result = FunctionalTestResult("KeyboardInputValidation")
        start_time = time.time()
        
        try:
            # Test keyboard input API operations
            test_text = "AgentBay Test"
            
            # Test 1: input_text
            input_result = self.session.computer.input_text(test_text)
            if not input_result.success:
                result.set_failure(f"Failed to input text: {input_result.error_message}")
            else:
                result.add_detail("input_text_success", True)
            
            if not result.message:
                time.sleep(0.5)
                
                # Test 2: press_keys (Ctrl+A)
                select_result = self.session.computer.press_keys(["Ctrl", "a"], False)
                if not select_result.success:
                    result.set_failure(f"Failed to press Ctrl+A: {select_result.error_message}")
                else:
                    result.add_detail("press_keys_success", True)
            
            if not result.message:
                time.sleep(0.5)
                
                # Test 3: press_keys (Delete)
                delete_result = self.session.computer.press_keys(["Delete"], False)
                if not delete_result.success:
                    result.set_failure(f"Failed to press Delete: {delete_result.error_message}")
                else:
                    result.add_detail("delete_keys_success", True)
            
            if not result.message:
                result.set_success("Keyboard API operations validated successfully")
                print("✅ Keyboard operations: input_text, press_keys(Ctrl+A), press_keys(Delete) all successful")
                
        finally:
            result.duration = time.time() - start_time
            print(f"Test Result: {result}")
            self.assertTrue(result.success, result.message)

    def test_screen_consistency_validation(self):
        """Test screen consistency by validating cursor positions at boundaries."""
        import json
        result = FunctionalTestResult("ScreenConsistencyValidation")
        start_time = time.time()
        
        try:
            # Step 1: Get screen size
            screen = self.session.computer.get_screen_size()
            if screen.error_message:
                result.set_failure(f"Failed to get screen size: {screen.error_message}")
            elif not screen.data:
                result.set_failure("No screen size data received")
            elif not validate_screen_size(screen):
                result.set_failure("Invalid screen size")
            else:
                # Parse screen data if it's JSON string
                screen_data = screen.data
                if isinstance(screen_data, str):
                    screen_data = json.loads(screen_data)
                
                result.add_detail("screen", {
                    "width": screen_data.get('width'),
                    "height": screen_data.get('height'),
                    "dpi": screen_data.get('dpiScalingFactor')
                })
                
                # Step 2: Test cursor positions at screen boundaries
                test_positions = [
                    ("top_left", 0, 0),
                    ("top_right", screen_data.get('width') - 1, 0),
                    ("bottom_left", 0, screen_data.get('height') - 1),
                    ("bottom_right", screen_data.get('width') - 1, screen_data.get('height') - 1),
                    ("center", screen_data.get('width') // 2, screen_data.get('height') // 2),
                ]
                
                all_valid = True
                position_results = {}
                
                for name, x, y in test_positions:
                    # Move to position
                    move_result = self.session.computer.move_mouse(x, y)
                    if not move_result.success:
                        print(f"Failed to move to {name} ({x},{y}): {move_result.error_message}")
                        all_valid = False
                        position_results[name] = False
                        continue
                    
                    time.sleep(0.5)
                    
                    # Get cursor position
                    cursor = self.session.computer.get_cursor_position()
                    if cursor.error_message:
                        print(f"Failed to get cursor at {name}: {cursor.error_message}")
                        all_valid = False
                        position_results[name] = False
                        continue
                    
                    # Validate position
                    valid = validate_cursor_position(cursor, screen, x, y, self.config.cursor_position_tolerance)
                    position_results[name] = valid
                    
                    # Parse cursor data for display
                    cursor_data = cursor.data
                    if isinstance(cursor_data, str):
                        cursor_data = json.loads(cursor_data)
                    
                    if not valid:
                        all_valid = False
                        print(f"❌ Position {name}: expected ({x},{y}), got ({cursor_data.get('x')},{cursor_data.get('y')})")
                    else:
                        print(f"✅ Position {name}: ({cursor_data.get('x')},{cursor_data.get('y')}) validated")
                
                result.add_detail("position_results", position_results)
                result.add_detail("all_positions_valid", all_valid)
                
                if all_valid:
                    result.set_success("Screen consistency validation successful")
                else:
                    result.set_failure("Some cursor positions failed validation")
                
        finally:
            result.duration = time.time() - start_time
            print(f"Test Result: {result}")
            self.assertTrue(result.success, result.message)

    def test_complete_workflow_validation(self):
        """Test complete desktop automation workflow with mouse and keyboard operations.
        
        This test validates a sequence of computer operations execute successfully.
        """
        import json
        result = FunctionalTestResult("CompleteWorkflowValidation")
        start_time = time.time()
        
        try:
            # This test combines multiple operations to validate a complete workflow
            workflow_steps = []
            
            # Step 1: Get screen size
            screen = self.session.computer.get_screen_size()
            if screen.error_message or not screen.data:
                result.set_failure("Failed to get screen size")
            else:
                workflow_steps.append("Got screen size")
            
            # Step 2: Move mouse
            if not result.message:
                screen_data = screen.data
                if isinstance(screen_data, str):
                    screen_data = json.loads(screen_data)
                
                center_x = screen_data.get('width') // 2
                center_y = screen_data.get('height') // 2
                move_result = self.session.computer.move_mouse(center_x, center_y)
                if move_result.success:
                    workflow_steps.append("Moved mouse to center")
                else:
                    result.set_failure("Failed to move mouse")
            
            # Step 3: Click mouse
            if not result.message:
                click_result = self.session.computer.click_mouse(center_x, center_y, "left")
                if click_result.success:
                    workflow_steps.append("Clicked at center")
                else:
                    result.set_failure("Failed to click mouse")
            
            # Step 4: Input text
            if not result.message:
                input_result = self.session.computer.input_text("Workflow Test")
                if input_result.success:
                    workflow_steps.append("Input text")
                else:
                    result.set_failure("Failed to input text")
            
            # Step 5: Press keys (Ctrl+A)
            if not result.message:
                select_result = self.session.computer.press_keys(["Ctrl", "a"], False)
                if select_result.success:
                    workflow_steps.append("Pressed Ctrl+A")
                else:
                    result.set_failure("Failed to press Ctrl+A")
            
            # Step 6: Press keys (Ctrl+C)
            if not result.message:
                copy_result = self.session.computer.press_keys(["Ctrl", "c"], False)
                if copy_result.success:
                    workflow_steps.append("Pressed Ctrl+C")
                else:
                    result.set_failure("Failed to press Ctrl+C")
            
            # Step 7: Press keys (Delete)
            if not result.message:
                delete_result = self.session.computer.press_keys(["Delete"], False)
                if delete_result.success:
                    workflow_steps.append("Pressed Delete")
                else:
                    result.set_failure("Failed to press Delete")
            
            # Step 8: Press keys (Ctrl+V)
            if not result.message:
                paste_result = self.session.computer.press_keys(["Ctrl", "v"], False)
                if paste_result.success:
                    workflow_steps.append("Pressed Ctrl+V")
                else:
                    result.set_failure("Failed to press Ctrl+V")
            
            # Step 9: Take screenshot
            if not result.message:
                screenshot, error = safe_screenshot(self.session.computer, "workflow_end")
                if error or not screenshot:
                    result.set_failure("Failed to take screenshot")
                else:
                    workflow_steps.append("Took screenshot")
            
            # Validate workflow completion
            if not result.message:
                result.add_detail("workflow_steps", workflow_steps)
                
                if len(workflow_steps) >= 8:
                    result.set_success("Complete workflow validation successful")
                    print(f"✅ Workflow completed: {len(workflow_steps)} steps")
                else:
                    result.set_failure(f"Workflow incomplete: only {len(workflow_steps)} steps")
                    print(f"❌ Workflow failed: {len(workflow_steps)} steps")
                
        finally:
            result.duration = time.time() - start_time
            print(f"Test Result: {result}")
            self.assertTrue(result.success, result.message)


if __name__ == '__main__':
    unittest.main() 