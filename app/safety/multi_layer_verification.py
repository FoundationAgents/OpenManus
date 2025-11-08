"""Multi-layer verification orchestrating all safety defences."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Sequence, Tuple

from app.logger import logger
from app.safety.exceptions import SafetyViolationError


@dataclass
class VerificationLayer:
    name: str
    check: Callable[[], None]
    description: str


@dataclass
class MultiLayerVerificationResult:
    all_layers_passed: bool
    violations: Sequence[Tuple[str, str]] = field(default_factory=list)


class MultiLayerVerificationError(SafetyViolationError):
    """Raised when one or more safety layers detect a violation."""

    def __init__(self, violations: Sequence[Tuple[str, str]]) -> None:
        message = "; ".join(f"{name}: {reason}" for name, reason in violations)
        super().__init__(message)
        self.violations = tuple(violations)


class MultiLayerVerification:
    """Aggregates independent safety checks to guarantee defence in depth."""

    def __init__(self, layers: Iterable[VerificationLayer] | None = None) -> None:
        self.layers: List[VerificationLayer] = list(layers or [])

    def register_layer(self, layer: VerificationLayer) -> None:
        logger.debug("Registering verification layer", extra={"layer": layer.name})
        self.layers.append(layer)

    def verify_all_layers(self, *, stop_on_violation: bool = False) -> MultiLayerVerificationResult:
        violations: List[Tuple[str, str]] = []

        for layer in self.layers:
            try:
                layer.check()
                logger.debug("Layer verification passed", extra={"layer": layer.name})
            except SafetyViolationError as exc:
                logger.critical(
                    "Safety layer detected violation",
                    extra={"layer": layer.name, "reason": str(exc)},
                )
                violations.append((layer.name, str(exc)))
                if stop_on_violation:
                    break
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception(
                    "Unexpected error during safety layer verification",
                    extra={"layer": layer.name},
                )
                violations.append((layer.name, f"unexpected error: {exc}"))
                if stop_on_violation:
                    break

        if violations:
            raise MultiLayerVerificationError(violations)

        return MultiLayerVerificationResult(all_layers_passed=True)
