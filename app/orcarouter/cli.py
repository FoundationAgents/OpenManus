"""``orcarouter`` console entry point.

Both authentication choices are separately discoverable commands:

* ``orcarouter login --api-key sk-orca-...`` (or ``ORCAROUTER_API_KEY``)
* ``orcarouter login``                      (OAuth 2.0 + PKCE, loopback)
* ``orcarouter login --code <code>``        (PKCE with a code the screen showed)

plus ``status``, ``logout``, ``models`` and ``key``. The ``key`` subcommand is
the only place the credential is ever printed, and it prints the masked form
unless ``--reveal`` is passed explicitly.
"""

import argparse
import json
import sys
from typing import Dict, List, Optional, Sequence

from app.orcarouter.catalog import ModelCatalog, capability_options, filter_models
from app.orcarouter.constants import (
    API_KEY_ENVS,
    API_KEY_PROVIDER,
    PKCE_PROVIDER,
    OrcaOrigins,
    api_key_from_env,
    api_key_prefix_ok,
    resolve_origins,
)
from app.orcarouter.credentials import ApiKeyAdapter, PkceAdapter
from app.orcarouter.errors import OrcaError
from app.orcarouter.provider import PROVIDERS
from app.orcarouter.store import CredentialStore, mask_key


def _read_api_key(args, environ) -> Optional[str]:
    if args.api_key:
        return args.api_key.strip()
    import os

    env = os.environ if environ is None else environ
    for name in API_KEY_ENVS:
        value = env.get(name)
        if value and value.strip():
            return value.strip()
    return None


def cmd_login(args, store: CredentialStore, origins: OrcaOrigins) -> int:
    if args.provider == PKCE_PROVIDER or (
        args.provider is None and not _read_api_key(args, None)
    ):
        # PKCE path. The issued credential is a durable API key, reused until
        # OrcaRouter revokes it; there is no refresh grant and none is faked.
        adapter = PkceAdapter(
            store=store,
            origins=origins,
            open_browser=not args.no_browser,
            on_url=lambda url: print("If your browser did not open, visit:\n  " + url),
            reuse_stored=not args.force,
        )
        if args.code:
            credential = adapter.acquire_with_code(args.code)
        else:
            credential = adapter.acquire(
                use_loopback=not args.oob,
                code_reader=_prompt_code,
            )
    else:
        adapter = ApiKeyAdapter(
            store=store,
            api_key=args.api_key,
            prompt=_prompt_api_key,
            interactive=True,
        )
        credential = adapter.acquire()

    print(
        f"Stored OrcaRouter credential ({credential.source}) "
        f"{credential.masked} -> {origins.api_base}"
    )
    if credential.source == "pkce":
        print(
            "This key is durable and reused until revoked. Revoke it at "
            f"{PROVIDERS[PKCE_PROVIDER].console_url}."
        )
    return 0


def _prompt_api_key(prompt: str) -> str:
    return input(prompt)


def _prompt_code() -> str:
    return input("Authorization code shown by OrcaRouter: ")


def cmd_status(args, store: CredentialStore, origins: OrcaOrigins) -> int:
    record = store.load()
    payload: Dict[str, object] = {
        "auth_base": origins.auth_base,
        "api_base": origins.api_base,
        "stored": bool(record),
    }
    if record:
        payload.update(
            {
                "source": record.get("source"),
                "masked_key": mask_key(record.get("api_key")),
                "scope": record.get("scope"),
                "account_id": record.get("account_id"),
                "generation": record.get("generation"),
                "needs_reauth": bool(record.get("needs_reauth")),
            }
        )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")
        if record and record.get("needs_reauth"):
            print(
                "This credential was rejected by OrcaRouter (401). Run "
                "`orcarouter login` to authorize again."
            )
    return 0


def cmd_logout(args, store: CredentialStore, origins: OrcaOrigins) -> int:
    removed = store.clear()
    print("Removed the stored OrcaRouter credential." if removed else "Nothing stored.")
    return 0


def cmd_key(args, store: CredentialStore, origins: OrcaOrigins) -> int:
    credential = store.get_api_key()
    if not credential:
        print("No OrcaRouter credential is stored.", file=sys.stderr)
        return 1
    print(credential if args.reveal else mask_key(credential))
    return 0


def _effective_api_key(store: CredentialStore) -> Optional[str]:
    """The credential the runtime would use: stored first, then environment."""
    return store.get_api_key() or api_key_from_env()


