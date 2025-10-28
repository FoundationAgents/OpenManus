"""
Functional validation helpers for Computer and Mobile modules.
These helpers verify that operations actually work by checking their effects.
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class FunctionalTestConfig:
    """Configuration for functional tests."""
    wait_time_after_action: float = 1.0  # Wait time after each action (seconds)
    max_retries: int = 3  # Maximum retry attempts
    screenshot_comparison: bool = True  # Enable screenshot comparison
    ui_element_tolerance: float = 0.3  # UI element change tolerance (0.0-1.0)
    cursor_position_tolerance: int = 5  # Cursor position tolerance in pixels


@dataclass
class FunctionalTestResult:
    """Result of a functional test."""
    test_name: str
    success: bool = False
    message: str = ""
    details: Dict[str, Any] = None
    duration: float = 0.0
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
    
    def set_success(self, message: str):
        """Mark the test as successful."""
        self.success = True
        self.message = message
    
    def set_failure(self, message: str):
        """Mark the test as failed."""
        self.success = False
        self.message = message
    
    def add_detail(self, key: str, value: Any):
        """Add a detail to the test result."""
        self.details[key] = value


def default_functional_test_config() -> FunctionalTestConfig:
    """Return default configuration for functional tests."""
    return FunctionalTestConfig()


def validate_cursor_position(cursor_result, screen_result, expected_x: int, expected_y: int, tolerance: int) -> bool:
    """
    Check if cursor position is within screen bounds and expected range.
    
    Args:
        cursor_result: Result from get_cursor_position()
        screen_result: Result from get_screen_size()
        expected_x: Expected X coordinate
        expected_y: Expected Y coordinate
        tolerance: Position tolerance in pixels
        
    Returns:
        bool: True if position is valid
    """
    if not cursor_result or not screen_result:
        return False
    
    if not hasattr(cursor_result, 'data') or not hasattr(screen_result, 'data'):
        return False
    
    cursor_data = cursor_result.data
    screen_data = screen_result.data
    
    if not cursor_data or not screen_data:
        return False
    
    # Parse JSON data if it's a string
    import json
    try:
        if isinstance(cursor_data, str):
            cursor_data = json.loads(cursor_data)
        if isinstance(screen_data, str):
            screen_data = json.loads(screen_data)
    except (json.JSONDecodeError, TypeError):
        return False
    
    # Check if cursor is within screen bounds
    if (cursor_data.get('x', -1) < 0 or cursor_data.get('y', -1) < 0 or
        cursor_data.get('x', 0) >= screen_data.get('width', 0) or
        cursor_data.get('y', 0) >= screen_data.get('height', 0)):
        return False
    
    # Check if cursor is within expected position tolerance
    delta_x = abs(cursor_data.get('x', 0) - expected_x)
    delta_y = abs(cursor_data.get('y', 0) - expected_y)
    
    return delta_x <= tolerance and delta_y <= tolerance


def validate_screenshot_changed(url1: str, url2: str) -> bool:
    """
    Check if screenshot content actually changed by comparing image hashes.
    
    Args:
        url1: First screenshot URL
        url2: Second screenshot URL
        
    Returns:
        bool: True if image content is different
    """
    if not url1 or not url2:
        return False
    
    try:
        import requests
        from PIL import Image
        import imagehash
        from io import BytesIO
        
        # Download images
        response1 = requests.get(url1, timeout=10)
        response1.raise_for_status()
        img1 = Image.open(BytesIO(response1.content))
        
        response2 = requests.get(url2, timeout=10)
        response2.raise_for_status()
        img2 = Image.open(BytesIO(response2.content))
        
        # Calculate perceptual hashes (resistant to minor variations)
        hash1 = imagehash.average_hash(img1)
        hash2 = imagehash.average_hash(img2)
        
        # Compare hashes (0 = identical, >0 = different)
        hash_diff = hash1 - hash2
        
        # Consider images different if hash difference > 0
        return hash_diff > 0
        
    except Exception as e:
        # If image comparison fails, log error and return False
        print(f"Warning: Failed to compare screenshots: {e}")
        return False


def validate_screen_size(screen_result) -> bool:
    """
    Check if screen size values are reasonable.
    
    Args:
        screen_result: Result from get_screen_size()
        
    Returns:
        bool: True if screen size is valid
    """
    if not screen_result or not hasattr(screen_result, 'data'):
        return False
    
    screen_data = screen_result.data
    if not screen_data:
        return False
    
    # Parse JSON data if it's a string
    import json
    try:
        if isinstance(screen_data, str):
            screen_data = json.loads(screen_data)
    except (json.JSONDecodeError, TypeError):
        return False
    
    width = screen_data.get('width', 0)
    height = screen_data.get('height', 0)
    dpi = screen_data.get('dpiScalingFactor', 0)
    
    # Screen dimensions should be positive and reasonable
    return (width > 0 and height > 0 and
            width <= 10000 and height <= 10000 and  # Max reasonable size
            dpi > 0 and dpi <= 10)  # Reasonable DPI range


def convert_mobile_ui_elements(elements: List[Any]) -> List[Dict[str, Any]]:
    """
    Convert mobile UI elements to simplified format for comparison.
    
    Args:
        elements: List of UI elements from mobile API
        
    Returns:
        List of simplified UI element dictionaries
    """
    result = []
    for elem in elements:
        if elem:
            simplified = {
                'text': getattr(elem, 'text', ''),
                'class_name': getattr(elem, 'class_name', ''),
                'bounds': {
                    'left': getattr(elem, 'bounds', {}).get('left', 0),
                    'top': getattr(elem, 'bounds', {}).get('top', 0),
                    'right': getattr(elem, 'bounds', {}).get('right', 0),
                    'bottom': getattr(elem, 'bounds', {}).get('bottom', 0),
                }
            }
            result.append(simplified)
    return result


def validate_ui_elements_changed(before: List[Dict[str, Any]], after: List[Dict[str, Any]], tolerance: float) -> bool:
    """
    Check if UI elements have changed significantly.
    
    Args:
        before: UI elements before action
        after: UI elements after action
        tolerance: Change tolerance (0.0-1.0)
        
    Returns:
        bool: True if elements changed significantly
    """
    if len(before) == 0 and len(after) == 0:
        return False  # No elements in either case
    
    # Calculate change ratio
    total_elements = len(before) + len(after)
    if total_elements == 0:
        return False
    
    # Simple comparison: check if element counts differ significantly
    count_diff = abs(len(after) - len(before))
    if count_diff / max(len(before), 1) > tolerance:
        return True
    
    # Check for text content changes
    before_texts = {elem.get('text', '') for elem in before if elem.get('text')}
    after_texts = {elem.get('text', '') for elem in after if elem.get('text')}
    
    # Count text differences
    different_count = len(after_texts - before_texts) + len(before_texts - after_texts)
    
    change_ratio = different_count / total_elements
    return change_ratio > tolerance


def validate_app_launched(before_ui: List[Dict[str, Any]], after_ui: List[Dict[str, Any]]) -> bool:
    """
    Check if app launch was successful by analyzing UI changes.
    
    Args:
        before_ui: UI elements before app launch
        after_ui: UI elements after app launch
        
    Returns:
        bool: True if app launch caused significant UI changes
    """
    # App launch should result in significant UI changes (50% threshold)
    return validate_ui_elements_changed(before_ui, after_ui, 0.5)


def find_text_input_element(elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Find a text input element in UI elements list.
    
    Args:
        elements: List of UI elements
        
    Returns:
        First text input element found, or None
    """
    for elem in elements:
        class_name = elem.get('class_name', '').lower()
        if ('edittext' in class_name or 
            'textfield' in class_name or 
            'input' in class_name):
            return elem
    return None


