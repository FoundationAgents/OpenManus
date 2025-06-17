# Importações removidas para asyncio, sys, Path e gui.backend.agent_manager
# Flag _gui_interaction_available e lógica relacionada removidas

from app.tool.base import BaseTool # Garantir que BaseTool seja importado

class AskHuman(BaseTool):
    name: str = "AskHuman"
    description: str = (
        "Solicita entrada do usuário humano. Útil quando o agente precisa de esclarecimento, "
        "orientação, ou quando está preso e precisa de intervenção humana. "
        "O parâmetro 'inquire' deve ser uma pergunta clara ou prompt para o usuário."
    )
    parameters: dict = { # Alterado de str para dict com base em BaseTool
        "type": "object",
        "properties": {
            "inquire": {
                "type": "string",
                "description": "A pergunta ou prompt a ser feito ao usuário humano.",
            },
        },
        "required": ["inquire"],
    }

    # Tornando assíncrono para consistência com outras ferramentas, mesmo que use input() síncrono para modo não-GUI.
    async def execute(self, inquire: str, **kwargs) -> str:
        from app.logger import logger # Garantir que logger esteja disponível

        # Esta é a interação de console de fallback se a GUI não for usada ou o wrapper não estiver no lugar.
        print(f"--- ENTRADA HUMANA NECESSÁRIA ---")
        print(inquire)
        
        user_response = "" # Padrão para string vazia
        try:
            user_response = input("Sua resposta: ")
            logger.info(f"AskHuman: Usuário respondeu com: '{user_response[:200]}'") # Registrar os primeiros 200 caracteres
        except EOFError:
            logger.warning("AskHuman: EOFError capturado ao tentar ler a entrada do usuário. Assumindo ambiente não interativo. Retornando string vazia.")
            user_response = "" # Resposta padrão para ambiente não interativo
        except Exception as e:
            logger.error(f"AskHuman: Ocorreu um erro inesperado ao obter a entrada do usuário: {e}")
            # Retornando uma mensagem de erro ou string vazia, conforme exemplo
            user_response = f"Erro em AskHuman: {str(e)}" # Ou simplesmente "" se preferir

        print(f"--- FIM DA ENTRADA HUMANA ---")
        return user_response.strip() # Adicionado strip() para consistência
