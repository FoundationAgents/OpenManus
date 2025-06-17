import asyncio
import os # Added for workspace directory creation
import sys
import select
import threading
from app.config import config # Added for workspace directory creation

from app.agent.manus import Manus
from app.logger import logger
from app.schema import AgentState # Import AgentState


class KeyboardListener(threading.Thread):
    def __init__(self, agent_instance, stop_event):
        super().__init__(daemon=True) # Thread daemon para sair se o programa principal sair
        self.agent_instance = agent_instance
        self.stop_event = stop_event
        self.listener_logger = logger # Usar o logger global da aplicação

    def run(self):
        self.listener_logger.info("[KeyboardListener] Iniciando...")
        try:
            while not self.stop_event.is_set():
                # Usar select para verificar stdin de forma não bloqueante
                # O timeout de 0.1 segundos faz o loop verificar self.stop_event regularmente
                ready_to_read, _, _ = select.select([sys.stdin], [], [], 0.1)
                if self.stop_event.is_set(): # Verificar novamente após o select
                    break
                if ready_to_read:
                    line = sys.stdin.readline().strip().lower()
                    if line == "p":
                        self.listener_logger.info("[KeyboardListener] Comando 'p' detectado. Sinalizando pausa para o agente.")
                        if hasattr(self.agent_instance, 'user_pause_requested_event'):
                            self.agent_instance.user_pause_requested_event.set()
                        # Não precisa parar a thread aqui; ela será parada quando agent.run() retornar.
        except Exception as e:
            self.listener_logger.error(f"[KeyboardListener] Erro: {e}", exc_info=True)
        finally:
            self.listener_logger.info("[KeyboardListener] Encerrando.")