def calculate_element_center(elem: Dict[str, Any]) -> Tuple[int, int]:
    """
    Calculate the center point of a UI element.
    
    Args:
        elem: UI element with bounds
        
    Returns:
        Tuple of (center_x, center_y)
    """
    if not elem:
        return 0, 0
    
    bounds = elem.get('bounds', {})
    center_x = (bounds.get('left', 0) + bounds.get('right', 0)) // 2
    center_y = (bounds.get('top', 0) + bounds.get('bottom', 0)) // 2
    return center_x, center_y


def validate_element_bounds(elem: Dict[str, Any], screen_width: int, screen_height: int) -> bool:
    """
    Check if element bounds are reasonable.
    
    Args:
        elem: UI element with bounds
        screen_width: Screen width
        screen_height: Screen height
        
    Returns:
        bool: True if bounds are valid
    """
    if not elem:
        return False
    
    bounds = elem.get('bounds', {})
    left = bounds.get('left', -1)
    top = bounds.get('top', -1)
    right = bounds.get('right', -1)
    bottom = bounds.get('bottom', -1)
    
    return (left >= 0 and top >= 0 and
            right <= screen_width and bottom <= screen_height and
            left < right and top < bottom)


def safe_screenshot(computer_or_mobile, test_name: str) -> Tuple[Optional[str], Optional[Exception]]:
    """
    Take a screenshot with error handling.
    
    Args:
        computer_or_mobile: Computer or Mobile instance
        test_name: Name of the test (for logging)
        
    Returns:
        Tuple of (screenshot_url, error)
    """
    try:
        if computer_or_mobile is None:
            return None, None
        
        result = computer_or_mobile.screenshot()
        if result is None:
            return None, None
        
        if hasattr(result, 'error_message') and result.error_message:
            return None, Exception(result.error_message)
        
        if hasattr(result, 'data') and result.data:
            return result.data, None
        
        return None, None
    except Exception as e:
        return None, e


def wait_with_timeout(condition_func, timeout: float, check_interval: float = 0.1) -> bool:
    """
    Wait for a condition with timeout.
    
    Args:
        condition_func: Function that returns True when condition is met
        timeout: Maximum wait time in seconds
        check_interval: How often to check the condition
        
    Returns:
        bool: True if condition was met within timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(check_interval)
    return False 