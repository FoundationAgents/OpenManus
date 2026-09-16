"""Integration: provider registration, the LLM seam, the CLI, and live calls.

Live checks are skipped unless ``ORCAROUTER_API_KEY`` is set. When it is set
they run through the provider code path this change implements - the credential
seam, the catalog service and an ``AsyncOpenAI`` client built from
``client_config_for`` - rather than a hand-rolled curl.
"""

import asyncio
import json
import os

import pytest

from app.orcarouter.catalog import (
    ModelCatalog,
    filter_models,
    reset_shared_catalog,
    shared_catalog,
)
from app.orcarouter.cli import main as orca_main
from app.orcarouter.constants import API_KEY_PROVIDER, PKCE_PROVIDER, resolve_origins
from app.orcarouter.credentials import ApiKeyAdapter
from app.orcarouter.provider import client_config_for
from app.orcarouter.store import CredentialStore
from tests.orcarouter.conftest import (
    FAKE_KEY,
    FakeCatalogServer,
    chat_record,
    model_payload,
)


LIVE_KEY = os.environ.get("ORCAROUTER_API_KEY")
requires_live_key = pytest.mark.skipif(
    not LIVE_KEY, reason="ORCAROUTER_API_KEY is not set"
)


# --------------------------------------------------------------- LLM seam


def _llm_settings(**overrides):
    from app.config import LLMSettings

    settings = {
        "model": "orcarouter/auto",
        "base_url": "",
        "api_key": "",
        "max_tokens": 1024,
        "temperature": 0.0,
        "api_type": API_KEY_PROVIDER,
        "api_version": "",
    }
    settings.update(overrides)
    return LLMSettings(**settings)


def test_llm_seam_builds_an_openai_client_against_the_relay(monkeypatch, tmp_path):
    from app.llm import LLM

    store = CredentialStore(tmp_path / "c.json")
    ApiKeyAdapter(store=store, api_key=FAKE_KEY).acquire()
    monkeypatch.setattr("app.orcarouter.store.default_store_path", lambda: store.path)

    LLM._instances.clear()
    llm = LLM("orcarouter-integration", {"default": _llm_settings()})
    assert str(llm.client.base_url).rstrip("/") == "https://api.orcarouter.ai/v1"
    assert llm.client.api_key == FAKE_KEY
    assert llm.api_key == FAKE_KEY
    assert "www.orcarouter.ai" not in str(llm.client.base_url)
    LLM._instances.clear()


def test_llm_seam_covers_both_provider_ids(monkeypatch, tmp_path):
    from app.llm import LLM

    store = CredentialStore(tmp_path / "c.json")
    ApiKeyAdapter(store=store, api_key=FAKE_KEY).acquire()
    monkeypatch.setattr("app.orcarouter.store.default_store_path", lambda: store.path)
    LLM._instances.clear()

    for index, provider in enumerate((API_KEY_PROVIDER, PKCE_PROVIDER)):
        llm = LLM(f"orca-{index}", {"default": _llm_settings(api_type=provider)})
        assert str(llm.client.base_url).rstrip("/") == "https://api.orcarouter.ai/v1"
        assert llm.client.api_key == FAKE_KEY
    LLM._instances.clear()


def test_llm_seam_leaves_other_providers_alone():
    from app.llm import LLM

    LLM._instances.clear()
    llm = LLM(
        "plain-openai",
        {
            "default": _llm_settings(
                api_type="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-openai-placeholder",
            )
        },
    )
    assert str(llm.client.base_url).rstrip("/") == "https://api.openai.com/v1"
    assert llm.client.api_key == "sk-openai-placeholder"
    assert not hasattr(llm, "orca_credential")
    LLM._instances.clear()


def test_llm_seam_raises_an_actionable_error_without_a_credential(
    monkeypatch, tmp_path
):
    from app.llm import LLM
    from app.orcarouter.errors import OrcaConfigError

    store = CredentialStore(tmp_path / "empty.json")
    monkeypatch.setattr("app.orcarouter.store.default_store_path", lambda: store.path)
    monkeypatch.delenv("ORCAROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ORCA_KEY", raising=False)
    LLM._instances.clear()
    with pytest.raises(OrcaConfigError) as excinfo:
        LLM("orca-missing", {"default": _llm_settings()})
    assert "ORCAROUTER_API_KEY" in str(excinfo.value)
    LLM._instances.clear()


