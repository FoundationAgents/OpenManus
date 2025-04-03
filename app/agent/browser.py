import base64
import hashlib
import io
import json
import os
import time
from hashlib import sha256
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image
from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.config import config
from app.logger import logger
from app.prompt.browser import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import Message, ToolChoice
from app.tool import BrowserUseTool, Terminate, ToolCollection
from app.tool.browser_use_tool import BROWSER_USE_TOOL_NAME


class BrowserAgent(ToolCallAgent):
    """
    A browser agent that uses the browser_use library to control a browser.

    This agent can navigate web pages, interact with elements, fill forms,
    extract content, and perform other browser-based actions to accomplish tasks.
    """

    class Events(ToolCallAgent.Events):
        # Browser events
        BROWSER_BROWSER_USE_START = "agent:browser:browse:start"
        BROWSER_BROWSER_USE_COMPLETE = "agent:browser:browse:complete"
        BROWSER_BROWSER_USE_ERROR = "agent:browser:browse:error"

    name: str = "browser"
    description: str = "A browser agent that can control a browser to accomplish tasks"

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20

    # Configure the available tools
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(BrowserUseTool(), Terminate())
    )

    # Use Auto for tool choice to allow both tool usage and free-form responses
    tool_choices: ToolChoice = ToolChoice.AUTO
    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])

    _current_base64_image: Optional[str] = None
    _pre_base64_image: Optional[str] = None
    _pre_base64_path: Optional[str] = None

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        if not self._is_special_tool(name):
            return
        else:
            await self.available_tools.get_tool(BROWSER_USE_TOOL_NAME).cleanup()
            await super()._handle_special_tool(name, result, **kwargs)

    async def get_browser_state(self) -> Optional[dict]:
        """Get the current browser state for context in next steps."""
        browser_tool = self.available_tools.get_tool(BROWSER_USE_TOOL_NAME)
        if not browser_tool:
            return {"error": "Browser tool not found"}

        try:
            # Get browser state directly from the tool
            result = await browser_tool.get_current_state()

            if result.error:
                logger.debug(f"Browser state error: {result.error}")
                return {"error": result.error}

            # Store screenshot if available
            if hasattr(result, "base64_image") and result.base64_image:
                self._current_base64_image = result.base64_image

            # Parse the state info
            state = json.loads(result.output)
            return state

        except Exception as e:
            logger.debug(f"Failed to get browser state: {str(e)}")
            return None

    async def think(self) -> bool:
        """Process current state and decide next actions using tools, with browser state info added"""
        # Add browser state to the context
        self.emit(self.Events.BROWSER_BROWSER_USE_START, {})
        browser_state = await self.get_browser_state()

        # Initialize placeholder values
        url_info = ""
        tabs_info = ""
        content_above_info = ""
        content_below_info = ""
        results_info = ""

        if browser_state and not browser_state.get("error"):
            # URL and title info
            url_info = f"\n   URL: {browser_state.get('url', 'N/A')}\n   Title: {browser_state.get('title', 'N/A')}"

            # Tab information
            if "tabs" in browser_state:
                tabs = browser_state.get("tabs", [])
                if tabs:
                    tabs_info = f"\n   {len(tabs)} tab(s) available"

            # Content above/below viewport
            pixels_above = browser_state.get("pixels_above", 0)
            pixels_below = browser_state.get("pixels_below", 0)

            if pixels_above > 0:
                content_above_info = f" ({pixels_above} pixels)"

            if pixels_below > 0:
                content_below_info = f" ({pixels_below} pixels)"

            # Add screenshot as base64 if available
            if self._current_base64_image:
                # Create a message with image attachment
                image_message = Message.user_message(
                    content="Current browser screenshot:",
                    base64_image=self._current_base64_image,
                )
                self.memory.add_message(image_message)

        # Replace placeholders with actual browser state info
        self.next_step_prompt = NEXT_STEP_PROMPT.format(
            url_placeholder=url_info,
            tabs_placeholder=tabs_info,
            content_above_placeholder=content_above_info,
            content_below_placeholder=content_below_info,
            results_placeholder=results_info,
        )

        if browser_state and not browser_state.get("error"):
            # Save screenshot to local file and use relative path
            if self._current_base64_image:
                # Check if the current image is similar to the previous one
                similar_image_found = False
                if self._pre_base64_image and calculate_image_similarity(
                    self._current_base64_image, self._pre_base64_image
                ):
                    similar_image_found = True

                if not similar_image_found:
                    task_dir = f"{config.workspace_root}/{self.task_id or 'unknown'}"
                    if not os.path.exists(task_dir):
                        os.makedirs(task_dir, exist_ok=True)
                    image_path = f"{task_dir}/screenshot_{time.time()}.png"
                    with open(image_path, "wb") as f:
                        f.write(base64.b64decode(self._current_base64_image))

                    relative_path = os.path.relpath(image_path, config.workspace_root)
                    screenshot_path = f"/workspace/{relative_path}"
                else:
                    screenshot_path = self._pre_base64_path

                # Update previous image
                self._pre_base64_image = self._current_base64_image
                self._pre_base64_path = screenshot_path
            self.emit(
                self.Events.BROWSER_BROWSER_USE_COMPLETE,
                {
                    "url": (
                        browser_state.get("url", "N/A")
                        if browser_state and not browser_state.get("error")
                        else "N/A"
                    ),
                    "title": (
                        browser_state.get("title", "N/A")
                        if browser_state and not browser_state.get("error")
                        else "N/A"
                    ),
                    "tabs": tabs_info,
                    "content_above": content_above_info,
                    "content_below": content_below_info,
                    "screenshot": (
                        Path(screenshot_path)
                        .as_posix()
                        .replace(config.workspace_root.as_posix(), "/workspace")
                    ),
                    "results": results_info,
                },
            )
        else:
            self.emit(
                self.Events.BROWSER_BROWSER_USE_ERROR,
                {
                    "error": (
                        browser_state.get("error", "Unknown error")
                        if browser_state
                        else "Unknown error"
                    )
                },
            )

        # Call parent implementation
        result = await super().think()

        # Reset the next_step_prompt to its original state
        self.next_step_prompt = NEXT_STEP_PROMPT

        return result


