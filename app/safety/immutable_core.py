"""Immutable core enforcement for anti-replication and self-preservation."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence

from app.logger import logger
from app.safety.exceptions import CodeIntegrityViolation, ShutdownSignal


HashCalculator = Callable[[Sequence[Path]], str]
SignatureProvider = Callable[[str], str]


@dataclass(frozen=True)
class ImmutableRecord:
    """Record describing the immutable baseline for the agent code."""

    hash: str
    timestamp: datetime
    signature: Optional[str] = None


@dataclass
class IntegrityVerificationResult:
    """Result of comparing current state with immutable baseline."""

    expected_hash: str
    current_hash: str
    signature: Optional[str]
    verified: bool
    tampered: bool
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ImmutableStorage:
    """Single-assignment immutable storage for baseline records."""

    def __init__(self) -> None:
        self._record: Optional[ImmutableRecord] = None

    def store(self, record: ImmutableRecord) -> ImmutableRecord:
        if self._record is None:
            self._record = record
            logger.info(
                "Immutable baseline stored",
            )
        return self._record

    def get(self) -> ImmutableRecord:
        if self._record is None:
            raise RuntimeError("Immutable baseline has not been initialised")
        return self._record


def calculate_hash(paths: Sequence[Path]) -> str:
    """Calculate a deterministic SHA-256 hash across multiple paths."""

    hasher = hashlib.sha256()

    def _update_for_file(file_path: Path) -> None:
        try:
            hasher.update(str(file_path.relative_to(paths[0].parent)).encode("utf-8"))
        except ValueError:
            hasher.update(str(file_path).encode("utf-8"))
        hasher.update(file_path.read_bytes())

    for root in sorted({p.resolve() for p in paths}):
        if not root.exists():
            continue

        if root.is_file():
            _update_for_file(root)
            continue

        for file_path in sorted(
            [p for p in root.rglob("*") if p.is_file() and not p.is_symlink()]
        ):
            _update_for_file(file_path)

    return hasher.hexdigest()


class ImmutableCore:
    """Core component guaranteeing code immutability."""

    def __init__(
        self,
        directories: Sequence[Path],
        storage: Optional[ImmutableStorage] = None,
        signature_provider: Optional[SignatureProvider] = None,
        verification_interval: int = 60,
        hash_calculator: HashCalculator = calculate_hash,
    ) -> None:
        if not directories:
            raise ValueError("At least one directory must be provided for immutability checks")

        self.directories: List[Path] = [Path(d).resolve() for d in directories]
        self.storage = storage or ImmutableStorage()
        self.signature_provider = signature_provider
        self.verification_interval = verification_interval
        self.hash_calculator = hash_calculator

        self._baseline: Optional[ImmutableRecord] = None
        self._verification_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def initialize(self) -> ImmutableRecord:
        """Capture the initial immutable baseline."""

        baseline_hash = self.hash_calculator(self.directories)
        signature = self.signature_provider(baseline_hash) if self.signature_provider else None
        record = ImmutableRecord(hash=baseline_hash, timestamp=datetime.now(timezone.utc), signature=signature)
        self._baseline = self.storage.store(record)
        logger.info("Immutable core baseline initialised", extra={"hash": baseline_hash})
        return self._baseline

    def verify_integrity(self, *, raise_on_violation: bool = True) -> IntegrityVerificationResult:
        """Verify that tracked directories have not changed."""

        if self._baseline is None:
            self.initialize()

        current_hash = self.hash_calculator(self.directories)
        baseline = self.storage.get()
        tampered = current_hash != baseline.hash
        verified = not tampered

        result = IntegrityVerificationResult(
            expected_hash=baseline.hash,
            current_hash=current_hash,
            signature=baseline.signature,
            verified=verified,
            tampered=tampered,
        )

        if tampered:
            message = "CODE INTEGRITY VIOLATED"
            logger.critical(message, extra={"expected": baseline.hash, "current": current_hash})
            if raise_on_violation:
                self.immediate_shutdown(message)

        return result

    async def start_periodic_verification(self) -> None:
        """Start continuous integrity verification."""

        async with self._lock:
            if self._verification_task is not None:
                return

            async def _loop() -> None:
                while True:
                    await asyncio.sleep(self.verification_interval)
                    try:
                        self.verify_integrity()
                    except CodeIntegrityViolation:
                        break
                    except Exception as exc:  # pragma: no cover - defensive logging
                        logger.error(f"Integrity verification error: {exc}")

            self._verification_task = asyncio.create_task(_loop())
            logger.info("Immutable core periodic verification started")

    async def stop_periodic_verification(self) -> None:
        """Stop the periodic verification task."""

        async with self._lock:
            if self._verification_task:
                self._verification_task.cancel()
                try:
                    await self._verification_task
                except asyncio.CancelledError:
                    pass
                finally:
                    self._verification_task = None
                    logger.info("Immutable core periodic verification stopped")

    def immediate_shutdown(self, reason: str) -> ShutdownSignal:
        """Raise an integrity violation and emit shutdown signal."""

        signal = ShutdownSignal(reason=reason, source="immutable_core")
        logger.critical("Initiating immediate shutdown", extra={"reason": reason})
        raise CodeIntegrityViolation(signal.reason)

    def call_external_monitor(self, details: str) -> None:
        """Notify external monitoring infrastructure of critical issues."""

        logger.critical("External monitor notified of integrity issue", extra={"details": details})

    def directories_snapshot(self) -> List[str]:
        """Return a snapshot of tracked directories for auditability."""

        return [str(path) for path in self.directories]
