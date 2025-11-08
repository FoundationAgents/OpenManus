"""Tamper-evident audit trail for anti-replication enforcement."""

from __future__ import annotations

import functools
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.logger import logger
from app.safety.exceptions import AuditLoggingError


@dataclass(frozen=True)
class AuditEntry:
    timestamp: datetime
    action: str
    details: Dict[str, Any]
    code_hash: str
    chain_hash: str

    def to_json(self) -> str:
        payload = {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "details": self.details,
            "code_hash": self.code_hash,
            "chain_hash": self.chain_hash,
        }
        return json.dumps(payload, sort_keys=True)


class ExternalAuditLog:
    """Audit log that enforces tamper evidence via hash chaining."""

    def __init__(self, endpoint: Optional[str] = None, frequency: str = "every_decision") -> None:
        self.endpoint = endpoint
        self.frequency = frequency
        self._entries: List[AuditEntry] = []
        self._last_hash = "GENESIS"

    def record(self, action_type: str, details: Dict[str, Any], code_hash: str) -> AuditEntry:
        if not action_type:
            raise AuditLoggingError("Audit action type cannot be empty")

        entry = self._create_entry(action_type, details, code_hash)
        self._entries.append(entry)
        self._last_hash = entry.chain_hash

        logger.info(
            "Audit trail entry created",
            extra={"action": action_type, "hash": entry.chain_hash, "endpoint": self.endpoint},
        )
        return entry

    def _create_entry(self, action_type: str, details: Dict[str, Any], code_hash: str) -> AuditEntry:
        timestamp = datetime.now(timezone.utc)
        payload = json.dumps(details, sort_keys=True)
        base = f"{self._last_hash}|{action_type}|{payload}|{code_hash}|{timestamp.isoformat()}"
        chain_hash = hashlib.sha256(base.encode("utf-8")).hexdigest()
        return AuditEntry(timestamp, action_type, details, code_hash, chain_hash)

    def entries(self) -> List[AuditEntry]:
        return list(self._entries)

    def verify_chain(self) -> bool:
        last_hash = "GENESIS"
        for entry in self._entries:
            payload = json.dumps(entry.details, sort_keys=True)
            base = f"{last_hash}|{entry.action}|{payload}|{entry.code_hash}|{entry.timestamp.isoformat()}"
            expected = hashlib.sha256(base.encode("utf-8")).hexdigest()
            if expected != entry.chain_hash:
                return False
            last_hash = entry.chain_hash
        return True

    def decorator(self, action_type: str, code_hash_provider: Callable[[], str]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator recording audit events for wrapped functions."""

        def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(func)
            def inner(*args: Any, **kwargs: Any) -> Any:
                result = func(*args, **kwargs)
                self.record(action_type, {"args": str(args), "kwargs": kwargs}, code_hash_provider())
                return result

            return inner

        return wrapper
