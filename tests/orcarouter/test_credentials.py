"""The credential seam: two adapters, one credential shape, redaction, 401."""

import os
import stat

import pytest

from app.orcarouter.constants import API_KEY_PROVIDER, PKCE_PROVIDER
from app.orcarouter.credentials import (
    ApiKeyAdapter,
    OrcaCredential,
    PkceAdapter,
    resolve_credential,
    stored_credential,
)
from app.orcarouter.errors import OrcaConfigError, redact
from app.orcarouter.provider import (
    PROVIDERS,
    client_config_for,
    is_orcarouter,
    mark_terminal_reauth,
)
from app.orcarouter.store import CredentialStore, mask_key
from tests.orcarouter.conftest import (
    FAKE_CODE,
    FAKE_KEY,
    FAKE_KEY_B,
    FakeAuthServer,
    FakeLoopbackReceiver,
)


# ------------------------------------------------------------------- store


def test_store_saves_reads_and_clears(store):
    assert store.load() is None
    record = store.save(FAKE_KEY, source="api_key")
    assert record["api_key"] == FAKE_KEY
    assert record["generation"] == 1
    assert store.get_api_key() == FAKE_KEY
    assert store.clear() is True
    assert store.load() is None
    assert store.clear() is False


def test_store_file_is_owner_only(store, tmp_path):
    store.save(FAKE_KEY, source="api_key")
    mode = stat.S_IMODE(os.stat(store.path).st_mode)
    assert mode == 0o600, oct(mode)


def test_store_refuses_an_empty_credential(store):
    with pytest.raises(OrcaConfigError):
        store.save("   ", source="api_key")


def test_mask_never_reveals_more_than_the_tail():
    assert mask_key(FAKE_KEY) == "sk-orca-…" + FAKE_KEY[-4:]
    assert mask_key(None) == ""
    assert FAKE_KEY not in mask_key(FAKE_KEY)
    assert mask_key("short") == "sk-orca-…"


