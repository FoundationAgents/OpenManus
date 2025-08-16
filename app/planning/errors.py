class PlanningError(Exception):
    """Base error for the planning pipeline."""

    hint: str | None = None

    def __init__(self, message: str, *, hint: str | None = None):
        super().__init__(message)
        self.hint = hint


class JSONParseError(PlanningError):
    """Failed to json.loads the repaired text."""


class JSONSchemaError(PlanningError):
    """Schema validation failed for Plan/Step (Pydantic)."""


class JSONRepairFailed(PlanningError):
    """Repair considered unsafe or impossible."""
