import asyncio
import signal # Para lidar com Ctrl+C graciosamente
from uuid import UUID # Para o tipo de workflow_id

from app.agent.data_analysis import DataAnalysis
from app.agent.manus import Manus
from app.config import config # config global
from app.flow.flow_factory import FlowFactory, FlowType
from app.logger import logger

# Importar os novos componentes da arquitetura EDA
from app.event_bus.redis_bus import RedisEventBus
from app.checkpointing.postgresql_checkpointer import PostgreSQLCheckpointer
from app.orchestration.workflow_orchestrator import WorkflowOrchestrator
from app.notification.notification_manager import NotificationManager
from app.database.base import init_db # Para criar tabelas se não existirem

# Lista de tarefas asyncio para gerenciar e cancelar na saída
running_tasks = []

async def main_eda_flow():
    global running_tasks

    # 1. Inicializar componentes da arquitetura EDA
    logger.info("Inicializando componentes da arquitetura EDA...")
    event_bus = RedisEventBus()
    try:
        await event_bus.connect()
    except Exception as e:
        logger.error(f"Falha ao conectar ao Redis Event Bus: {e}. Encerrando.")
        return

    # Inicializar/Verificar tabelas do banco de dados
    # Em um ambiente de produção, isso seria feito por Alembic migrations.
    # Aqui, é para conveniência de desenvolvimento.
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Falha ao inicializar/verificar tabelas do banco de dados: {e}. "
                     "Verifique a conexão com o PostgreSQL e as configurações. Encerrando.")
        await event_bus.shutdown() # Tentar limpar o event_bus
        return

    checkpointer = PostgreSQLCheckpointer()
    orchestrator = WorkflowOrchestrator(event_bus, checkpointer)
    notifier = NotificationManager(event_bus)

    # 2. Iniciar os componentes que escutam eventos
    # O Orchestrator e Notifier se inscrevem nos seus respectivos eventos em seus métodos start()
    await orchestrator.start()
    await notifier.start()

    # Iniciar os loops de consumo do event_bus (isso precisa rodar em background)
    # RedisEventBus.start_consuming() cria tarefas asyncio para cada consumidor.
    # Essas tarefas serão adicionadas à lista running_tasks.
    # AVISO: A implementação atual de RedisEventBus.start_consuming() não retorna as tarefas
    # para gerenciamento externo. Isso precisará ser ajustado em RedisEventBus.
    # Por agora, vamos assumir que chamá-lo aqui é suficiente para iniciar os consumers.
    # Idealmente, event_bus.start_consuming() retornaria uma lista de tasks.

    # --- Ajuste necessário em RedisEventBus ---
    # RedisEventBus.start_consuming() deve ser async e retornar as tasks criadas.
    # Vamos simular isso por enquanto, pois a refatoração do RedisEventBus está fora do escopo imediato desta etapa.
    # Em uma implementação real:
    # consumer_event_tasks = await event_bus.start_consuming_and_get_tasks()
    # running_tasks.extend(consumer_event_tasks)
    # Por agora, chamamos o método síncrono que cria tasks internamente,
    # e o shutdown do event_bus tentará cancelá-las.
    event_bus.start_consuming() # Esta chamada deve ser não-bloqueante e iniciar os consumers em background.
    logger.info("WorkflowOrchestrator, NotificationManager e Consumidores do EventBus iniciados.")

    # 3. Configurar agentes para o PlanningFlow
    # O PlanningFlow agora também precisa do event_bus
    agents_for_flow = {
        "manus": await Manus.create(event_bus=event_bus), # Manus.create agora precisa do event_bus
        # Adicionar outros agentes se necessário, passando o event_bus
    }
    if config.run_flow_config.use_data_analysis_agent:
        # DataAnalysisAgent também precisaria ser adaptado para aceitar event_bus se for usado
        # e interagir com o sistema de eventos. Por enquanto, pode quebrar se não for atualizado.
        try:
            agents_for_flow["data_analysis"] = DataAnalysis(event_bus=event_bus)
        except TypeError: # Se DataAnalysis não aceitar event_bus
            logger.warning("DataAnalysis agent não pôde ser inicializado com event_bus. Pode não funcionar corretamente na nova arquitetura.")
            # agents_for_flow["data_analysis"] = DataAnalysis() # Tentativa sem event_bus


    # 4. Criar e executar o PlanningFlow (que agora apenas publica um evento)
    try:
        prompt = input("Entre com seu prompt (ou 'quit' para sair): ")
        if not prompt or prompt.lower() == 'quit':
            logger.info("Nenhum prompt fornecido ou 'quit' inserido. Encerrando.")
            return

        planning_flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,
            agents=agents_for_flow, # Passar os agentes criados
            event_bus=event_bus  # Passar o event_bus para o PlanningFlow
        )
        logger.info("Processando sua requisição inicial (criando plano e publicando TaskCreatedEvent)...")

        # flow.execute agora é rápido, apenas publica um evento.
        initial_response = await planning_flow.execute(prompt)
        logger.info(f"Resposta da inicialização do fluxo: {initial_response}")

        # 5. Manter a aplicação rodando para processar eventos em background
        logger.info("A tarefa foi iniciada e está sendo processada em background.")
        logger.info("Pressione Ctrl+C para encerrar o sistema.")
        # Este loop mantém o script principal vivo. Os handlers de eventos nos outros componentes
        # (Orchestrator, Notifier, Agentes) farão o trabalho real.
        while True:
            await asyncio.sleep(1) # Mantém o loop de eventos rodando

    except KeyboardInterrupt:
        logger.info("Operação cancelada pelo usuário (Ctrl+C).")
    except Exception as e:
        logger.error(f"Erro na execução principal do fluxo EDA: {str(e)}", exc_info=True)
    finally:
        logger.info("Iniciando processo de encerramento do sistema EDA...")

        # Parar o Orchestrator e Notifier (eles podem precisar de métodos de shutdown assíncronos)
        if 'orchestrator' in locals() and hasattr(orchestrator, 'shutdown'):
            await orchestrator.shutdown()
        if 'notifier' in locals() and hasattr(notifier, 'shutdown'):
            await notifier.shutdown()

        # Parar o event_bus (que deve parar seus consumidores)
        if 'event_bus' in locals() and hasattr(event_bus, 'shutdown'):
            await event_bus.shutdown()

        # Limpar agentes
        if 'agents_for_flow' in locals():
            for agent_name, agent_instance in agents_for_flow.items():
                if hasattr(agent_instance, 'cleanup'):
                    logger.info(f"Limpando agente: {agent_name}")
                    await agent_instance.cleanup()

        # Cancelar quaisquer outras tarefas asyncio pendentes
        for task in running_tasks:
            if not task.done():
                task.cancel()
        if running_tasks:
            await asyncio.gather(*running_tasks, return_exceptions=True)

        logger.info("Sistema EDA encerrado.")