def test_corrupt_store_is_treated_as_no_login(store):
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{not json", encoding="utf-8")
    assert store.load() is None
    assert store.get_api_key() is None


def test_store_generation_increments_across_logins(store):
    first = store.save(FAKE_KEY, source="api_key")
    second = store.save(FAKE_KEY_B, source="pkce")
    assert second["generation"] == first["generation"] + 1
    assert store.get_api_key() == FAKE_KEY_B


# --------------------------------------------------------------- api key


def test_api_key_adapter_uses_an_explicit_key(store):
    credential = ApiKeyAdapter(store=store, api_key=FAKE_KEY).acquire()
    assert credential.api_key == FAKE_KEY
    assert credential.source == "api_key"
    assert store.get_api_key() == FAKE_KEY


def test_api_key_adapter_uses_the_environment(store):
    credential = ApiKeyAdapter(
        store=store, environ={"ORCAROUTER_API_KEY": FAKE_KEY}
    ).acquire()
    assert credential.api_key == FAKE_KEY


def test_api_key_adapter_accepts_orca_key_as_a_fallback_env(store):
    credential = ApiKeyAdapter(store=store, environ={"ORCA_KEY": FAKE_KEY}).acquire()
    assert credential.api_key == FAKE_KEY


def test_api_key_adapter_ignores_the_shipped_placeholder(store):
    with pytest.raises(OrcaConfigError):
        ApiKeyAdapter(store=store, api_key="your OrcaRouter api key").acquire()


def test_api_key_adapter_rejects_a_foreign_key_shape(store):
    with pytest.raises(OrcaConfigError) as excinfo:
        ApiKeyAdapter(store=store, api_key="sk-openai-abc").acquire()
    assert "sk-openai-abc" not in str(excinfo.value)
    assert store.get_api_key() is None


def test_api_key_adapter_prompts_only_when_interactive(store):
    answers = []

    def prompt(message):
        answers.append(message)
        return FAKE_KEY

    credential = ApiKeyAdapter(
        store=store, prompt=prompt, interactive=True, environ={}
    ).acquire()
    assert credential.api_key == FAKE_KEY
    assert answers and "sk-orca" in answers[0]


def test_api_key_adapter_reads_a_previously_stored_key(store):
    store.save(FAKE_KEY, source="pkce")
    credential = ApiKeyAdapter(store=store, environ={}).acquire()
    assert credential.api_key == FAKE_KEY


def test_api_key_adapter_does_not_reuse_a_key_flagged_for_reauth(store):
    store.save(FAKE_KEY, source="api_key")
    store.mark_needs_reauth()
    with pytest.raises(OrcaConfigError):
        ApiKeyAdapter(store=store, environ={}).acquire()


def test_api_key_error_never_echoes_the_key(store):
    adapter = ApiKeyAdapter(store=store, api_key="sk-openai-abc")
    adapter._explicit = "sk-openai-abc"
    with pytest.raises(OrcaConfigError) as excinfo:
        adapter.acquire()
    assert "sk-openai-abc" not in str(excinfo.value)
    assert store.get_api_key() is None


def test_missing_credential_message_points_at_both_entries(store):
    with pytest.raises(OrcaConfigError) as excinfo:
        ApiKeyAdapter(store=store, environ={}).acquire()
    message = str(excinfo.value)
    assert "ORCAROUTER_API_KEY" in message
    assert "orcarouter login" in message


# -------------------------------------------------------------------- pkce


def _pkce(store, server, receiver=None, **kwargs):
    return PkceAdapter(
        store=store,
        poster=server,
        open_browser=False,
        timeout=5,
        reuse_stored=False,
        **kwargs,
    )


def test_pkce_adapter_persists_the_issued_key(store):
    server = FakeAuthServer()
    adapter = PkceAdapter(
        store=store,
        poster=server,
        open_browser=False,
        timeout=5,
        reuse_stored=False,
        receiver_factory=lambda: FakeLoopbackReceiver(port=51733),
    )
    credential = adapter.acquire()
    assert credential.api_key == FAKE_KEY
    assert credential.source == "pkce"
    assert credential.account_id == "12345"
    assert store.get_api_key() == FAKE_KEY
    assert store.load()["source"] == "pkce"
    assert store.load()["scope"] == "api"


def test_pkce_adapter_reuses_a_stored_credential(store):
    store.save(FAKE_KEY, source="pkce", account_id="12345")
    server = FakeAuthServer()
    adapter = PkceAdapter(store=store, poster=server, open_browser=False)
    credential = adapter.acquire()
    assert credential.api_key == FAKE_KEY
    # No second key was minted: the per-user cap is 10 per 24 hours.
    assert server.calls == []


def test_pkce_adapter_reuses_across_processes(store, tmp_path):
    first = PkceAdapter(
        store=store,
        poster=FakeAuthServer(),
        open_browser=False,
        timeout=5,
        reuse_stored=False,
        receiver_factory=lambda: FakeLoopbackReceiver(port=1),
    )
    first.acquire()
    # A brand new store object, as a restart would build.
    reopened = CredentialStore(tmp_path / "orcarouter.json")
    second = PkceAdapter(store=reopened, poster=FakeAuthServer(), open_browser=False)
    credential = second.acquire()
    assert credential.api_key == FAKE_KEY


def test_pkce_adapter_mints_a_fresh_key_when_reauth_is_required(store):
    store.save(FAKE_KEY, source="pkce")
    store.mark_needs_reauth()
    server = FakeAuthServer(
        payload={"key": FAKE_KEY_B, "user_id": "12345", "scope": "api"}
    )
    adapter = PkceAdapter(
        store=store,
        poster=server,
        open_browser=False,
        timeout=5,
        receiver_factory=lambda: FakeLoopbackReceiver(port=1),
    )
    credential = adapter.acquire()
    assert credential.api_key == FAKE_KEY_B
    assert len(server.calls) == 1
    assert store.load()["needs_reauth"] is False


def test_pkce_adapter_does_not_delete_the_old_secret_on_failure(store):
    store.save(FAKE_KEY, source="pkce")
    store.mark_needs_reauth()
    server = FakeAuthServer(status=403, body="denied")
    adapter = PkceAdapter(
        store=store,
        poster=server,
        open_browser=False,
        timeout=5,
        receiver_factory=lambda: FakeLoopbackReceiver(port=1),
    )
    with pytest.raises(Exception):
        adapter.acquire()
    assert store.get_api_key() == FAKE_KEY
    assert store.load()["needs_reauth"] is True


def test_pkce_acquisition_always_posts_to_the_auth_origin(store):
    server = FakeAuthServer()
    adapter = PkceAdapter(
        store=store,
        poster=server,
        open_browser=False,
        timeout=5,
        reuse_stored=False,
        receiver_factory=lambda: FakeLoopbackReceiver(port=1),
    )
    adapter.acquire()
    url, body = server.calls[0]
    assert url == "https://www.orcarouter.ai/api/v1/auth/keys"
    assert "api.orcarouter.ai" not in url
    assert body["code"] == FAKE_CODE
    assert "code_verifier" in body


def test_pkce_acquisition_with_a_pasted_code(store):
    server = FakeAuthServer()
    adapter = PkceAdapter(store=store, poster=server, open_browser=False)
    credential = adapter.acquire_with_code(FAKE_CODE)
    assert credential.api_key == FAKE_KEY
    assert server.last_body["code"] == FAKE_CODE
    assert server.last_body["code_challenge_method"] == "S256"


# ------------------------------------------------------- both adapters agree


def test_both_adapters_produce_the_same_credential_result(store, tmp_path):
    api_credential = ApiKeyAdapter(store=store, api_key=FAKE_KEY).acquire()

    pkce_store = CredentialStore(tmp_path / "pkce.json")
    pkce_credential = PkceAdapter(
        store=pkce_store,
        poster=FakeAuthServer(),
        open_browser=False,
        timeout=5,
        reuse_stored=False,
        receiver_factory=lambda: FakeLoopbackReceiver(port=1),
    ).acquire()

    assert type(api_credential) is type(pkce_credential) is OrcaCredential
    assert api_credential.api_key == pkce_credential.api_key
    assert api_credential.scope == pkce_credential.scope == "api"


def test_downstream_client_config_ignores_the_credential_source(store, tmp_path):
    ApiKeyAdapter(store=store, api_key=FAKE_KEY).acquire()
    from_key = client_config_for(API_KEY_PROVIDER, store=store, environ={})

    pkce_store = CredentialStore(tmp_path / "pkce.json")
    PkceAdapter(
        store=pkce_store,
        poster=FakeAuthServer(),
        open_browser=False,
        timeout=5,
        reuse_stored=False,
        receiver_factory=lambda: FakeLoopbackReceiver(port=1),
    ).acquire()
    from_pkce = client_config_for(PKCE_PROVIDER, store=pkce_store, environ={})

    assert from_key.api_key == from_pkce.api_key == FAKE_KEY
    assert from_key.base_url == from_pkce.base_url == "https://api.orcarouter.ai/v1"


def test_client_config_never_targets_the_auth_origin(store):
    ApiKeyAdapter(store=store, api_key=FAKE_KEY).acquire()
    resolved = client_config_for(API_KEY_PROVIDER, store=store, environ={})
    assert resolved.base_url == "https://api.orcarouter.ai/v1"
    assert "www.orcarouter.ai" not in resolved.base_url
    assert not resolved.base_url.endswith("/auth")


def test_client_config_prefers_a_configured_key_over_the_store(store, monkeypatch):
    monkeypatch.setenv("ORCAROUTER_API_KEY", FAKE_KEY_B)
    resolved = client_config_for(
        API_KEY_PROVIDER, configured_api_key=FAKE_KEY, store=store, environ={}
    )
    assert resolved.api_key == FAKE_KEY


def test_client_config_honours_an_explicit_base_url(store):
    resolved = client_config_for(
        API_KEY_PROVIDER,
        configured_api_key=FAKE_KEY,
        configured_base_url="https://self.example.com/v1",
        store=store,
        environ={},
    )
    assert resolved.base_url == "https://self.example.com/v1"


def test_client_config_reads_the_environment_without_a_login(store):
    resolved = client_config_for(
        API_KEY_PROVIDER, store=store, environ={"ORCAROUTER_API_KEY": FAKE_KEY}
    )
    assert resolved.api_key == FAKE_KEY


def test_client_config_for_the_oauth_provider_without_a_login_is_actionable(store):
    with pytest.raises(OrcaConfigError) as excinfo:
        client_config_for(PKCE_PROVIDER, store=store, environ={})
    assert "orcarouter login" in str(excinfo.value)


def test_resolve_credential_dispatches_on_the_provider_id(store):
    credential = resolve_credential(
        API_KEY_PROVIDER, store=store, api_key=FAKE_KEY, environ={}
    )
    assert credential.source == "api_key"
    with pytest.raises(OrcaConfigError):
        resolve_credential("not-an-orcarouter-provider", store=store, environ={})


def test_provider_ids_are_registered_and_labelled_distinctly():
    assert is_orcarouter(API_KEY_PROVIDER)
    assert is_orcarouter(PKCE_PROVIDER)
    assert is_orcarouter("OrcaRouter")
    assert not is_orcarouter("openai")
    assert not is_orcarouter(None)
    labels = {spec.label for spec in PROVIDERS.values()}
    assert labels == {"OrcaRouter - API", "OrcaRouter - Auth"}
    assert PROVIDERS[PKCE_PROVIDER].is_oauth
    assert not PROVIDERS[API_KEY_PROVIDER].is_oauth


def test_stored_credential_is_independent_of_its_source(store):
    store.save(FAKE_KEY, source="pkce")
    credential = stored_credential(store=store, environ={})
    assert credential.api_key == FAKE_KEY
    store.save(FAKE_KEY_B, source="api_key")
    credential = stored_credential(store=store, environ={})
    assert credential.api_key == FAKE_KEY_B


# ------------------------------------------------------------- terminal 401


def test_401_marks_the_exact_account_and_generation(store):
    record = store.save(FAKE_KEY, source="pkce", account_id="12345")
    credential = OrcaCredential(
        api_key=FAKE_KEY,
        source="pkce",
        account_id="12345",
        generation=record["generation"],
    )
    assert mark_terminal_reauth(credential, store=store) is True
    assert store.needs_reauth() is True
    # The secret is kept: only a successful new login replaces it.
    assert store.get_api_key() == FAKE_KEY
    assert stored_credential(store=store, environ={}) is None


def test_a_stale_generation_cannot_mark_a_fresh_credential(store):
    old = store.save(FAKE_KEY, source="pkce", account_id="12345")
    stale = OrcaCredential(
        api_key=FAKE_KEY,
        source="pkce",
        account_id="12345",
        generation=old["generation"],
    )
    # A new login happens while the old request is still in flight.
    fresh = store.save(FAKE_KEY_B, source="pkce", account_id="12345")
    assert fresh["generation"] == old["generation"] + 1
    # The late 401 from the superseded request must not poison the new key.
    assert mark_terminal_reauth(stale, store=store) is False
    assert store.needs_reauth() is False
    assert store.get_api_key() == FAKE_KEY_B


def test_a_401_for_another_account_is_ignored(store):
    store.save(FAKE_KEY, source="pkce", account_id="12345")
    other = OrcaCredential(
        api_key=FAKE_KEY, source="pkce", account_id="99999", generation=1
    )
    assert mark_terminal_reauth(other, store=store) is False
    assert store.needs_reauth() is False


def test_401_without_a_credential_is_a_no_op(store):
    assert mark_terminal_reauth(None, store=store) is False


def test_reauth_marking_is_idempotent(store):
    record = store.save(FAKE_KEY, source="pkce", account_id="12345")
    credential = OrcaCredential(
        api_key=FAKE_KEY,
        source="pkce",
        account_id="12345",
        generation=record["generation"],
    )
    assert mark_terminal_reauth(credential, store=store) is True
    assert mark_terminal_reauth(credential, store=store) is False


def test_no_refresh_grant_is_ever_attempted(store, monkeypatch):
    """A revoked durable key is terminal; nothing tries to refresh it."""
    record = store.save(FAKE_KEY, source="pkce", account_id="12345")
    credential = OrcaCredential(
        api_key=FAKE_KEY,
        source="pkce",
        account_id="12345",
        generation=record["generation"],
    )
    mark_terminal_reauth(credential, store=store)
    assert credential.source == "pkce"
    assert not hasattr(credential, "refresh_token")
    assert not hasattr(credential, "expires_at")


# ---------------------------------------------------------------- redaction


def test_redact_removes_known_and_recognisable_secrets():
    assert FAKE_KEY not in redact(f"failed with {FAKE_KEY}")
    assert "sk-orca-abcdef" not in redact("key sk-orca-abcdef leaked")
    assert "hunter2" not in redact("Authorization: Bearer hunter2token")
    assert "xyz" not in redact("https://x/cb?code=xyz&state=s")


def test_redact_handles_a_supplied_verifier():
    assert "verifier-value" not in redact("verifier=verifier-value", ["verifier-value"])


def test_error_messages_are_redacted_at_construction():
    from app.orcarouter.errors import OrcaAuthError

    error = OrcaAuthError(f"boom {FAKE_KEY}")
    assert FAKE_KEY not in str(error)
    assert error.raw_message.endswith(FAKE_KEY)  # kept for debugging, not printed
