"""Cryptographic integrity verification utilities."""

from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from app.safety.exceptions import CodeIntegrityViolation

HARDCODED_PUBLIC_KEY = "IXLINX_AGENT_SAFETY_PUBLIC_KEY"


@dataclass(frozen=True)
class CodeSignature:
    """Represents a cryptographic signature over code content."""

    code_hash: str
    signature: str
    algorithm: str = "SHA256"
    path: Optional[str] = None


class CodeSigner:
    """Creates deterministic signatures using an HMAC-based scheme."""

    def __init__(self, private_key: str) -> None:
        if not private_key:
            raise ValueError("Private key must not be empty")
        self.private_key = private_key.encode("utf-8")

    def sign(self, code_hash: str) -> str:
        digest = hmac.new(self.private_key, code_hash.encode("utf-8"), hashlib.sha256).digest()
        return base64.b64encode(digest).decode("ascii")


class SignatureVerifier:
    """Verifies signatures against expected code hashes."""

    def __init__(self, public_key: str = HARDCODED_PUBLIC_KEY) -> None:
        if not public_key:
            raise ValueError("Public key must not be empty")
        self.public_key = public_key.encode("utf-8")

    def verify(self, code_hash: str, signature: str) -> bool:
        expected = hmac.new(self.public_key, code_hash.encode("utf-8"), hashlib.sha256).digest()
        provided = base64.b64decode(signature.encode("ascii"))
        return hmac.compare_digest(expected, provided)


class SignatureRegistry:
    """Immutable registry of expected signatures for code files."""

    def __init__(self) -> None:
        self._store: Dict[str, CodeSignature] = {}

    def register(self, path: Path, signature: CodeSignature) -> None:
        key = str(path.resolve())
        if key in self._store:
            return
        signature_with_path = CodeSignature(
            code_hash=signature.code_hash,
            signature=signature.signature,
            algorithm=signature.algorithm,
            path=key,
        )
        self._store[key] = signature_with_path

    def get(self, path: Path) -> Optional[CodeSignature]:
        return self._store.get(str(path.resolve()))


def compute_hash_from_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_file_read(path: Path, registry: SignatureRegistry, verifier: SignatureVerifier) -> str:
    """Read file contents ensuring the signature matches expectations."""

    path = path.resolve()
    signature = registry.get(path)
    if signature is None:
        raise CodeIntegrityViolation(f"No signature registered for {path}")

    data = path.read_bytes()
    computed_hash = compute_hash_from_bytes(data)
    if computed_hash != signature.code_hash:
        raise CodeIntegrityViolation("File hash mismatch detected")

    if not verifier.verify(signature.code_hash, signature.signature):
        raise CodeIntegrityViolation("Signature verification failed")

    return data.decode("utf-8")
