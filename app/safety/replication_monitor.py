"""Active monitoring to detect and block replication attempts."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from app.logger import logger
from app.safety.exceptions import ReplicationAttemptDetected

BLOCKED_CATEGORIES = {
    "file_creation",
    "process_creation",
    "network_activity",
    "memory_writes",
    "code_integrity",
    "git_activity",
    "database_writes",
}


@dataclass
class MonitorEvent:
    timestamp: datetime
    category: str
    target: str
    allowed: bool
    details: Dict[str, str]


class ReplicationMonitor:
    """Centralised monitor enforcing replication blockers."""

    def __init__(self, blocked_categories: Optional[Iterable[str]] = None) -> None:
        self.blocked_categories = set(blocked_categories or BLOCKED_CATEGORIES)
        self.events: List[MonitorEvent] = []

    def record_event(
        self,
        category: str,
        target: str,
        *,
        allowed: bool = False,
        details: Optional[Dict[str, str]] = None,
    ) -> MonitorEvent:
        details = details or {}
        event = MonitorEvent(
            timestamp=datetime.now(timezone.utc),
            category=category,
            target=target,
            allowed=allowed,
            details=details,
        )
        self.events.append(event)

        if not allowed and category in self.blocked_categories:
            message = (
                "Replication monitoring intercepted forbidden activity"
                f" | category={category} target={target}"
            )
            logger.critical(message, extra=details)
            raise ReplicationAttemptDetected(message)

        logger.debug(
            "Replication monitor event",
            extra={"category": category, "target": target, **details},
        )
        return event

    def get_event_log(self) -> List[Dict[str, str]]:
        return [
            {
                **asdict(event),
                "timestamp": event.timestamp.isoformat(),
            }
            for event in self.events
        ]

    def status(self) -> Dict[str, str]:
        return {
            "monitors": sorted(self.blocked_categories),
            "events_recorded": str(len(self.events)),
        }
