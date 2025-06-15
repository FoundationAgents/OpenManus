import pytest
from unittest.mock import patch
import requests
from urllib3.exceptions import MaxRetryError, NameResolutionError
import socket

# Assuming LLM and LLMSettings are importable from app.llm and app.config respectively
# Adjust the import paths if they are different based on the project structure.
# It's possible that app.llm cannot be imported directly if 'app' is not in PYTHONPATH for tests.
# If direct import fails, the test execution might require specific pytest configurations or PYTHONPATH adjustments.
# For now, assume direct import works.
from app.llm import LLM
from app.config import LLMSettings

# A mock LLMSettings configuration
mock_llm_config_data = {
    "default": {
        "model": "gpt-4.1-mini-2025-04-14", # A model that would cause the fallback
        "max_tokens": 1000,
        "temperature": 0.7,
        "api_type": "openai",
        "api_key": "test_key",
        "api_version": "N/A",  # Pydantic requires a string
        "base_url": "https://api.openai.com/v1",  # Pydantic requires a string
        "max_input_tokens": 10000,
    }
}

# Create a mock LLMSettings object
# Assuming LLMSettings can be instantiated this way or similar.
# Adjust if LLMSettings expects a different structure or Pydantic model.
mock_llm_settings = {}
for name, settings in mock_llm_config_data.items():
    provider_settings = LLMSettings(**settings)
    mock_llm_settings[name] = provider_settings


@pytest.mark.parametrize(
    "network_exception",
    [
        requests.exceptions.ConnectionError("Test ConnectionError"),
        MaxRetryError(None, "test_url", "Test MaxRetryError"),
        NameResolutionError("test_host", "test_endpoint", "Test NameResolutionError"),
        socket.gaierror("Test gaierror"),
    ],
)
# Removed patch for app.config.config.llm as it's a property and causes issues.
# Instead, we will pass mock_llm_settings directly to the LLM constructor.
def test_llm_init_network_error_handling(network_exception):
    """
    Test that LLM initialization raises RuntimeError when tiktoken.get_encoding
    fails with a network-related error.
    """
    # Ensure LLM._instances is cleared so __init__ is called.
    # This is important if LLM is a singleton and instances are cached.
    LLM._instances = {}

    with patch("tiktoken.get_encoding", side_effect=network_exception) as mock_get_encoding:
        with pytest.raises(RuntimeError) as excinfo:
            # Use a model name that is known not to be in tiktoken's default list
            # to trigger the fallback to tiktoken.get_encoding("cl100k_base")
            # Pass mock_llm_settings directly to the constructor
            LLM(config_name="default", llm_config=mock_llm_settings)

        assert "Could not initialize LLM tokenizer due to network issues" in str(excinfo.value)
        mock_get_encoding.assert_called_once_with("cl100k_base")
