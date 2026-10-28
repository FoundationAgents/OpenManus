from pathlib import Path


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.llm import LLM, supports_image_input
    from app.schema import Message
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


def test_default_config_model_accepts_images():
    assert supports_image_input("claude-3-7-sonnet-20250219")


def test_dated_snapshots_and_provider_prefixed_ids():
    assert supports_image_input("claude-3-5-sonnet-20241022")
    assert supports_image_input("us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    assert supports_image_input("gpt-4o-2024-11-20")
    assert supports_image_input("gemini-2.0-flash-exp")
    assert supports_image_input("qwen/qwen2.5-vl-72b-instruct")
    assert supports_image_input("llama3.2-vision")


def test_text_only_models_are_not_treated_as_multimodal():
    for model in ("deepseek-chat", "llama3.2", "qwen2.5-72b-instruct"):
        assert not supports_image_input(model)
    assert not supports_image_input("")


def test_format_messages_keeps_images_for_supported_models():
    message = Message.user_message("what is on screen?", base64_image="cG5n")

    formatted = LLM.format_messages(
        [message], supports_images=supports_image_input("claude-3-7-sonnet-20250219")
    )

    assert "image_url" in str(formatted)


def test_format_messages_drops_images_for_text_only_models():
    message = Message.user_message("hello", base64_image="cG5n")

    formatted = LLM.format_messages(
        [message], supports_images=supports_image_input("deepseek-chat")
    )

    assert "image_url" not in str(formatted)