def calculate_image_similarity(
    img1_base64: str, img2_base64: str, threshold: float = 0.85
) -> bool:
    """
    Calculate the similarity between two images using perceptual hashing method.

    Args:
        img1_base64: Base64 encoded string of the first image
        img2_base64: Base64 encoded string of the second image
        threshold: Similarity threshold, default 0.85

    Returns:
        bool: Returns True if similarity exceeds threshold, False otherwise
    """

    def base64_to_pil(base64_str: str) -> Image.Image:
        img_data = base64.b64decode(base64_str)
        return Image.open(io.BytesIO(img_data))

    def calculate_phash(image: Image.Image, hash_size: int = 8) -> str:
        # Convert to grayscale
        image = image.convert("L")
        # Resize image
        image = image.resize((hash_size, hash_size), Image.Resampling.LANCZOS)
        # Calculate mean value
        pixels = np.array(image)
        avg = pixels.mean()
        # Generate hash
        diff = pixels > avg
        return "".join(["1" if pixel else "0" for pixel in diff.flatten()])

    def hamming_distance(hash1: str, hash2: str) -> int:
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

    try:
        # Convert base64 to PIL image
        img1 = base64_to_pil(img1_base64)
        img2 = base64_to_pil(img2_base64)

        # Calculate perceptual hash
        hash1 = calculate_phash(img1)
        hash2 = calculate_phash(img2)

        # Calculate Hamming distance
        distance = hamming_distance(hash1, hash2)
        max_distance = len(hash1)
        similarity = 1 - (distance / max_distance)

        return similarity >= threshold
    except Exception as e:
        logger.error(f"Error calculating image similarity: {str(e)}")
        return False