def cmd_models(args, store: CredentialStore, origins: OrcaOrigins) -> int:
    catalog = ModelCatalog(origins=origins)
    catalog.refresh(api_key=_effective_api_key(store))
    capabilities = args.capability or ["chat"]
    catalog_status = catalog.status()
    print(
        f"catalog source: {catalog_status['source']} "
        f"({catalog_status['model_count']} models from {origins.models_url})"
    )
    if catalog_status["degraded"]:
        print(f"degraded: {catalog_status['error']}")
    exit_code = 0
    for capability in capabilities:
        result = capability_options(catalog.records, capability, args.selected)
        print(f"[{capability}] {len(result['ids'])} option(s)")
        if result["invalidated"]:
            print(
                f"  selected model {args.selected!r} is not compatible with "
                f"{capability!r}; re-select from the list below"
            )
            exit_code = 2
        for model in result["options"]:
            print(f"  {model['id']}  ctx={model['context_length']}")
    return exit_code


def cmd_doctor(args, store: CredentialStore, origins: OrcaOrigins) -> int:
    """Show what the two authentication entries resolve to, without secrets."""
    print(f"auth origin: {origins.auth_base}")
    print(f"inference origin: {origins.api_base}")
    print(f"authorize path: {origins.authorize_url}")
    print(f"exchange path: {origins.exchange_url}")
    print(f"catalog path: {origins.models_url}")
    record = store.load()
    print(f"credential file: {store.path}")
    api_key = _effective_api_key(store)
    if record:
        print(f"credential: {record.get('source')} {mask_key(record.get('api_key'))}")
        if record.get("needs_reauth"):
            print("credential state: needs re-authentication (401 from the relay)")
    elif api_key:
        print(f"credential: environment {mask_key(api_key)}")
    else:
        print("credential: none stored")
    catalog = ModelCatalog(origins=origins)
    catalog.refresh(api_key=api_key)
    status = catalog.status()
    print(f"catalog: {status['source']} ({status['model_count']} models)")
    chat = filter_models(catalog.records, "chat")
    print(f"chat-capable models: {len(chat)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orcarouter",
        description="Manage the OrcaRouter credential used by OpenManus.",
    )
    subs = parser.add_subparsers(dest="command")

    login = subs.add_parser("login", help="authorize with an API key or an account")
    login.add_argument(
        "--provider",
        choices=[API_KEY_PROVIDER, PKCE_PROVIDER],
        default=None,
        help=(
            "orcarouter: paste/configure an existing API key (default when a "
            "key is present). orcarouter-oauth: browser login with PKCE."
        ),
    )
    login.add_argument("--api-key", default=None, help="an sk-orca-... API key")
    login.add_argument(
        "--code", default=None, help="authorization code shown on the consent screen"
    )
    login.add_argument(
        "--oob",
        action="store_true",
        help="do not listen on loopback; paste the code by hand",
    )
    login.add_argument(
        "--no-browser", action="store_true", help="never try to open a browser"
    )
    login.add_argument(
        "--force",
        action="store_true",
        help="mint a fresh credential even when one is already stored",
    )
    login.set_defaults(func=cmd_login)

    status = subs.add_parser("status", help="show the stored credential's state")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    logout = subs.add_parser("logout", help="remove the stored credential")
    logout.set_defaults(func=cmd_logout)

    key = subs.add_parser("key", help="print the stored key (masked by default)")
    key.add_argument("--reveal", action="store_true")
    key.set_defaults(func=cmd_key)

    models = subs.add_parser("models", help="list models the catalog offers")
    models.add_argument(
        "--capability",
        action="append",
        help="chat, chat_multimodal, embedding, image, video, rerank",
    )
    models.add_argument("--selected", default=None)
    models.set_defaults(func=cmd_models)

    doctor = subs.add_parser("doctor", help="print resolved origins and catalog state")
    doctor.set_defaults(func=cmd_doctor)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1

    store = CredentialStore()
    origins = resolve_origins()
    try:
        return args.func(args, store, origins)
    except OrcaError as exc:
        # Every OrcaError message is redacted at construction time.
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("cancelled", file=sys.stderr)
        return 130


def validate_api_key_shape(value: str) -> bool:
    """Exposed for tests: the lightweight shape check used by ``login``."""
    return api_key_prefix_ok(value)


__all__: List[str] = [
    "build_parser",
    "cmd_doctor",
    "cmd_key",
    "cmd_login",
    "cmd_logout",
    "cmd_models",
    "cmd_status",
    "main",
    "validate_api_key_shape",
]