def test_401_marks_the_rejected_generation_through_the_provider_layer(
    monkeypatch, tmp_path
):
    import openai

    from app.llm import LLM

    store = CredentialStore(tmp_path / "c.json")
    monkeypatch.setattr("app.orcarouter.store.default_store_path", lambda: store.path)
    ApiKeyAdapter(store=store, api_key=FAKE_KEY).acquire()

    LLM._instances.clear()
    llm = LLM("orca-401", {"default": _llm_settings()})
    assert llm.orca_credential is not None

    llm._handle_orcarouter_unauthorized(
        openai.AuthenticationError("revoked", response=httpx_request(), body=None)
    )
    record = store.load()
    assert record["needs_reauth"] is True
    assert record["api_key"] == FAKE_KEY  # never silently deleted
    LLM._instances.clear()


def test_401_handling_is_inert_for_other_providers(tmp_path, monkeypatch):
    from app.llm import LLM

    store = CredentialStore(tmp_path / "c.json")
    monkeypatch.setattr("app.orcarouter.store.default_store_path", lambda: store.path)
    LLM._instances.clear()
    llm = LLM(
        "plain-401",
        {
            "default": _llm_settings(
                api_type="openai",
                base_url="https://api.openai.com/v1",
                api_key="sk-openai-placeholder",
            )
        },
    )
    llm._handle_orcarouter_unauthorized(RuntimeError("x"))
    assert store.load() is None
    LLM._instances.clear()


def httpx_request():
    import httpx

    return httpx.Response(
        401,
        request=httpx.Request("POST", "https://api.orcarouter.ai/v1/chat/completions"),
        json={"error": {"message": "revoked"}},
    )


# ------------------------------------------------- catalog-driven attachments


@pytest.fixture
def live_catalog_server(monkeypatch, tmp_path):
    """Point the shared catalog at a fake relay, and store a fake credential.

    The catalog is the same object every entry point would use, so these checks
    exercise the real wiring rather than a per-test copy.
    """
    from app.orcarouter.constants import resolve_origins

    store = CredentialStore(tmp_path / "c.json")
    ApiKeyAdapter(store=store, api_key=FAKE_KEY).acquire()
    monkeypatch.setattr("app.orcarouter.store.default_store_path", lambda: store.path)

    reset_shared_catalog()
    catalog = shared_catalog(origins=resolve_origins())
    catalog._fetcher = FakeCatalogServer(
        payload=model_payload(
            chat_record("vendor/text-only"),
            chat_record(
                "vendor/vision-chat",
                architecture={
                    "input_modalities": ["text", "image"],
                    "output_modalities": ["text"],
                },
            ),
        )
    )
    catalog._records = None
    catalog.source = "unresolved"
    catalog.refresh(api_key=FAKE_KEY)
    yield catalog
    reset_shared_catalog()


def _image_message():
    from app.schema import Message

    return Message.user_message(content="what is this?", base64_image="ZmFrZQ==")


def test_a_text_only_orcarouter_model_refuses_an_attached_image(live_catalog_server):
    """Fail closed instead of silently answering a screenshot with text only."""
    from app.llm import LLM
    from app.orcarouter.errors import OrcaConfigError

    LLM._instances.clear()
    llm = LLM(
        "orca-image-guard",
        {"default": _llm_settings(model="vendor/text-only")},
    )
    assert llm._supports_images() is False
    with pytest.raises(OrcaConfigError) as excinfo:
        llm._guard_orcarouter_image([_image_message()])
    message = str(excinfo.value)
    assert "vendor/text-only" in message
    assert "chat_vision" in message
    LLM._instances.clear()


def test_a_vision_orcarouter_model_keeps_the_image(live_catalog_server):
    from app.llm import LLM

    LLM._instances.clear()
    llm = LLM("orca-image-ok", {"default": _llm_settings(model="vendor/vision-chat")})
    assert llm._supports_images() is True
    llm._guard_orcarouter_image([_image_message()])
    formatted = LLM.format_messages([_image_message()], llm._supports_images())
    assert formatted[-1]["content"][-1]["type"] == "image_url"
    LLM._instances.clear()