async def main():
    # Garantir que o diretório do workspace existe
    try:
        workspace_path = config.workspace_root
        os.makedirs(workspace_path, exist_ok=True)
        logger.info(f"[main.py] Diretório do workspace garantido: {workspace_path}")
    except Exception as e_mkdir:
        logger.error(f"[main.py] Não foi possível criar o diretório do workspace {config.workspace_root}: {e_mkdir}. Continuando, mas operações de arquivo no workspace podem falhar.")

    # Criar e inicializar o agente Manus
    agent = await Manus.create()
    agent.max_steps = 10 # Máximo de passos por ciclo agent.run()
    logger.info(f"[main.py] Agente criado. agent.max_steps inicial = {agent.max_steps}, estado inicial = {agent.state.value}")

    try:
        logger.info(f"[main.py] Iniciando loop de execução principal. Estado do agente: {agent.state.value}")
        loop_iteration = 0
        while agent.state not in [AgentState.USER_HALTED, AgentState.FINISHED, AgentState.ERROR]:
            loop_iteration += 1
            logger.info(f"[main.py] Iteração do loop: {loop_iteration}. Estado atual do agente: {agent.state.value}")

            current_prompt_for_run = None # Inicializar para cada iteração do loop

            if agent.state == AgentState.IDLE:
                user_input = ""
                try:
                    user_input = input("Digite seu prompt (ou 'quit' para sair): ").strip()
                except (EOFError, KeyboardInterrupt) as e:
                    logger.warning(f"[main.py] Entrada interrompida ({type(e).__name__}) durante o estado IDLE. Definindo estado para USER_HALTED.")
                    agent.state = AgentState.USER_HALTED
                    if hasattr(agent, 'user_pause_requested_event') and agent.user_pause_requested_event:
                        agent.user_pause_requested_event.set()
                    break

                input_lower = user_input.lower()
                if input_lower == "quit":
                    agent.state = AgentState.USER_HALTED
                    logger.info("[main.py] Comando 'quit' recebido no estado IDLE. Estado do agente definido para USER_HALTED.")
                    break
                elif not user_input:
                    logger.warning("[main.py] Prompt vazio recebido no estado IDLE. Interrompendo.")
                    agent.state = AgentState.USER_HALTED
                    break
                else:
                    current_prompt_for_run = user_input
                    agent.state = AgentState.RUNNING
                    logger.info(f"[main.py] Prompt para execução: '{current_prompt_for_run}'. Estado do agente definido para RUNNING.")

            elif agent.state == AgentState.USER_PAUSED:
                user_input = ""
                try:
                    user_input = input("Agente pausado. Digite um novo comando (ou 'quit' para interromper): ").strip()
                except (EOFError, KeyboardInterrupt) as e:
                    logger.warning(f"[main.py] Entrada interrompida ({type(e).__name__}) durante o estado USER_PAUSED. Definindo estado para USER_HALTED.")
                    agent.state = AgentState.USER_HALTED
                    if hasattr(agent, 'user_pause_requested_event') and agent.user_pause_requested_event:
                        agent.user_pause_requested_event.set()
                    break

                input_lower = user_input.lower()
                if input_lower == "quit":
                    agent.state = AgentState.USER_HALTED
                    logger.info("[main.py] Comando 'quit' recebido no estado USER_PAUSED. Estado do agente definido para USER_HALTED.")
                    break
                elif not user_input:
                    logger.warning("[main.py] Comando vazio recebido no estado USER_PAUSED. Solicitando novamente.")
                    continue
                else:
                    # Processar como novo comando
                    agent.update_memory("user", user_input)
                    agent.current_step = 0
                    agent.state = AgentState.RUNNING
                    logger.info(f"[main.py] Novo comando recebido: '{user_input}'. Memória do agente atualizada, current_step redefinido. Estado do agente definido para RUNNING.")

            elif agent.state == AgentState.AWAITING_USER_FEEDBACK:
                logger.info("[main.py] Agente está AWAITING_USER_FEEDBACK. Feedback é assumido como processado pelo agente (ex: via Manus.periodic_user_check_in). Definindo estado para RUNNING para continuar.")
                agent.state = AgentState.RUNNING

            elif agent.state == AgentState.RUNNING:
                 # Este caso implica que agent.run() de uma iteração anterior retornou RUNNING,
                 # ou o estado do agente foi definido para RUNNING por meios externos dentro do loop.
                 # Geralmente, isso não é esperado se agent.run() completar totalmente ou entrar em estado de espera.
                 logger.warning("[main.py] Agente já está no estado RUNNING no início de um novo ciclo de entrada. Isso é inesperado se não for imediatamente após o processamento da entrada. Prosseguindo para agent.run().")
                 # current_prompt_for_run deve ser None aqui, a menos que explicitamente definido pelo tratamento do estado IDLE na mesma iteração.

            else: # Não deve ser alcançado se as condições do loop estiverem corretas
                logger.error(f"[main.py] Estado inesperado do agente {agent.state.value} encontrado no loop principal. Definindo para ERROR.")
                agent.state = AgentState.ERROR
                break

            # Chamar agent.run() se o agente estiver no estado RUNNING
            if agent.state == AgentState.RUNNING:
                run_message = f"Chamando agent.run() com {'prompt inicial' if current_prompt_for_run else 'memória existente/atualizada'}."
                logger.info(f"[main.py] {run_message} Passo atual antes da execução: {agent.current_step}.")

                keyboard_listener_thread = None
                listener_stop_event = None # Definir listener_stop_event aqui para escopo mais amplo no finally
                if agent.state == AgentState.RUNNING: # Só iniciar listener se o agente for realmente executar passos
                    listener_stop_event = threading.Event()
                    keyboard_listener_thread = KeyboardListener(agent, listener_stop_event)
                    logger.info("[main.py] Iniciando KeyboardListener em background...")
                    keyboard_listener_thread.start()

                try:
                    await agent.run(current_prompt_for_run) # Passar prompt se inicial, senão None
                except Exception as e_run:
                    # Linha de log geral existente (exc_info=True também deve fornecer um traceback,
                    # mas a explícita acima é uma salvaguarda para este problema específico)
                    logger.error(f"[main.py] Exceção durante agent.run(): {type(e_run).__name__} - {e_run}", exc_info=True)
                    agent.state = AgentState.ERROR

                if keyboard_listener_thread is not None and keyboard_listener_thread.is_alive():
                    logger.info("[main.py] Parando KeyboardListener...")
                    if listener_stop_event: # Verificar se listener_stop_event foi inicializado
                        listener_stop_event.set()
                    keyboard_listener_thread.join(timeout=0.5) # Esperar um pouco pela thread
                    if keyboard_listener_thread.is_alive():
                        logger.warning("[main.py] KeyboardListener não encerrou a tempo.")
                    else:
                        logger.info("[main.py] KeyboardListener encerrado.")

                logger.info(f"[main.py] agent.run() concluído. Estado do agente agora é: {agent.state.value}")

            # Se o estado se tornou terminal devido ao tratamento de entrada ou erro em agent.run, o loop verificará a condição e sairá.
            if agent.state in [AgentState.USER_HALTED, AgentState.FINISHED, AgentState.ERROR]:
                logger.info(f"[main.py] Estado do agente é {agent.state.value}. Loop avaliará condições de saída.")
                # continue # Deixar a condição while lidar com a terminação

        logger.info(f"[main.py] Loop de execução principal finalizado. Estado final do agente: {agent.state.value}")
        if agent.state == AgentState.USER_HALTED:
            logger.info("[main.py] Execução interrompida pelo usuário ou comando específico.")
        elif agent.state == AgentState.FINISHED:
            logger.info("[main.py] Processamento do agente finalizado.")
        elif agent.state == AgentState.ERROR:
            logger.error("[main.py] Agente parado devido a um erro.")

    except KeyboardInterrupt: # Isso lida com Ctrl+C durante as partes do loop não cobertas por input()
        logger.warning("[main.py] KeyboardInterrupt capturado no bloco try principal. Definindo estado para USER_HALTED.")
        if agent:
            agent.state = AgentState.USER_HALTED
            if hasattr(agent, 'user_pause_requested_event') and agent.user_pause_requested_event:
                agent.user_pause_requested_event.set()
    except Exception as e:
        logger.exception(f"[main.py] Um erro inesperado ocorreu no main: {type(e).__name__} - {e}", exc_info=True)
        if agent:
            agent.state = AgentState.ERROR
    finally:
        logger.info("[main.py] Entrando no bloco finally para limpeza.")
        if agent:
            logger.info(f"[main.py] Limpando recursos do agente. Estado do agente na limpeza: {agent.state.value}")
            await agent.cleanup()
            logger.info("[main.py] Recursos do agente limpos.")
        else:
            logger.info("[main.py] Nenhuma instância de agente para limpar.")

        # Esta é uma salvaguarda, idealmente a thread já foi parada.
        if 'keyboard_listener_thread' in locals() and keyboard_listener_thread is not None and keyboard_listener_thread.is_alive():
            logger.info("[main.py] Finally: Parando KeyboardListener remanescente...")
            if 'listener_stop_event' in locals() and listener_stop_event is not None:
                 listener_stop_event.set()
            keyboard_listener_thread.join(timeout=0.5)
            logger.info("[main.py] Finally: KeyboardListener remanescente encerrado.")


if __name__ == "__main__":
    asyncio.run(main())
