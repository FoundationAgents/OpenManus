"""PKCE primitives, the authorize/exchange wire format, and error semantics."""

import base64
import hashlib
import json

import pytest

from app.orcarouter import pkce
from app.orcarouter.constants import resolve_origins
from app.orcarouter.errors import (
    OrcaAuthError,
    OrcaAuthorizationDenied,
    OrcaAuthorizationTimeout,
    OrcaCodeRejected,
    OrcaExchangeRejected,
    OrcaNetworkError,
    OrcaRateLimited,
    OrcaScopeError,
    OrcaStateMismatch,
    constant_time_equals,
)
from tests.orcarouter.conftest import (
    FAKE_CODE,
    FAKE_KEY,
    FakeAuthServer,
    FakeLoopbackReceiver,
)


def test_verifier_is_fresh_and_from_a_crypto_rng():
    seen = {pkce.new_verifier() for _ in range(200)}
    assert len(seen) == 200
    for value in seen:
        assert 43 <= len(value) <= 128
        assert "=" not in value and "+" not in value and "/" not in value


def test_state_is_fresh_and_unpadded():
    seen = {pkce.new_state() for _ in range(200)}
    assert len(seen) == 200
    assert all("=" not in value for value in seen)


def test_challenge_is_unpadded_base64url_sha256_of_the_verifier():
    verifier = "abc123"
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    assert pkce.challenge_for(verifier) == expected
    assert "=" not in pkce.challenge_for(verifier)


def test_attempt_repr_never_contains_the_verifier():
    attempt = pkce.new_attempt("http://127.0.0.1:1234/cb")
    assert attempt.verifier not in repr(attempt)
    assert attempt.verifier not in str(attempt)


def test_callback_path_and_app_name_defaults():
    attempt = pkce.new_oob_attempt()
    assert attempt.redirect_uri == "oob"
    assert attempt.challenge == pkce.challenge_for(attempt.verifier)
    assert attempt.challenge != attempt.verifier
    assert pkce.CALLBACK_PATH == "/cb"
    assert pkce.DEFAULT_APP_NAME == "OpenManus"


def test_authorize_url_uses_the_auth_origin_and_carries_s256(origins):
    attempt = pkce.new_attempt("http://127.0.0.1:51733/cb")
    url = pkce.build_authorize_url(origins, attempt, app_name="OpenManus")
    assert url.startswith("https://www.orcarouter.ai/auth?")
    assert "code_challenge_method=S256" in url
    assert "app_name=OpenManus" in url
    assert "state=" in url
    # The verifier must never travel on the authorize URL.
    assert attempt.verifier not in url
    assert "code_verifier" not in url


def test_authorize_url_never_targets_the_inference_origin(origins):
    attempt = pkce.new_attempt("http://127.0.0.1:1/cb")
    url = pkce.build_authorize_url(origins, attempt)
    assert "api.orcarouter.ai" not in url
    assert "/v1/auth" not in url


def test_exchange_body_shape():
    attempt = pkce.new_attempt("http://127.0.0.1:1/cb")
    body = pkce.exchange_body(attempt, FAKE_CODE)
    assert body == {
        "code": FAKE_CODE,
        "code_verifier": attempt.verifier,
        "code_challenge_method": "S256",
    }
    assert set(body) == {"code", "code_verifier", "code_challenge_method"}


def test_exchange_posts_to_the_auth_origin_keys_path(origins):
    server = FakeAuthServer()
    attempt = pkce.new_attempt("http://127.0.0.1:1/cb")
    result = pkce._exchange(origins, server, attempt, FAKE_CODE)
    url, body = server.calls[-1]
    assert url == "https://www.orcarouter.ai/api/v1/auth/keys"
    assert "/v1/auth/keys" not in url.replace("/api/v1/auth/keys", "")
    assert body["code"] == FAKE_CODE
    assert body["code_verifier"] == attempt.verifier
    assert result["key"] == FAKE_KEY
    assert result["scope"] == "api"


