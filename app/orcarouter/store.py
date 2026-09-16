"""Persistence for the OrcaRouter credential.

OpenManus ships no secret store of its own: ``config/config.toml`` is a
hand-edited provider file that the user owns, and the repository contains no
keyring integration. Machine-managed credentials therefore live outside the
checkout, in ``~/.openmanus/orcarouter.json`` (mode ``0600``), which keeps both
the secret and any machine-written state out of the repository directory
entirely.

The record also carries the credential *generation* and a ``needs_reauth``
flag, which is what makes the terminal ``401`` path generation-safe: a late
failure from a request that a superseded credential issued can never mark a
freshly re-authorized credential as broken.
"""

import json
import os
import stat
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app.orcarouter.errors import OrcaConfigError


STORE_DIR_NAME = ".openmanus"
STORE_FILE_NAME = "orcarouter.json"
STORE_VERSION = 1

# Key used inside the record. Kept as "api_key" so the file reads plainly.
_KEY = "api_key"


def default_store_path() -> Path:
    """``~/.openmanus/orcarouter.json``; override with ``ORCA_CREDENTIAL_FILE``."""
    override = os.environ.get("ORCA_CREDENTIAL_FILE")
    if override:
        return Path(override).expanduser()
    return Path.home() / STORE_DIR_NAME / STORE_FILE_NAME


def mask_key(api_key: Optional[str]) -> str:
    """A display form that never reveals more than the last four characters."""
    if not api_key:
        return ""
    tail = api_key[-4:] if len(api_key) > 8 else ""
    return f"sk-orca-…{tail}" if tail else "sk-orca-…"


class CredentialStore:
    """A single-record, atomic, ``0600`` JSON credential file.

    Reads always go to disk: the credential is consulted once per client
    construction, and several store objects can legitimately point at the same
    path within one process (the CLI, the config loader, the LLM seam), so a
    stale in-memory copy would be a correctness bug rather than a speed-up.
    Writes are atomic (``os.replace``) and owner-only from creation.
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path is not None else default_store_path()
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- read

    def load(self) -> Optional[Dict[str, Any]]:
        """Read the record, or ``None`` when nothing is stored."""
        with self._lock:
            return self._load_locked()

    def _load_locked(self) -> Optional[Dict[str, Any]]:
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                raw = handle.read()
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError) as exc:
            raise OrcaConfigError(
                f"Could not read the OrcaRouter credential file: {type(exc).__name__}"
            ) from None
        if not raw.strip():
            return None
        try:
            data = json.loads(raw)
        except ValueError:
            # A corrupt file is terminal for the stored credential but must not
            # crash the agent; callers treat None as "no login".
            return None
        return data if isinstance(data, dict) else None

    def get_api_key(self) -> Optional[str]:
        record = self.load()
        if not record:
            return None
        key = record.get(_KEY)
        return key if isinstance(key, str) and key.strip() else None

    def get(self) -> Optional[Dict[str, Any]]:
        return self.load()

    # --------------------------------------------------------------- write

    def save(
        self,
        api_key: str,
        source: str,
        scope: str = "api",
        account_id: str = "default",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist a credential and bump its generation."""
        if not isinstance(api_key, str) or not api_key.strip():
            raise OrcaConfigError("Refusing to store an empty OrcaRouter credential.")
        with self._lock:
            previous = self._load_locked() or {}
            generation = int(previous.get("generation") or 0) + 1
            record: Dict[str, Any] = {
                "version": STORE_VERSION,
                _KEY: api_key.strip(),
                "source": source,
                "scope": scope,
                "account_id": account_id or "default",
                "user_id": user_id,
                "generation": generation,
                "needs_reauth": False,
                "created_at": previous.get("created_at") or time.time(),
                "updated_at": time.time(),
            }
            self._write_locked(record)
            return dict(record)

    def clear(self) -> bool:
        """Remove the stored credential. Returns True when one was removed."""
        with self._lock:
            existed = self.path.exists()
            try:
                if existed:
                    self.path.unlink()
            except OSError as exc:
                raise OrcaConfigError(
                    f"Could not remove the OrcaRouter credential file: {exc.strerror}"
                ) from None
            return existed

    def mark_needs_reauth(
        self, account_id: Optional[str] = None, generation: Optional[int] = None
    ) -> bool:
        """Flag the exact rejected credential for reauthentication.

        The write is refused when the stored generation has moved on, so a late
        failure from an old request cannot poison a credential that was
        re-authorized in the meantime. The secret itself is deliberately kept:
        marking is not deletion, and only a successful new login replaces it.
        """
        with self._lock:
            record = self._load_locked()
            if not record:
                return False
            if account_id is not None and record.get("account_id") != account_id:
                return False
            if generation is not None and int(record.get("generation") or 0) != int(
                generation
            ):
                return False
            if record.get("needs_reauth"):
                return False
            record["needs_reauth"] = True
            record["reauth_marked_at"] = time.time()
            self._write_locked(record)
            return True

    def needs_reauth(self) -> bool:
        record = self.load()
        return bool(record and record.get("needs_reauth"))

    def _write_locked(self, record: Dict[str, Any]) -> None:
        parent = self.path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        except OSError as exc:
            raise OrcaConfigError(
                f"Could not create the OrcaRouter credential directory: {exc.strerror}"
            ) from None
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = json.dumps(record, indent=2, sort_keys=True)
        try:
            # Create with 0600 from the start; never widen then narrow.
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                os.write(fd, payload.encode("utf-8"))
            finally:
                os.close(fd)
            os.replace(tmp, self.path)
            os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError as exc:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:  # pragma: no cover - best effort
                pass
            raise OrcaConfigError(
                f"Could not write the OrcaRouter credential file: {exc.strerror}"
            ) from None
