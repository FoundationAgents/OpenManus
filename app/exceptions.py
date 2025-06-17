class ToolError(Exception):
    """Levantado quando uma ferramenta encontra um erro."""

    def __init__(self, message):
        self.message = message


class OpenManusError(Exception):
    """Exceção base para todos os erros do OpenManus"""


class TokenLimitExceeded(OpenManusError):
    """Exceção levantada quando o limite de token é excedido"""
