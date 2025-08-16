class PlanningError(Exception):
    """Erro base do pipeline de planejamento."""

    hint: str | None = None

    def __init__(self, message: str, *, hint: str | None = None):
        super().__init__(message)
        self.hint = hint


class JSONParseError(PlanningError):
    """Falha ao converter o texto (após reparos) para JSON."""


class JSONSchemaError(PlanningError):
    """Falha de validação Pydantic do schema Plan/Step."""


class JSONRepairFailed(PlanningError):
    """Reparo considerado inseguro ou impossível."""
