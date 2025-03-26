import httpx

from app.logger import logger

FIREWORKS_BASE_URL = "https://api.fireworks.ai"


class UnsupportedToolsError(Exception):
    """Exception raised when a model does not support tool calling."""

    pass


def check_model_capabilities(
    model: str, api_key: str, require_tools: bool = False
) -> bool:
    """
    Check if a Fireworks model supports tools by querying the Fireworks API.

    Args:
        model: The model identifier (e.g., "accounts/<ACCOUNT_ID>/models/<MODEL_ID>" or "<MODEL_ID>")
        api_key: The Fireworks API key
        require_tools: If True, raise UnsupportedToolsError when tools are not supported

    Returns:
        bool: True if the model supports tools

    Raises:
        UnsupportedToolsError: If require_tools is True and the model doesn't support tools
    """
    try:
        # Extract account_id and model_id from the model string according to Fireworks format
        # The standard format is: accounts/<ACCOUNT_ID>/models/<MODEL_ID> or just <MODEL_ID>
        account_id = "fireworks"  # Default account
        model_id = model

        if model.startswith("accounts/"):
            # Format: accounts/<ACCOUNT_ID>/models/<MODEL_ID>
            parts = model.split("/")
            if len(parts) >= 4 and parts[0] == "accounts" and parts[2] == "models":
                account_id = parts[1]
                model_id = parts[3]

        # Make API call to get model information
        response = httpx.get(
            f"{FIREWORKS_BASE_URL}/v1/accounts/{account_id}/models/{model_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        if response.status_code == 200:
            model_info = response.json()
            supports_tools = model_info.get("supportsTools", False)
            logger.info(f"Model {model} supports tools: {supports_tools}")

            if require_tools and not supports_tools:
                model_name = model_id if model_id else model

                error_message = (
                    f"Model '{model_name}' does not support tool calling. \n"
                    f"Please use a model known to support function calling like 'accounts/fireworks/models/llama-v3p1-405b-instruct', "
                    f"or check https://docs.fireworks.ai/guides/function-calling#supported-models for the latest list."
                )
                raise UnsupportedToolsError(error_message)

            return supports_tools
        else:
            logger.warning(
                f"Failed to get model info: {response.status_code} {response.text}"
            )
            if require_tools:
                error_message = (
                    f"Failed to verify tool support for model '{model}'. "
                    f"Error code: {response.status_code}. "
                    f"Please check:\n"
                    f"1. The model ID is correct\n"
                    f"2. Your API key has permission to access this model\n"
                    f"3. The model exists on Fireworks.ai\n\n"
                    f"Try using a model known to support function calling like 'accounts/fireworks/models/llama-v3p1-405b-instruct', "
                    f"or check https://docs.fireworks.ai/guides/function-calling#supported-models for the latest list."
                )
                raise UnsupportedToolsError(error_message)
            return False
    except UnsupportedToolsError:
        raise
    except Exception as e:
        logger.warning(f"Error checking model capabilities: {e}")
        if require_tools:
            error_message = (
                f"Error verifying tool support for model '{model}': {e}\n"
                f"If you need to use tools/function calling, please:\n"
                f"1. Check your network connection\n"
                f"2. Verify your Fireworks API key is valid\n"
                f"3. Try using a known supported model like 'accounts/fireworks/models/llama-v3p1-405b-instruct'\n"
                f"4. If the issue persists, contact Fireworks support"
            )
            raise UnsupportedToolsError(error_message)
        return False
