from pathlib import Path

_CONFIG = Path(__file__).parents[1] / "config" / "config.toml"
_CREATED = not _CONFIG.exists()
if _CREATED:
    _CONFIG.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.llm import LLM
finally:
    if _CREATED:
        _CONFIG.unlink()


def test_format_messages_keeps_caller_owned_dicts_untouched():
    message = {"role": "user", "content": "hi", "base64_image": "QUJD"}

    formatted = LLM.format_messages([message], supports_images=True)

    # The caller's message keeps its image and string content ...
    assert message == {"role": "user", "content": "hi", "base64_image": "QUJD"}
    assert formatted[0] is not message
    # ... while the formatted copy carries the image part.
    assert formatted[0]["content"][1]["image_url"]["url"].endswith("QUJD")

    # A later text-only request must not inherit the earlier image conversion.
    assert LLM.format_messages([message], supports_images=False)[0]["content"] == "hi"