if __name__ == "__main__":
    # Configurar signal handler para Ctrl+C
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def handle_sigint():
        logger.info("SIGINT recebido, sinalizando para parar...")
        stop_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, handle_sigint)
    except NotImplementedError: # Em Windows, add_signal_handler não é totalmente suportado para SIGINT
        logger.warning("add_signal_handler para SIGINT não é suportado nesta plataforma (provavelmente Windows). Use Ctrl+Break ou feche o console.")

    # Envolve a execução principal em uma task para que possa ser cancelada pelo stop_event
    main_task = loop.create_task(main_eda_flow())

    try:
        # Espera a main_task ou o stop_event
        done, pending = loop.run_until_complete(asyncio.wait([main_task, stop_event.wait()], return_when=asyncio.FIRST_COMPLETED))

        # Se main_task ainda estiver em pending, significa que stop_event.wait() completou primeiro
        if main_task in pending:
            logger.info("Evento de parada acionado, cancelando tarefa principal...")
            main_task.cancel()
            # Esperar que a tarefa principal termine após o cancelamento
            loop.run_until_complete(main_task)
    except KeyboardInterrupt: # Captura Ctrl+C se o signal handler não funcionar (Windows)
        logger.info("KeyboardInterrupt capturado no loop principal. Encerrando.")
        if not main_task.done():
            main_task.cancel()
            loop.run_until_complete(main_task)
    finally:
        logger.info("Encerrando loop de eventos asyncio.")
        loop.close()
        logger.info("Loop de eventos asyncio fechado.")
