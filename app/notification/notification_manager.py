import asyncio
import json # Para o caso de precisar lidar com JSON no futuro, embora não diretamente aqui.
from uuid import UUID

from app.event_bus.redis_bus import RedisEventBus
from app.event_bus.events import HumanInputRequiredEvent, HumanInputProvidedEvent
from app.logger import logger

class NotificationManager:
    def __init__(self, event_bus: RedisEventBus):
        self.event_bus = event_bus

    async def handle_human_input_required(self, event_data: dict, event_id_str: str, stream_name: str, group_name: str, consumer_name: str):
        """
        Handles HumanInputRequiredEvent by presenting the question to the user (console)
        and publishing their response.
        """
        try:
            # O event_data já é um dicionário porque RedisEventBus decodifica o JSON.
            # Se precisarmos do objeto Pydantic, podemos recriá-lo, mas para acessar os campos, o dict é suficiente.
            # event = HumanInputRequiredEvent(**event_data) # Opcional, se precisar de validação/métodos do Pydantic.

            question = event_data.get("question_or_prompt", "Nenhuma pergunta fornecida.")
            original_event_id = event_data.get("event_id") # ID do HumanInputRequiredEvent original
            request_id = event_data.get("request_id") # ID da solicitação específica da ferramenta AskHuman
            task_id = event_data.get("task_id", "N/A")
            subtask_id = event_data.get("subtask_id", "N/A")

            logger.info(f"NotificationManager: Received HumanInputRequiredEvent (ID: {original_event_id}, ReqID: {request_id}) for task '{task_id}', subtask '{subtask_id}'.")

            print("\n============================================")
            print("===         intervento UMANO RICHIESTO        ===")
            print("============================================")
            print(f"Domanda per il Task ID: {task_id} (Sottotask: {subtask_id}, Richiesta ID: {request_id})")
            print(f"\n{question}\n")

            # Obter input do usuário (bloqueante para esta thread/processo do NotificationManager)
            # Para permitir que o usuário leve tempo para responder sem bloquear outras partes do sistema,
            # este NotificationManager idealmente rodaria em seu próprio processo.
            try:
                user_response_text = await asyncio.to_thread(input, "La tua risposta: ")
            except EOFError:
                logger.warning("NotificationManager: EOFError ao ler input, talvez rodando em ambiente não interativo. Usando resposta vazia.")
                user_response_text = ""
            except Exception as e_input:
                logger.error(f"NotificationManager: Erro ao obter input do usuário: {e_input}")
                user_response_text = f"[Erro ao obter input: {e_input}]"

            print("============================================")
            print("===    FINE DELL'INTERVENTO UMANO         ===")
            print("============================================")

            # Publicar HumanInputProvidedEvent
            response_event = HumanInputProvidedEvent(
                source="NotificationManager:Console",
                task_id=task_id,
                subtask_id=subtask_id,
                response_to_event_id=UUID(original_event_id) if original_event_id else None, # UUID do evento original
                user_response=user_response_text.strip(),
                # Adicionar request_id aqui se o modelo HumanInputProvidedEvent for atualizado para incluí-lo
                # ou passá-lo dentro de responder_info.
                responder_info={"method": "console_input", "request_id_correlation": request_id}
            )

            await self.event_bus.publish(
                stream_name="human_responses_events", # Stream dedicado para respostas
                event_data=response_event.model_dump(mode='json')
            )
            logger.info(f"NotificationManager: HumanInputProvidedEvent published for request_id {request_id} (original event {original_event_id}).")

        except Exception as e:
            logger.error(f"NotificationManager: Error in handle_human_input_required: {e}", exc_info=True)


    async def start(self):
        logger.info("NotificationManager starting...")
        if not self.event_bus.redis_client or not self.event_bus.redis_client.is_connected:
            try:
                await self.event_bus.connect()
            except Exception as e_conn:
                logger.error(f"NotificationManager: Failed to connect to event bus on start: {e_conn}. Cannot subscribe.")
                return

        # O NotificationManager escuta os eventos HumanInputRequiredEvent
        await self.event_bus.subscribe(
            stream_name="human_interaction_events", # Mesmo stream que AskHuman publica
            group_name="notification_manager_group",
            consumer_name="console_notifier_1", # Pode haver múltiplos notificadores
            callback=self.handle_human_input_required
        )

        logger.info("NotificationManager subscribed to 'human_interaction_events'.")
        # O loop de consumo é gerenciado pela instância do event_bus,
        # que deve ser iniciada externamente (e.g., no main.py da aplicação ou em um script de serviço).

    async def shutdown(self):
        logger.info("NotificationManager shutting down...")
        # O shutdown do event_bus (desconectar, parar consumers) geralmente é tratado
        # pela aplicação principal que gerencia o ciclo de vida do event_bus.
        # Se este NotificationManager tivesse seus próprios loops de consumo independentes,
        # eles precisariam ser parados aqui. Mas como ele usa o `subscribe` do event_bus,
        # o `event_bus.shutdown()` global cuidará de parar os consumers.
        logger.info("NotificationManager shutdown complete.")


# Exemplo de como o NotificationManager poderia ser iniciado e parado:
# async def run_notification_manager_example():
#     from app.config import config # Ensure config is loaded
#     if not hasattr(config, 'redis'): # Mock config for Redis if not present
#         class MockRedisConfig: host = "localhost"; port = 6379; db = 0; password = None; event_stream_max_len = 1000
#         setattr(config, 'redis', MockRedisConfig())
#
#     event_bus = RedisEventBus()
#     # await event_bus.connect() # connect é chamado dentro de start se necessário
#
#     notifier = NotificationManager(event_bus)
#     await notifier.start() # Subscribes to events
#
#     # A instância do event_bus precisa ter seus consumidores iniciados em algum lugar
#     # Esta chamada iniciaria os loops de consumo para TODAS as subscrições, incluindo a do notifier.
#     event_bus.start_consuming()
#
#     logger.info("NotificationManager example running. Waiting for HumanInputRequiredEvents...")
#     logger.info("To test, publish an event to 'human_interaction_events' stream in Redis, e.g., using AskHuman tool or redis-cli.")
#     # Exemplo de publicação manual para teste (simulando AskHuman)
#     # test_event_payload = HumanInputRequiredEvent(
#     #     source="TestAskHuman",
#     #     task_id="test_workflow_01",
#     #     subtask_id="test_subtask_01",
#     #     requesting_component="TestAskHuman",
#     #     question_or_prompt="Este é um teste do NotificationManager. Qual é a sua cor favorita?",
#     #     context={"some_info": "para ajudar o usuário"},
#     #     relevant_checkpoint_id="cp_test_001"
#     # ).model_dump(mode='json')
#     # test_event_payload["request_id"] = str(uuid.uuid4())
#     # await event_bus.publish("human_interaction_events", test_event_payload)
#
#     try:
#         while True: # Mantenha o processo principal rodando para que os consumers do event_bus funcionem
#             await asyncio.sleep(10)
#             logger.debug("NotificationManager example keep-alive tick.")
#     except KeyboardInterrupt:
#         logger.info("NotificationManager example interrupted by user.")
#     finally:
#         logger.info("Shutting down NotificationManager example...")
#         await notifier.shutdown()
#         await event_bus.shutdown()
#
# if __name__ == "__main__":
#     import logging
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
#     # asyncio.run(run_notification_manager_example())
#     logger.info("Standalone NotificationManager example finished (or commented out).")