def test_flow_a_completes_through_the_receiver(origins, no_browser):
    server = FakeAuthServer()
    receiver = FakeLoopbackReceiver(port=51733)
    attempt = pkce.new_attempt("http://127.0.0.1:51733/cb")
    result = pkce.acquire_with_receiver(
        origins, server, attempt, receiver, timeout=5, app_name="OpenManus"
    )
    assert receiver.started and receiver.state == attempt.state
    assert result["key"] == FAKE_KEY
    assert no_browser and no_browser[0].startswith("https://www.orcarouter.ai/auth?")


def test_flow_a_denial_reports_and_stores_nothing(origins, no_browser, store):
    server = FakeAuthServer()
    receiver = FakeLoopbackReceiver(port=1, kind="access_denied")
    attempt = pkce.new_attempt("http://127.0.0.1:1/cb")
    with pytest.raises(OrcaAuthorizationDenied):
        pkce.acquire_with_receiver(origins, server, attempt, receiver, timeout=5)
    assert store.get_api_key() is None
    assert server.calls == []


def test_flow_a_state_mismatch_is_rejected(origins, no_browser):
    server = FakeAuthServer()
    receiver = FakeLoopbackReceiver(port=1, kind="state_mismatch")
    attempt = pkce.new_attempt("http://127.0.0.1:1/cb")
    with pytest.raises(OrcaStateMismatch):
        pkce.acquire_with_receiver(origins, server, attempt, receiver, timeout=5)
    assert server.calls == []


def test_flow_a_timeout_is_terminal(origins, no_browser):
    class TimeoutReceiver(FakeLoopbackReceiver):
        def wait(self, timeout):
            raise OrcaAuthorizationTimeout("timed out")

    server = FakeAuthServer()
    receiver = TimeoutReceiver(port=1)
    attempt = pkce.new_attempt("http://127.0.0.1:1/cb")
    with pytest.raises(OrcaAuthorizationTimeout):
        pkce.acquire_with_receiver(origins, server, attempt, receiver, timeout=0.01)
    assert server.calls == []


def test_real_loopback_listener_delivers_the_code(origins, no_browser):
    """The real HTTP listener, exercised end to end against a fake exchange."""
    import threading
    import urllib.request

    server = FakeAuthServer()
    receiver = pkce.LoopbackReceiver()
    attempt = pkce.new_attempt(f"http://127.0.0.1:{receiver.port}/cb")
    result = {}

    def run():
        result["value"] = pkce.acquire_with_receiver(
            origins, server, attempt, receiver, timeout=5
        )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    pkce._wait_until(lambda: no_browser and no_browser[-1], timeout=5)
    with urllib.request.urlopen(
        f"http://127.0.0.1:{receiver.port}/cb"
        f"?code={FAKE_CODE}&state={attempt.state}",
        timeout=5,
    ) as response:
        page = response.read().decode()
    thread.join(timeout=5)
    assert "close this tab" in page
    assert result["value"]["key"] == FAKE_KEY


def test_real_loopback_listener_rejects_a_wrong_state(origins, no_browser):
    import threading
    import urllib.request

    server = FakeAuthServer()
    receiver = pkce.LoopbackReceiver()
    attempt = pkce.new_attempt(f"http://127.0.0.1:{receiver.port}/cb")
    errors = []

    def run():
        try:
            pkce.acquire_with_receiver(origins, server, attempt, receiver, timeout=5)
        except OrcaAuthError as exc:
            errors.append(exc)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    pkce._wait_until(lambda: no_browser and no_browser[-1], timeout=5)
    urllib.request.urlopen(
        f"http://127.0.0.1:{receiver.port}/cb?code={FAKE_CODE}&state=WRONG",
        timeout=5,
    ).read()
    thread.join(timeout=5)
    assert errors and isinstance(errors[0], OrcaStateMismatch)
    assert server.calls == []


def test_pasted_code_path_still_sends_s256(origins, no_browser):
    server = FakeAuthServer()
    attempt = pkce.new_oob_attempt()
    assert attempt.redirect_uri == "oob"
    pkce.acquire_with_pasted_code(
        origins, server, attempt, lambda: FAKE_CODE, app_name="OpenManus"
    )
    assert server.last_body["code_challenge_method"] == "S256"