def test_an_orcarouter_model_the_catalog_does_not_list_refuses_an_image(
    live_catalog_server,
):
    """A hand-set model id the catalog never vouched for fails closed."""
    from app.llm import LLM
    from app.orcarouter.errors import OrcaConfigError

    LLM._instances.clear()
    llm = LLM("orca-image-unknown", {"default": _llm_settings(model="vendor/stranger")})
    with pytest.raises(OrcaConfigError):
        llm._guard_orcarouter_image([_image_message()])
    LLM._instances.clear()


def test_other_providers_keep_the_existing_name_list(tmp_path, monkeypatch):
    from app.llm import LLM

    monkeypatch.setattr(
        "app.orcarouter.store.default_store_path", lambda: tmp_path / "none.json"
    )
    LLM._instances.clear()
    llm = LLM(
        "plain-vision",
        {
            "default": _llm_settings(
                api_type="openai",
                model="gpt-4o",
                base_url="https://api.openai.com/v1",
                api_key="sk-openai-placeholder",
            )
        },
    )
    # No catalog lookup happens for a non-OrcaRouter provider.
    assert llm._orca_image_capability() is None
    assert llm._supports_images() is True
    llm._guard_orcarouter_image([_image_message()])
    LLM._instances.clear()


# ------------------------------------------------------------ config layer


def test_config_resolves_an_empty_orcarouter_api_key_from_the_seam(
    monkeypatch, tmp_path
):
    from app.config import _resolve_orcarouter_settings

    store = CredentialStore(tmp_path / "c.json")
    ApiKeyAdapter(store=store, api_key=FAKE_KEY).acquire()
    monkeypatch.setattr("app.orcarouter.store.default_store_path", lambda: store.path)

    settings = _resolve_orcarouter_settings(
        {
            "model": "orcarouter/auto",
            "base_url": "",
            "api_key": "",
            "max_tokens": 1024,
            "temperature": 0.0,
            "api_type": API_KEY_PROVIDER,
            "api_version": "",
        }
    )
    assert settings.api_key == FAKE_KEY
    assert settings.base_url == "https://api.orcarouter.ai/v1"


def test_config_keeps_an_explicit_api_key():
    from app.config import _resolve_orcarouter_settings

    settings = _resolve_orcarouter_settings(
        {
            "model": "orcarouter/auto",
            "base_url": "https://api.orcarouter.ai/v1",
            "api_key": FAKE_KEY,
            "max_tokens": 1024,
            "temperature": 0.0,
            "api_type": API_KEY_PROVIDER,
            "api_version": "",
        }
    )
    assert settings.api_key == FAKE_KEY


def test_config_does_not_fail_startup_without_a_credential(monkeypatch, tmp_path):
    from app.config import _resolve_orcarouter_settings

    store = CredentialStore(tmp_path / "empty.json")
    monkeypatch.setattr("app.orcarouter.store.default_store_path", lambda: store.path)
    monkeypatch.delenv("ORCAROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ORCA_KEY", raising=False)
    settings = _resolve_orcarouter_settings(
        {
            "model": "orcarouter/auto",
            "base_url": "https://api.orcarouter.ai/v1",
            "api_key": "",
            "max_tokens": 1024,
            "temperature": 0.0,
            "api_type": PKCE_PROVIDER,
            "api_version": "",
        }
    )
    assert settings.base_url == "https://api.orcarouter.ai/v1"


def test_config_leaves_other_providers_untouched():
    from app.config import _resolve_orcarouter_settings

    settings = _resolve_orcarouter_settings(
        {
            "model": "gpt-4o",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-openai-placeholder",
            "max_tokens": 1024,
            "temperature": 0.0,
            "api_type": "openai",
            "api_version": "",
        }
    )
    assert settings.api_key == "sk-openai-placeholder"
    assert settings.base_url == "https://api.openai.com/v1"


# ------------------------------------------------------------------- CLI


def test_cli_exposes_both_authentication_entries(tmp_path, capsys):
    from app.orcarouter import cli

    parser = cli.build_parser()
    help_text = parser.format_help()
    assert "login" in help_text
    assert "models" in help_text

    login_help = parser._subparsers._group_actions[0].choices["login"].format_help()
    assert "--api-key" in login_help
    assert PKCE_PROVIDER in login_help
    assert API_KEY_PROVIDER in login_help


