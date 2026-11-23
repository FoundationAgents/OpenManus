import asyncio
import threading
from pathlib import Path

import pytest


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.tool.ask_human import AskHuman
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


@pytest.mark.asyncio
async def test_waiting_for_console_input_allows_other_async_work(monkeypatch):
    loop = asyncio.get_running_loop()
    progressed = threading.Event()
    progress_during_input = []

    def input_while_waiting(prompt):
        loop.call_soon_threadsafe(progressed.set)
        progress_during_input.append(progressed.wait(timeout=2))
        return "  continue  "

    monkeypatch.setattr("builtins.input", input_while_waiting)

    result = await AskHuman()(inquire="Continue?")

    assert result == "continue"
    assert progress_during_input == [True]


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["  yes  ", "", "\n继续\t"])
async def test_console_prompt_and_trimmed_answer_are_preserved(monkeypatch, answer):
    prompts = []

    def answer_prompt(prompt):
        prompts.append(prompt)
        return answer

    monkeypatch.setattr("builtins.input", answer_prompt)

    assert await AskHuman()(inquire="What next?") == answer.strip()
    assert prompts == ["Bot: What next?\n\nYou: "]


@pytest.mark.asyncio
async def test_console_eof_is_still_reported_to_the_caller(monkeypatch):
    def closed_input(prompt):
        raise EOFError("console closed")

    monkeypatch.setattr("builtins.input", closed_input)

    with pytest.raises(EOFError, match="console closed"):
        await AskHuman()(inquire="Continue?")