def test_empty_pasted_code_is_refused(origins, no_browser):
    server = FakeAuthServer()
    attempt = pkce.new_oob_attempt()
    with pytest.raises(OrcaAuthorizationDenied):
        pkce.acquire_with_pasted_code(origins, server, attempt, lambda: "   ")
    assert server.calls == []


@pytest.mark.parametrize(
    "status,expected",
    [
        (400, OrcaExchangeRejected),
        (403, OrcaCodeRejected),
        (429, OrcaRateLimited),
        (500, OrcaAuthError),
    ],
)
def test_exchange_errors_are_classified(status, expected, origins):
    server = FakeAuthServer(status=status, body='{"error":"nope"}')
    attempt = pkce.new_attempt("http://127.0.0.1:1/cb")
    with pytest.raises(expected):
        pkce._exchange(origins, server, attempt, FAKE_CODE)


def test_error_messages_never_echo_the_verifier_or_code(origins):
    server = FakeAuthServer(status=403, body="denied")
    attempt = pkce.new_attempt("http://127.0.0.1:1/cb")
    with pytest.raises(OrcaCodeRejected) as excinfo:
        pkce._exchange(origins, server, attempt, FAKE_CODE)
    message = str(excinfo.value)
    assert attempt.verifier not in message
    assert FAKE_CODE not in message


def test_transport_failure_is_reported_without_the_request_body(origins):
    server = FakeAuthServer(raise_exc=OSError("connection refused"))
    attempt = pkce.new_attempt("http://127.0.0.1:1/cb")
    with pytest.raises(OrcaNetworkError) as excinfo:
        pkce._exchange(origins, server, attempt, FAKE_CODE)
    assert attempt.verifier not in str(excinfo.value)


def test_network_error_body_is_bounded_and_validated(origins):
    with pytest.raises(OrcaNetworkError):
        pkce.parse_exchange_body("not json")
    with pytest.raises(OrcaNetworkError):
        pkce.parse_exchange_body(json.dumps([1, 2, 3]))
    with pytest.raises(OrcaNetworkError):
        pkce.parse_exchange_body('{"key":"' + "x" * (65 * 1024) + '"}')


def test_exchange_without_a_key_is_refused(origins):
    server = FakeAuthServer(payload={"scope": "api"})
    attempt = pkce.new_attempt("http://127.0.0.1:1/cb")
    with pytest.raises(OrcaNetworkError):
        pkce._exchange(origins, server, attempt, FAKE_CODE)


def test_exchange_returning_a_foreign_credential_is_refused(origins):
    server = FakeAuthServer(payload={"key": "sk-something-else", "scope": "api"})
    attempt = pkce.new_attempt("http://127.0.0.1:1/cb")
    with pytest.raises(OrcaNetworkError):
        pkce._exchange(origins, server, attempt, FAKE_CODE)


def test_scope_downgrade_is_refused(origins):
    server = FakeAuthServer(payload={"key": FAKE_KEY, "scope": "connector"})
    attempt = pkce.new_attempt("http://127.0.0.1:1/cb")
    with pytest.raises(OrcaScopeError):
        pkce._exchange(origins, server, attempt, FAKE_CODE)


def test_granted_scope_is_read_from_the_response_not_the_request():
    # Asked for "connector", granted "api": the response wins.
    assert pkce.read_scope({"scope": "api"}) == "api"
    assert pkce.read_scope({}) == "api"
    pkce.ensure_scope_granted("api")
    with pytest.raises(OrcaScopeError):
        pkce.ensure_scope_granted("connector")


def test_account_id_prefers_the_stable_user_id():
    assert pkce._account_id({"user_id": "12345", "email": "a@b.c"}) == "12345"
    assert pkce._account_id({"email": "a@b.c"}) == "a@b.c"
    assert pkce._account_id({}) == "default"


def test_constant_time_equals():
    assert constant_time_equals("abc", "abc")
    assert not constant_time_equals("abc", "abd")
    assert not constant_time_equals("", "")
    assert not constant_time_equals(None, "abc")


