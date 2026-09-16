"""Shared helpers for the OrcaRouter tests.

Nothing here contains a real credential: every key, code and verifier used by
these tests is a fake literal, and the fake auth server never contacts
OrcaRouter.
"""

import atexit
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest


# ``app.config`` requires a ``config/config.toml`` with a ``[daytona]`` table on
# a fresh checkout (``config.example.toml`` has none, and ``daytona_api_key`` is
# a required field), so ``import app.config`` raises before any test runs. This
# is pre-existing and unrelated to the OrcaRouter change; the workaround is the
# one ``tests/tools/test_browser_use_mcp.py`` already uses, applied for the
# whole session instead of a single test.
_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )
    atexit.register(lambda: _CONFIG_PATH.exists() and _CONFIG_PATH.unlink())


from app.orcarouter.constants import OrcaOrigins  # noqa: E402
from app.orcarouter.store import CredentialStore  # noqa: E402


FAKE_KEY = "sk-orca-test-0000000000000000000000000000"
FAKE_KEY_B = "sk-orca-test-1111111111111111111111111111"
FAKE_CODE = "FAKE-CODE-NOT-REAL"
FAKE_VERIFIER = "fake-verifier-not-real-0000000000000000"


@pytest.fixture(autouse=True)
def isolate_orcarouter_env(monkeypatch):
    """Keep the real environment out of every unit test.

    A developer machine (or CI) may legitimately export ``ORCAROUTER_API_KEY``.
    No unit test should read it: the live checks capture it explicitly and pass
    it in, so every other test sees a clean environment and cannot accidentally
    assert against, or print, a real credential.
    """
    for name in (
        "ORCAROUTER_API_KEY",
        "ORCA_KEY",
        "ORCA_BASE_URL",
        "ORCA_AUTH_BASE_URL",
        "ORCA_API_BASE_URL",
        "ORCA_CREDENTIAL_FILE",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def store(tmp_path) -> CredentialStore:
    return CredentialStore(tmp_path / "orcarouter.json")


@pytest.fixture
def origins() -> OrcaOrigins:
    return OrcaOrigins("https://www.orcarouter.ai", "https://api.orcarouter.ai/v1")


class FakeAuthServer:
    """A stand-in for ``POST /api/v1/auth/keys`` on the auth origin.

    Records every request so a test can assert the exchange went to the auth
    origin with the documented path and body.
    """

    def __init__(
        self,
        status: int = 200,
        payload: Optional[Dict[str, object]] = None,
        body: Optional[str] = None,
        raise_exc: Optional[BaseException] = None,
    ):
        self.status = status
        self.payload = (
            payload
            if payload is not None
            else {
                "key": FAKE_KEY,
                "user_id": "12345",
                "scope": "api",
            }
        )
        self.body = body
        self.raise_exc = raise_exc
        self.calls: List[Tuple[str, Dict[str, str]]] = []

    def __call__(self, url: str, body: Dict[str, str]) -> Tuple[int, str]:
        self.calls.append((url, dict(body)))
        if self.raise_exc is not None:
            raise self.raise_exc
        if self.body is not None:
            return self.status, self.body
        return self.status, json.dumps(self.payload)

    @property
    def last_body(self) -> Dict[str, str]:
        return self.calls[-1][1]


class FakeCatalogServer:
    """A stand-in for ``GET {api_base}/models``."""

    def __init__(
        self, status: int = 200, payload: object = None, body: Optional[str] = None
    ):
        self.status = status
        self.payload = payload
        self.body = body
        self.calls: List[Tuple[str, Dict[str, str]]] = []

    def __call__(self, url: str, headers: Dict[str, str], timeout: float):
        self.calls.append((url, dict(headers)))
        if self.body is not None:
            return self.status, self.body
        return self.status, json.dumps(self.payload if self.payload is not None else {})


def model_payload(*records: Dict[str, object]) -> Dict[str, object]:
    """Wrap records the way ``GET /v1/models`` does."""
    return {"object": "list", "data": list(records)}


def chat_record(model_id: str, **overrides) -> Dict[str, object]:
    record = {
        "id": model_id,
        "object": "model",
        "created": 1626777600,
        "owned_by": "custom",
        "supported_endpoint_types": ["openai", "openai-response"],
        "name": model_id,
        "context_length": 128000,
        "max_completion_tokens": 8192,
        "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
    }
    record.update(overrides)
    return record


class FakeLoopbackReceiver:
    """Delivers a callback to the PKCE flow without opening a socket."""

    def __init__(self, port: int, kind: str = "ok", value: str = FAKE_CODE):
        self.port = port
        self.kind = kind
        self.value = value
        self.state: Optional[str] = None
        self.started = False
        self.closed = False

    def start(self, state: str) -> None:
        self.started = True
        self.state = state

    def wait(self, timeout: float) -> Tuple[str, str]:
        from app.orcarouter.errors import (
            OrcaAuthError,
            OrcaAuthorizationDenied,
            OrcaStateMismatch,
        )

        if self.kind == "state_mismatch":
            raise OrcaStateMismatch("state mismatch")
        if self.kind == "access_denied":
            raise OrcaAuthorizationDenied("access_denied")
        if self.kind != "ok":
            raise OrcaAuthError(self.kind)
        return "ok", self.value

    def close(self) -> None:
        self.closed = True


def thread_event() -> threading.Event:
    return threading.Event()


@pytest.fixture
def no_browser(monkeypatch):
    """Never try to open a real browser during tests."""
    import app.orcarouter.pkce as pkce_module

    calls = []

    def fake_open(url, new=0, autoraise=True):
        calls.append(url)
        return False

    monkeypatch.setattr(pkce_module.webbrowser, "open", fake_open)
    return calls
