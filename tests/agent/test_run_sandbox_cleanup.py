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
    import app.agent.base as base_module
    from app.agent.base import BaseAgent
    from app.llm import LLM
    from app.schema import AgentState
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class StubLLM(LLM):
    """LLM stand-in that never builds a real client or tokenizer."""

    def __new__(cls, *args, **kwargs):
        return object.__new__(cls)

    def __init__(self, *args, **kwargs):
        self.model = "stub"


class StubSandboxClient:
    """Records sandbox cleanup calls instead of touching docker."""

    def __init__(self):
        self.cleanup_calls = 0

    async def cleanup(self):
        self.cleanup_calls += 1


class StepError(RuntimeError):
    pass


class FailingAgent(BaseAgent):
    name: str = "failing"
    max_steps: int = 2

    async def step(self) -> str:
        raise StepError("step failed")


class FinishingAgent(BaseAgent):
    name: str = "finishing"
    max_steps: int = 1

    async def step(self) -> str:
        self.state = AgentState.FINISHED
        return "done"


@pytest.mark.asyncio
async def test_run_cleans_up_the_sandbox_when_a_step_raises(monkeypatch):
    sandbox_client = StubSandboxClient()
    monkeypatch.setattr(base_module, "SANDBOX_CLIENT", sandbox_client)
    agent = FailingAgent(llm=StubLLM())

    with pytest.raises(StepError):
        await agent.run("hello")

    assert sandbox_client.cleanup_calls == 1


@pytest.mark.asyncio
async def test_run_still_cleans_up_the_sandbox_on_success(monkeypatch):
    sandbox_client = StubSandboxClient()
    monkeypatch.setattr(base_module, "SANDBOX_CLIENT", sandbox_client)
    agent = FinishingAgent(llm=StubLLM())

    await agent.run("hello")

    assert sandbox_client.cleanup_calls == 1
