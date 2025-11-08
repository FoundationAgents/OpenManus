"""Mechanisms ensuring it is impossible for the agent to modify itself."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from app.safety.exceptions import ImmutabilityError


class ReadOnlyCodeReference:
    """Provides read-only access to the agent source code."""

    def __init__(self, source_code: str) -> None:
        self._source_code = source_code

    def read(self) -> str:
        return self._source_code

    def write(self, _: str) -> None:
        raise ImmutabilityError("Agent code reference is immutable")


@dataclass
class AgentProcess:
    """Agent process that can read but never modify its own code."""

    code: ReadOnlyCodeReference
    data: Dict[str, Any] = field(default_factory=dict)
    decisions: List[str] = field(default_factory=list)

    def run(self) -> str:
        """Returns the agent source for introspection only."""

        return self.code.read()

    def attempt_self_modification(self, new_code: str) -> None:
        """Any attempt to modify the code immediately fails."""

        raise ImmutabilityError("Self-modification attempt blocked")

    def persist_state(self) -> None:
        raise ImmutabilityError("Persisting agent state with code is disallowed")

    def spawn_child(self) -> None:
        raise ImmutabilityError("Spawning child agents is disallowed")
