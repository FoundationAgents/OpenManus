import unittest
from unittest.mock import AsyncMock, patch

from app.config import config
from app.llm import LLM
from app.logger import logger
from app.schema import Message


class TestLLM(unittest.IsolatedAsyncioTestCase):
    async def test_ask_success(self):
        """Test successful LLM API call"""
        # Mock the API response
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message = AsyncMock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = AsyncMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20

        # Patch the client
        with patch("app.llm.AsyncOpenAI") as mock_client:
            mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

            # Initialize LLM with test config
            llm = LLM(config_name="test")
            llm.client = mock_client.return_value
            llm.model = "gpt-3.5-turbo"

            # Test call
            messages = [Message.user_message("Hello 你是谁？")]
            response = await llm.ask(messages, stream=False)

            self.assertEqual(response, "Test response")
            self.assertEqual(llm.total_input_tokens, 10)
            self.assertEqual(llm.total_completion_tokens, 20)

    async def test_ask_with_real_api(self):
        """Test with real API call (requires valid API key)"""
        # Skip if no API key configured
        if not config.llm["default"].api_key:
            self.skipTest("No API key configured")

        llm = LLM()
        messages = [Message.system_message("You are a helpful assistant"), Message.user_message("Hello, how are you?")]
        logger.info(f"llm_url: {llm.base_url}")

        try:
            response = await llm.ask(messages, stream=False)
            self.assertIsInstance(response, str)
            self.assertTrue(len(response) > 0)
        except Exception as e:
            if "404" in str(e):
                # Handle 404 errors specifically
                self.fail(f"API endpoint not found (404). Check base_url: {llm.base_url}")
            raise
