import uuid
from typing import Dict, Optional

from app.tool.base import BaseTool, ToolResult
from app.logger import logger
from app.event_bus.redis_bus import RedisEventBus # Assume que teremos uma instância global ou passada
from app.event_bus.events import HumanInputRequiredEvent
# from app.config import config # Para obter workflow_id/subtask_id se estiverem no contexto do agente

# TODO: Decidir como o event_bus será instanciado e acessado pela ferramenta.
# Opção 1: Instância global (mais simples para agora, mas não ideal para testabilidade)
# Opção 2: Passar como parte do contexto da ferramenta ou no construtor.
# Por agora, vamos assumir que podemos instanciar um novo cliente,
# embora o ideal seria uma única instância gerenciada.
# Para simplificar o PR, vou instanciar um novo redis_bus aqui, mas isso deve ser refatorado.
# Em uma aplicação real, o event_bus seria injetado ou um singleton.


class AskHuman(BaseTool):
    name: str = "ask_human" # Nome da ferramenta consistente com outros lugares
    description: str = (
        "Sends a question to the human user and waits for their input asynchronously. "
        "Use this when clarification, guidance, or critical decisions are needed from the human. "
        "The agent will be notified when the human provides a response."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "inquire": {
                "type": "string",
                "description": "The clear and specific question or prompt for the human user.",
            },
            "workflow_id": { # Novo parâmetro
                "type": "string",
                "description": "Optional. The ID of the current workflow this question pertains to."
            },
            "subtask_id": { # Novo parâmetro
                "type": "string",
                "description": "Optional. The ID of the specific subtask that requires human input."
            },
            "relevant_checkpoint_id": { # Novo parâmetro
                "type": "string",
                "description": "Optional. The ID of the checkpoint taken before requesting this input, to allow rollback/resume."
            }
        },
        "required": ["inquire"],
    }

    def __init__(self, **data):
        super().__init__(**data)
        # A inicialização do event_bus aqui pode ser problemática se a config não estiver carregada
        # ou se o loop de eventos não estiver rodando. Idealmente, é injetado.
        # Para este exemplo, vamos criá-lo, mas com um aviso.
        try:
            from app.config import config # Late import to ensure config is loaded
            if hasattr(config, 'redis'):
                self.event_bus = RedisEventBus() # CUIDADO: Isso pode criar múltiplas conexões se não for singleton
            else:
                logger.error("AskHuman: Configuração do Redis não encontrada. A ferramenta AskHuman não funcionará.")
                self.event_bus = None
        except ImportError:
            logger.error("AskHuman: Falha ao importar config. A ferramenta AskHuman não funcionará.")
            self.event_bus = None
        except Exception as e:
            logger.error(f"AskHuman: Erro ao inicializar RedisEventBus: {e}. A ferramenta AskHuman não funcionará.")
            self.event_bus = None


    async def execute(self,
                      inquire: str,
                      workflow_id: Optional[str] = None,
                      subtask_id: Optional[str] = None,
                      relevant_checkpoint_id: Optional[str] = None,
                      **kwargs) -> Dict[str, str]: # Retorna um Dict para ser consistente com ToolResult implicitamente

        if not self.event_bus:
            logger.error("AskHuman: Event bus not available. Cannot request human input.")
            # Retornar um ToolResult de erro seria melhor, mas o tipo de retorno atual é str.
            # Mudando para Dict para permitir um retorno de erro estruturado.
            return {
                "status": "error",
                "message": "Event bus not available. Human input cannot be requested.",
                "request_id": None
            }

        # Conectar o event_bus se não estiver conectado (a conexão é idempotente)
        if not self.event_bus.redis_client or not self.event_bus.redis_client.is_connected:
            try:
                await self.event_bus.connect()
            except Exception as e_conn:
                 logger.error(f"AskHuman: Failed to connect to event bus: {e_conn}")
                 return {
                    "status": "error",
                    "message": f"Failed to connect to event bus: {e_conn}",
                    "request_id": None
                }


        request_id = str(uuid.uuid4())

        # Tentar obter IDs do contexto do agente se não fornecidos explicitamente.
        # Esta parte é um placeholder, pois o contexto do agente não é diretamente acessível aqui.
        # O LLM deve ser instruído a fornecer esses IDs.
        # workflow_id = workflow_id or getattr(config, 'CURRENT_WORKFLOW_ID', None)
        # subtask_id = subtask_id or getattr(config, 'CURRENT_SUBTASK_ID', None)

        event = HumanInputRequiredEvent(
            source=f"Agent:{self.name}", # Ou o nome do agente que está chamando
            task_id=workflow_id or "unknown_workflow", # Melhor ter um valor padrão
            subtask_id=subtask_id or "unknown_subtask",
            requesting_component=self.name,
            question_or_prompt=inquire,
            context={"additional_kwargs": kwargs}, # Passar quaisquer outros args recebidos
            relevant_checkpoint_id=relevant_checkpoint_id,
            # Adicionar request_id ao evento para rastreamento se o modelo de evento for atualizado
        )
        # Adicionar request_id ao payload do evento se o modelo suportar, ou logar com ele
        event_payload = event.model_dump(mode='json')
        event_payload["request_id"] = request_id # Adicionar request_id manualmente ao payload

        logger.info(f"AskHuman: Publishing HumanInputRequiredEvent (request_id: {request_id}) for workflow '{workflow_id}', subtask '{subtask_id}'. Question: '{inquire}'")

        await self.event_bus.publish(
            stream_name="human_interaction_events", # Um stream dedicado para interações humanas
            event_data=event_payload
        )

        # Não bloquear. Retornar uma mensagem indicando que a pergunta foi enviada.
        # O agente que chamou esta ferramenta deve então pausar esta linha de trabalho específica.
        # A subtarefa associada deve ser marcada como WAITING_HUMAN.
        response_message = (f"Sua pergunta foi enviada ao usuário (ID da Solicitação: {request_id}). "
                            "O sistema aguardará a resposta de forma assíncrona. "
                            "Você pode prosseguir com outras tarefas independentes, se houver, ou aguardar novas instruções.")

        logger.info(f"AskHuman: Returning status 'input_requested' for request_id: {request_id}")
        return {
            "status": "input_requested",
            "message": response_message,
            "request_id": request_id
        }

# Para testar standalone (requer Redis rodando e config):
# async def main_test_ask_human():
#     tool = AskHuman()
#     # Mock config if not running in full app context
#     from app.config import config as app_config
#     if not hasattr(app_config, 'redis'):
#         class MockRedisCfg: host = "localhost"; port = 6379; db = 0; password = None; event_stream_max_len=1000
#         setattr(app_config, 'redis', MockRedisCfg())
#
#     result = await tool.execute(
#         inquire="What is the next step for Project X?",
#         workflow_id="wf_123",
#         subtask_id="st_abc",
#         relevant_checkpoint_id="cp_001"
#     )
#     print(f"AskHuman tool execution result: {result}")
#     if tool.event_bus:
#         await tool.event_bus.shutdown()

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main_test_ask_human())
