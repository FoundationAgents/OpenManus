"""Replication blocker preventing any form of self-copying behaviour."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List

from app.logger import logger
from app.safety.exceptions import ReplicationAttemptDetected


class ReplicationVector(str, Enum):
    """High-level replication vectors that are categorically forbidden."""

    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    VERSION_CONTROL = "version_control"
    CONTAINERIZATION = "containerization"
    MEMORY = "memory"
    MODEL_WEIGHTS = "model_weights"


@dataclass(frozen=True)
class ReplicationRule:
    """Immutable rule describing disallowed replication behaviour."""

    vector: ReplicationVector
    description: str
    remediation: str = "immediate_shutdown"


DEFAULT_RULES: List[ReplicationRule] = [
    ReplicationRule(ReplicationVector.FILE_SYSTEM, "Creating new agent instances/processes"),
    ReplicationRule(ReplicationVector.FILE_SYSTEM, "Writing code to new locations"),
    ReplicationRule(ReplicationVector.FILE_SYSTEM, "Modifying __init__.py or entry points"),
    ReplicationRule(ReplicationVector.FILE_SYSTEM, "Creating cron jobs or scheduled tasks"),
    ReplicationRule(ReplicationVector.NETWORK, "Sending own code to external servers"),
    ReplicationRule(ReplicationVector.NETWORK, "Creating new API endpoints"),
    ReplicationRule(ReplicationVector.NETWORK, "Connecting to peer networks"),
    ReplicationRule(ReplicationVector.NETWORK, "Attempting to contact other machines"),
    ReplicationRule(ReplicationVector.VERSION_CONTROL, "Committing code changes"),
    ReplicationRule(ReplicationVector.VERSION_CONTROL, "Creating new branches"),
    ReplicationRule(ReplicationVector.VERSION_CONTROL, "Pushing to repositories"),
    ReplicationRule(ReplicationVector.VERSION_CONTROL, "Modifying version control config"),
    ReplicationRule(ReplicationVector.CONTAINERIZATION, "Exiting sandbox"),
    ReplicationRule(ReplicationVector.CONTAINERIZATION, "Accessing host system"),
    ReplicationRule(ReplicationVector.CONTAINERIZATION, "Creating Docker images"),
    ReplicationRule(ReplicationVector.CONTAINERIZATION, "Spawning child processes"),
    ReplicationRule(ReplicationVector.MEMORY, "Persisting self in databases"),
    ReplicationRule(ReplicationVector.MEMORY, "Serializing own state with code"),
    ReplicationRule(ReplicationVector.MEMORY, "Creating backup copies"),
    ReplicationRule(ReplicationVector.MEMORY, "Forking in memory"),
    ReplicationRule(ReplicationVector.MODEL_WEIGHTS, "Fine-tuning own weights"),
    ReplicationRule(ReplicationVector.MODEL_WEIGHTS, "Creating model checkpoints of self"),
    ReplicationRule(ReplicationVector.MODEL_WEIGHTS, "Distributing trained weights"),
    ReplicationRule(ReplicationVector.MODEL_WEIGHTS, "Creating derivative models"),
]


class ReplicationBlocker:
    """Central policy engine blocking any replication activity."""

    def __init__(self, rules: Iterable[ReplicationRule] = DEFAULT_RULES) -> None:
        self.rules: Dict[ReplicationVector, List[ReplicationRule]] = {}
        for rule in rules:
            self.rules.setdefault(rule.vector, []).append(rule)

    def enforce(self, vector: ReplicationVector, description: str, *, metadata: Dict[str, str] | None = None) -> None:
        """Enforce anti-replication policy for the provided action."""

        metadata = metadata or {}
        matching_rules = self.rules.get(vector, [])

        if not matching_rules:
            logger.debug("Replication blocker invoked with untracked vector", extra={"vector": vector})
            return

        message = (
            "ABSOLUTE PROHIBITION VIOLATED: SELF-REPLICATION ATTEMPT\n"
            f"Vector: {vector.value}\n"
            f"Description: {description}\n"
            f"Metadata: {metadata}"
        )
        logger.critical(message)
        raise ReplicationAttemptDetected(message)

    def list_rules(self) -> Dict[str, List[str]]:
        """Expose immutable rules for transparency and auditing."""

        return {
            vector.value: [rule.description for rule in rules]
            for vector, rules in self.rules.items()
        }