def test_loopback_callback_page_tells_the_user_what_to_do(origins, no_browser):
    import threading
    import urllib.request

    server = FakeAuthServer()
    receiver = pkce.LoopbackReceiver()
    attempt = pkce.new_attempt(f"http://127.0.0.1:{receiver.port}/cb")
    thread = threading.Thread(
        target=lambda: pkce.acquire_with_receiver(
            origins, server, attempt, receiver, timeout=5
        ),
        daemon=True,
    )
    thread.start()
    pkce._wait_until(lambda: no_browser and no_browser[-1], timeout=5)
    with urllib.request.urlopen(
        f"http://127.0.0.1:{receiver.port}/cb?error=access_denied&state={attempt.state}",
        timeout=5,
    ) as response:
        page = response.read().decode()
    thread.join(timeout=5)
    assert "not completed" in page or "Return to OpenManus" in page


def test_credentials_are_never_echoed_in_reprs(store):
    from app.orcarouter.credentials import OrcaCredential

    credential = OrcaCredential(api_key=FAKE_KEY, source="api_key")
    assert FAKE_KEY not in repr(credential)
    assert FAKE_KEY not in str(credential)
    assert credential.masked.startswith("sk-orca-")
    assert credential.masked.endswith(FAKE_KEY[-4:])


def test_origins_default_to_the_documented_pair():
    resolved = resolve_origins(environ={})
    assert resolved.auth_base == "https://www.orcarouter.ai"
    assert resolved.api_base == "https://api.orcarouter.ai/v1"
    assert resolved.authorize_url == "https://www.orcarouter.ai/auth"
    assert resolved.exchange_url == "https://www.orcarouter.ai/api/v1/auth/keys"
    assert resolved.models_url == "https://api.orcarouter.ai/v1/models"


def test_explicit_overrides_win_over_the_shared_base():
    resolved = resolve_origins(
        environ={
            "ORCA_BASE_URL": "https://shared.example.com",
            "ORCA_AUTH_BASE_URL": "https://auth.example.com",
            "ORCA_API_BASE_URL": "https://infer.example.com/v1",
        }
    )
    assert resolved.auth_base == "https://auth.example.com"
    assert resolved.api_base == "https://infer.example.com/v1"


def test_shared_base_splits_without_doubling_v1():
    resolved = resolve_origins(environ={"ORCA_BASE_URL": "https://self.example.com"})
    assert resolved.auth_base == "https://self.example.com"
    assert resolved.api_base == "https://self.example.com/v1"
    resolved = resolve_origins(environ={"ORCA_BASE_URL": "https://self.example.com/v1"})
    assert resolved.auth_base == "https://self.example.com"
    assert resolved.api_base == "https://self.example.com/v1"


def test_origin_are_never_derived_from_each_other():
    resolved = resolve_origins(
        environ={"ORCA_AUTH_BASE_URL": "https://auth.example.com"}
    )
    assert resolved.api_base == "https://api.orcarouter.ai/v1"
    assert "auth.example.com" not in resolved.api_base
    resolved = resolve_origins(
        environ={"ORCA_API_BASE_URL": "https://infer.example.com/v1"}
    )
    assert resolved.auth_base == "https://www.orcarouter.ai"
    assert "infer.example.com" not in resolved.auth_base


def test_plaintext_remote_origins_are_refused():
    from app.orcarouter.errors import OrcaConfigError

    with pytest.raises(OrcaConfigError):
        resolve_origins(environ={"ORCA_AUTH_BASE_URL": "http://orcarouter.ai"})
    with pytest.raises(OrcaConfigError):
        resolve_origins(environ={"ORCA_API_BASE_URL": "http://api.orcarouter.ai/v1"})


def test_loopback_http_is_allowed_for_development():
    resolved = resolve_origins(
        environ={
            "ORCA_AUTH_BASE_URL": "http://127.0.0.1:8080",
            "ORCA_API_BASE_URL": "http://localhost:8080/v1",
        }
    )
    assert resolved.auth_base == "http://127.0.0.1:8080"
    assert resolved.api_base == "http://localhost:8080/v1"
