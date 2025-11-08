"""Simplified hardware security module integration used for signing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.safety.crypto_verification import CodeSigner


@dataclass
class HardwareSecurityModule:
    endpoint: str
    device_id: str
    _signer: Optional[CodeSigner] = None

    def __post_init__(self) -> None:
        if not self.endpoint:
            raise ValueError("HSM endpoint cannot be empty")
        if not self.device_id:
            raise ValueError("HSM device id cannot be empty")

    def configure_signer(self, private_key: str) -> None:
        self._signer = CodeSigner(private_key)

    def sign(self, code_hash: str) -> str:
        if self._signer is None:
            raise RuntimeError("HSM signer has not been configured")
        return self._signer.sign(code_hash)
