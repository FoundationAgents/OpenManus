import base64
import hashlib
import io
import json
import os
import time
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import numpy as np
from PIL import Image
from pydantic import Field, model_validator

from app.agent.toolcall import ToolCallAgent, ToolCallAgentEvents, ToolCallContextHelper
from app.config import config
from app.logger import logger
from app.prompt.browser import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import Message, ToolChoice
from app.tool import BrowserUseTool, Terminate, ToolCollection

# Avoid circular import if BrowserAgent needs BrowserContextHelper
if TYPE_CHECKING:
    from app.agent.base import BaseAgent  # Or wherever memory is defined


class BrowserAgentEvents(ToolCallAgentEvents):
    # Browser events
    BROWSER_BROWSER_USE_START = "agent:lifecycle:step:think:browser:browse:start"
    BROWSER_BROWSER_USE_COMPLETE = "agent:lifecycle:step:think:browser:browse:complete"
    BROWSER_BROWSER_USE_ERROR = "agent:lifecycle:step:think:browser:browse:error"


class BrowserContextHelper:
    def __init__(self, agent: "BaseAgent"):
        self.agent = agent
        self._current_base64_image: Optional[str] = None
        self._pre_base64_image: Optional[str] = None
        self._pre_base64_path: Optional[str] = None

    async def get_browser_state(self) -> Optional[dict]:
        browser_tool = self.agent.tool_call_context_helper.available_tools.get_tool(
            BrowserUseTool().name
        )
        if not browser_tool or not hasattr(browser_tool, "get_current_state"):
            logger.warning("BrowserUseTool not found or doesn't have get_current_state")
            return None
        try:
            result = await browser_tool.get_current_state()
            if result.error:
                logger.debug(f"Browser state error: {result.error}")
                return None
            if hasattr(result, "base64_image") and result.base64_image:
                self._current_base64_image = result.base64_image
            else:
                self._current_base64_image = None
            return json.loads(result.output)
        except Exception as e:
            logger.debug(f"Failed to get browser state: {str(e)}")
            return None

    async def format_next_step_prompt(self) -> str:
        """Gets browser state and formats the browser prompt."""
        browser_state = await self.get_browser_state()
        url_info, tabs_info, content_above_info, content_below_info = "", "", "", ""
        results_info = ""  # Or get from agent if needed elsewhere

        if browser_state and not browser_state.get("error"):
            url_info = f"\n   URL: {browser_state.get('url', 'N/A')}\n   Title: {browser_state.get('title', 'N/A')}"
            tabs = browser_state.get("tabs", [])
            if tabs:
                tabs_info = f"\n   {len(tabs)} tab(s) available"
            pixels_above = browser_state.get("pixels_above", 0)
            pixels_below = browser_state.get("pixels_below", 0)
            if pixels_above > 0:
                content_above_info = f" ({pixels_above} pixels)"
            if pixels_below > 0:
                content_below_info = f" ({pixels_below} pixels)"

            if self._current_base64_image:
                image_message = Message.user_message(
                    content="Current browser screenshot:",
                    base64_image=self._current_base64_image,
                )
                # Check if the current image is similar to the previous one
                similar_image_found = False
                if self._pre_base64_image and calculate_image_similarity(
                    self._current_base64_image, self._pre_base64_image
                ):
                    similar_image_found = True

                if not similar_image_found:
                    task_dir = (
                        f"{config.workspace_root}/{self.agent.task_id or 'unknown'}"
                    )
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

                self.agent.memory.add_message(image_message)
                self._current_base64_image = None  # Consume the image after adding

            self.agent.emit(
                BrowserAgentEvents.BROWSER_BROWSER_USE_COMPLETE,
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
            self.agent.emit(
                BrowserAgentEvents.BROWSER_BROWSER_USE_ERROR,
                {
                    "error": (
                        browser_state.get("error", "Unknown error")
                        if browser_state
                        else "Unknown error"
                    )
                },
            )

        return NEXT_STEP_PROMPT.format(
            language=self.agent.language or "English",
            url_placeholder=url_info,
            tabs_placeholder=tabs_info,
            content_above_placeholder=content_above_info,
            content_below_placeholder=content_below_info,
            results_placeholder=results_info,
        )

    async def cleanup_browser(self):
        browser_tool = self.agent.tool_call_context_helper.available_tools.get_tool(
            BrowserUseTool().name
        )
        if browser_tool and hasattr(browser_tool, "cleanup"):
            await browser_tool.cleanup()


class BrowserAgent(ToolCallAgent):
    """
    A browser agent that uses the browser_use library to control a browser.

    This agent can navigate web pages, interact with elements, fill forms,
    extract content, and perform other browser-based actions to accomplish tasks.
    """

    name: str = "browser"
    description: str = "A browser agent that can control a browser to accomplish tasks"

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_steps: int = 20

    # Use Auto for tool choice to allow both tool usage and free-form responses
    tool_choices: ToolChoice = ToolChoice.AUTO
    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])

    browser_context_helper: Optional[BrowserContextHelper] = None
    tool_call_context_helper: Optional[ToolCallContextHelper] = None

    @model_validator(mode="after")
    def initialize_helper(self) -> "BrowserAgent":
        self.browser_context_helper = BrowserContextHelper(self)
        self.tool_call_context_helper = ToolCallContextHelper(self)
        # Configure the available tools
        self.tool_call_context_helper.available_tools = ToolCollection(
            BrowserUseTool(), Terminate()
        )
        self.next_step_prompt = NEXT_STEP_PROMPT.format(
            language=self.language or "English",
        )
        return self

    async def think(self) -> bool:
        """Process current state and decide next actions using tools, with browser state info added"""
        self.emit(BrowserAgentEvents.BROWSER_BROWSER_USE_START, {})
        self.next_step_prompt = (
            await self.browser_context_helper.format_next_step_prompt()
        )
        return await super().think()

    async def cleanup(self):
        """Clean up browser agent resources by calling parent cleanup."""
        await self.browser_context_helper.cleanup_browser()


def calculate_image_similarity(
    img1_base64: str, img2_base64: str, threshold: float = 0.9
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