def test_cli_login_stores_an_api_key(tmp_path, monkeypatch, capsys):
    store = CredentialStore(tmp_path / "c.json")
    monkeypatch.setattr("app.orcarouter.cli.CredentialStore", lambda: store)
    assert orca_main(["login", "--api-key", FAKE_KEY, "--no-browser"]) == 0
    assert store.get_api_key() == FAKE_KEY
    out = capsys.readouterr().out
    assert FAKE_KEY not in out  # the credential is never printed in full
    assert "sk-orca-…" in out


def test_cli_status_reports_the_masked_credential(tmp_path, monkeypatch, capsys):
    store = CredentialStore(tmp_path / "c.json")
    ApiKeyAdapter(store=store, api_key=FAKE_KEY).acquire()
    monkeypatch.setattr("app.orcarouter.cli.CredentialStore", lambda: store)
    assert orca_main(["status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["masked_key"].startswith("sk-orca-…")
    assert payload["source"] == "api_key"
    assert FAKE_KEY not in json.dumps(payload)


def test_cli_key_is_masked_unless_revealed(tmp_path, monkeypatch, capsys):
    store = CredentialStore(tmp_path / "c.json")
    ApiKeyAdapter(store=store, api_key=FAKE_KEY).acquire()
    monkeypatch.setattr("app.orcarouter.cli.CredentialStore", lambda: store)

    assert orca_main(["key"]) == 0
    assert FAKE_KEY not in capsys.readouterr().out
    assert orca_main(["key", "--reveal"]) == 0
    assert capsys.readouterr().out.strip() == FAKE_KEY


def test_cli_logout_clears_the_credential(tmp_path, monkeypatch, capsys):
    store = CredentialStore(tmp_path / "c.json")
    ApiKeyAdapter(store=store, api_key=FAKE_KEY).acquire()
    monkeypatch.setattr("app.orcarouter.cli.CredentialStore", lambda: store)
    assert orca_main(["logout"]) == 0
    assert store.get_api_key() is None


def test_cli_key_without_a_credential_fails_cleanly(tmp_path, monkeypatch, capsys):
    store = CredentialStore(tmp_path / "c.json")
    monkeypatch.setattr("app.orcarouter.cli.CredentialStore", lambda: store)
    assert orca_main(["key"]) == 1
    assert "No OrcaRouter credential" in capsys.readouterr().err


def test_cli_models_reports_a_degraded_catalog(tmp_path, monkeypatch, capsys):
    from app.orcarouter import cli

    store = CredentialStore(tmp_path / "c.json")
    monkeypatch.setattr("app.orcarouter.cli.CredentialStore", lambda: store)
    monkeypatch.setattr(
        cli,
        "ModelCatalog",
        lambda origins=None: _degraded_catalog(),
    )
    assert orca_main(["models", "--capability", "chat"]) == 0
    out = capsys.readouterr().out
    assert "verified_seed" in out
    assert "degraded" in out


def _degraded_catalog():
    def boom(url, headers, timeout):
        raise OSError("down")

    return ModelCatalog(fetcher=boom)


def test_cli_models_flags_an_invalidated_selection(tmp_path, monkeypatch, capsys):
    from app.orcarouter import cli

    store = CredentialStore(tmp_path / "c.json")
    monkeypatch.setattr("app.orcarouter.cli.CredentialStore", lambda: store)
    monkeypatch.setattr(cli, "ModelCatalog", lambda origins=None: _live_catalog())
    code = orca_main(
        [
            "models",
            "--capability",
            "chat",
            "--selected",
            "vendor/image-gen",
        ]
    )
    assert code == 2
    assert "not compatible" in capsys.readouterr().out


def _live_catalog():
    payload = model_payload(
        chat_record("vendor/text-only"),
        {
            "id": "vendor/image-gen",
            "supported_endpoint_types": ["image-generation"],
            "architecture": {
                "input_modalities": ["text"],
                "output_modalities": ["image"],
            },
        },
    )
    return ModelCatalog(fetcher=FakeCatalogServer(payload=payload))


def test_cli_doctor_prints_both_origins(tmp_path, monkeypatch, capsys):
    from app.orcarouter import cli

    store = CredentialStore(tmp_path / "c.json")
    store.save(FAKE_KEY, source="api_key")
    monkeypatch.setattr("app.orcarouter.cli.CredentialStore", lambda: store)
    monkeypatch.setattr(cli, "ModelCatalog", lambda origins=None: _live_catalog())
    assert orca_main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "auth origin: https://www.orcarouter.ai" in out
    assert "inference origin: https://api.orcarouter.ai/v1" in out
    assert "https://www.orcarouter.ai/api/v1/auth/keys" in out
    assert FAKE_KEY not in out


def test_cli_reports_errors_without_a_traceback(tmp_path, monkeypatch, capsys):
    store = CredentialStore(tmp_path / "c.json")
    monkeypatch.setattr("app.orcarouter.cli.CredentialStore", lambda: store)
    monkeypatch.delenv("ORCAROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ORCA_KEY", raising=False)
    assert orca_main(["login", "--api-key", "not-an-orca-key"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "not-an-orca-key" not in err


# ------------------------------------------------------------- live checks


@requires_live_key
def test_live_catalog_lists_real_models_through_the_provider():
    """GET https://api.orcarouter.ai/v1/models via the implemented service."""
    origins = resolve_origins(environ={})
    assert origins.models_url == "https://api.orcarouter.ai/v1/models"
    catalog = ModelCatalog(origins=origins)
    catalog.refresh(api_key=LIVE_KEY)
    status = catalog.status()
    assert status["source"] == "live", status
    assert status["model_count"] > 0
    ids = [r.id for r in catalog.records]
    assert all("/" in model_id for model_id in ids)  # vendor namespace kept
    chat = filter_models(catalog.records, "chat")
    assert chat, "no chat-capable model was advertised"
    print(f"live catalog: {status['model_count']} models, {len(chat)} chat-capable")


@requires_live_key
def test_live_catalog_filters_multimodal_fail_closed():
    catalog = ModelCatalog(origins=resolve_origins(environ={}))
    catalog.refresh(api_key=LIVE_KEY)
    vision = filter_models(catalog.records, "chat_vision")
    for record in vision:
        assert "image" in record.input_modalities
    for record in filter_models(catalog.records, "chat"):
        if record not in vision:
            assert "image" not in record.input_modalities


@requires_live_key
def test_live_inference_request_through_the_implemented_provider():
    """One real chat completion, built from the provider code path.

    The catalog is workspace-level while the key may be narrower, so the check
    walks the chat-capable models the catalog offers and requires at least one
    to answer. A model the key is not scoped for answers 403 and is skipped
    with its reason printed.
    """
    import openai
    from openai import AsyncOpenAI

    origins = resolve_origins(environ={})
    resolved = client_config_for(
        API_KEY_PROVIDER, configured_api_key=LIVE_KEY, environ={}
    )
    assert resolved.base_url == "https://api.orcarouter.ai/v1"

    catalog = ModelCatalog(origins=origins)
    catalog.refresh(api_key=LIVE_KEY)
    chat_models = filter_models(catalog.records, "chat")
    assert chat_models

    async def probe_all():
        # One event loop for the whole probe: the async client owns a connection
        # pool bound to the loop it was created on, so a loop per model leaks
        # transports and fails with "Event loop is closed" instead of reporting
        # the real HTTP status.
        served = []
        skipped = []
        async with AsyncOpenAI(
            api_key=resolved.api_key, base_url=resolved.base_url
        ) as client:
            for record in chat_models:
                try:
                    response = await client.chat.completions.create(
                        model=record.id,
                        messages=[
                            {
                                "role": "user",
                                "content": "Reply with the single word: ok",
                            }
                        ],
                        max_tokens=8,
                        temperature=0.0,
                    )
                except (openai.PermissionDeniedError, openai.NotFoundError) as exc:
                    skipped.append((record.id, type(exc).__name__))
                    continue
                assert response.choices and response.choices[0].message
                served.append((record.id, response.model))
        return served, skipped

    served, skipped = asyncio.run(probe_all())

    print(f"live inference ok: {served}; skipped (key scope): {skipped}")
    assert served, f"no catalog model answered through the provider: {skipped}"


@requires_live_key
def test_live_capability_query_returns_only_compatible_models():
    catalog = ModelCatalog(origins=resolve_origins(environ={}))
    records = catalog.refresh(api_key=LIVE_KEY, capability="chat")
    assert records
    assert all(
        filter_models([r], "chat") for r in records
    ), "a model returned for ?capability=chat was not chat-capable"
