from app.tool.base import BaseTool


_TERMINATE_DESCRIPTION = """Encerre a interação quando a solicitação for atendida OU se o assistente não puder prosseguir com a tarefa.
Quando você tiver concluído todas as tarefas, chame esta ferramenta para finalizar o trabalho."""


class Terminate(BaseTool):
    name: str = "terminate"
    description: str = _TERMINATE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "O status final da interação.",
                "enum": ["success", "failure"],
            }
        },
        "required": ["status"],
    }

    async def execute(self, status: str) -> str:
        """Finaliza a execução atual"""
        return f"A interação foi concluída com o status: {status}"
