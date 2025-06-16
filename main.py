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
        super().__init__(daemon=True) # Daemon thread para sair se o programa principal sair
        self.agent_instance = agent_instance
        self.stop_event = stop_event
        self.listener_logger = logger # Usar o logger global da app

    def run(self):
        self.listener_logger.info("[KeyboardListener] Iniciando...")
        try:
            while not self.stop_event.is_set():
                # Usar select para checar stdin de forma não bloqueante
                # O timeout de 0.1 segundos faz o loop verificar self.stop_event regularmente
                ready_to_read, _, _ = select.select([sys.stdin], [], [], 0.1)
                if self.stop_event.is_set(): # Checar novamente após o select
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
    # Ensure workspace directory exists
    try:
        workspace_path = config.workspace_root
        os.makedirs(workspace_path, exist_ok=True)
        logger.info(f"[main.py] Ensured workspace directory exists: {workspace_path}")
    except Exception as e_mkdir:
        logger.error(f"[main.py] Could not create workspace directory {config.workspace_root}: {e_mkdir}. Proceeding, but file operations in workspace may fail.")

    # Create and initialize Manus agent
    agent = await Manus.create()
    agent.max_steps = 10 # Max steps per agent.run() cycle
    logger.info(f"[main.py] Agent created. Initial agent.max_steps = {agent.max_steps}, initial state = {agent.state.value}")

    try:
        logger.info(f"[main.py] Starting main execution loop. Agent state: {agent.state.value}")
        loop_iteration = 0
        while agent.state not in [AgentState.USER_HALTED, AgentState.FINISHED, AgentState.ERROR]:
            loop_iteration += 1
            logger.info(f"[main.py] Loop iteration: {loop_iteration}. Current agent state: {agent.state.value}")

            current_prompt_for_run = None # Initialize for each loop iteration

            if agent.state == AgentState.IDLE:
                user_input = ""
                try:
                    user_input = input("Enter your prompt (or 'quit' to exit): ").strip()
                except (EOFError, KeyboardInterrupt) as e:
                    logger.warning(f"[main.py] Input interrupted ({type(e).__name__}) during IDLE state. Setting state to USER_HALTED.")
                    agent.state = AgentState.USER_HALTED
                    if hasattr(agent, 'user_pause_requested_event') and agent.user_pause_requested_event:
                        agent.user_pause_requested_event.set()
                    break

                input_lower = user_input.lower()
                if input_lower == "quit":
                    agent.state = AgentState.USER_HALTED
                    logger.info("[main.py] 'quit' command received in IDLE state. Agent state set to USER_HALTED.")
                    break
                elif not user_input:
                    logger.warning("[main.py] Empty prompt received in IDLE state. Halting.")
                    agent.state = AgentState.USER_HALTED
                    break
                else:
                    current_prompt_for_run = user_input
                    agent.state = AgentState.RUNNING
                    logger.info(f"[main.py] Prompt for run: '{current_prompt_for_run}'. Agent state set to RUNNING.")

            elif agent.state == AgentState.USER_PAUSED:
                user_input = ""
                try:
                    user_input = input("Agent paused. Enter a new command (or 'quit' to halt): ").strip()
                except (EOFError, KeyboardInterrupt) as e:
                    logger.warning(f"[main.py] Input interrupted ({type(e).__name__}) during USER_PAUSED state. Setting state to USER_HALTED.")
                    agent.state = AgentState.USER_HALTED
                    if hasattr(agent, 'user_pause_requested_event') and agent.user_pause_requested_event:
                        agent.user_pause_requested_event.set()
                    break

                input_lower = user_input.lower()
                if input_lower == "quit":
                    agent.state = AgentState.USER_HALTED
                    logger.info("[main.py] 'quit' command received in USER_PAUSED state. Agent state set to USER_HALTED.")
                    break
                elif not user_input:
                    logger.warning("[main.py] Empty command received in USER_PAUSED state. Re-prompting.")
                    continue
                else:
                    # Process as new command
                    agent.update_memory("user", user_input)
                    agent.current_step = 0
                    agent.state = AgentState.RUNNING
                    logger.info(f"[main.py] New command received: '{user_input}'. Agent memory updated, current_step reset. Agent state set to RUNNING.")

            elif agent.state == AgentState.AWAITING_USER_FEEDBACK:
                logger.info("[main.py] Agent is AWAITING_USER_FEEDBACK. Feedback is assumed to be processed by the agent (e.g., via Manus.periodic_user_check_in). Setting state to RUNNING to continue.")
                agent.state = AgentState.RUNNING

            elif agent.state == AgentState.RUNNING:
                 # This case implies agent.run() from a previous iteration returned RUNNING,
                 # or agent state was set to RUNNING by external means within the loop.
                 # This is generally not expected if agent.run() completes fully or enters a wait state.
                 logger.warning("[main.py] Agent is already in RUNNING state at the start of a new input cycle. This is unexpected if not immediately after input processing. Proceeding to agent.run().")
                 # current_prompt_for_run should be None here unless explicitly set by IDLE state handling in the same iteration.

            else: # Should not be reached if loop conditions are correct
                logger.error(f"[main.py] Unexpected agent state {agent.state.value} encountered in main loop. Setting to ERROR.")
                agent.state = AgentState.ERROR
                break

            # Call agent.run() if agent is in RUNNING state
            if agent.state == AgentState.RUNNING:
                run_message = f"Calling agent.run() with {'initial prompt' if current_prompt_for_run else 'existing/updated memory'}."
                logger.info(f"[main.py] {run_message} Current step before run: {agent.current_step}.")

                keyboard_listener_thread = None
                listener_stop_event = None # Define listener_stop_event here for wider scope in finally
                if agent.state == AgentState.RUNNING: # Só iniciar listener se o agente for realmente rodar steps
                    listener_stop_event = threading.Event()
                    keyboard_listener_thread = KeyboardListener(agent, listener_stop_event)
                    logger.info("[main.py] Iniciando KeyboardListener em background...")
                    keyboard_listener_thread.start()

                try:
                    await agent.run(current_prompt_for_run) # Pass prompt if initial, else None
                except Exception as e_run:
                    # Existing general log line (exc_info=True should also provide a traceback,
                    # but the explicit one above is a safeguard for this specific issue)
                    logger.error(f"[main.py] Exception during agent.run(): {type(e_run).__name__} - {e_run}", exc_info=True)
                    agent.state = AgentState.ERROR

                if keyboard_listener_thread is not None and keyboard_listener_thread.is_alive():
                    logger.info("[main.py] Parando KeyboardListener...")
                    if listener_stop_event: # Check if listener_stop_event was initialized
                        listener_stop_event.set()
                    keyboard_listener_thread.join(timeout=0.5) # Espera um pouco pela thread
                    if keyboard_listener_thread.is_alive():
                        logger.warning("[main.py] KeyboardListener não encerrou a tempo.")
                    else:
                        logger.info("[main.py] KeyboardListener encerrado.")

                logger.info(f"[main.py] agent.run() completed. Agent state is now: {agent.state.value}")

            # If state became terminal due to input handling or agent.run error, loop will check condition and exit.
            if agent.state in [AgentState.USER_HALTED, AgentState.FINISHED, AgentState.ERROR]:
                logger.info(f"[main.py] Agent state is {agent.state.value}. Loop will evaluate exit conditions.")
                # continue # Let the while condition handle termination

        logger.info(f"[main.py] Main execution loop finished. Final agent state: {agent.state.value}")
        if agent.state == AgentState.USER_HALTED:
            logger.info("[main.py] Execution halted by user or specific command.")
        elif agent.state == AgentState.FINISHED:
            logger.info("[main.py] Agent processing finished.")
        elif agent.state == AgentState.ERROR:
            logger.error("[main.py] Agent stopped due to an error.")

    except KeyboardInterrupt: # This handles Ctrl+C during the parts of the loop not covered by input()
        logger.warning("[main.py] KeyboardInterrupt caught in main try block. Setting state to USER_HALTED.")
        if agent:
            agent.state = AgentState.USER_HALTED
            if hasattr(agent, 'user_pause_requested_event') and agent.user_pause_requested_event:
                agent.user_pause_requested_event.set()
    except Exception as e:
        logger.exception(f"[main.py] An unexpected error occurred in main: {type(e).__name__} - {e}", exc_info=True)
        if agent:
            agent.state = AgentState.ERROR
    finally:
        logger.info("[main.py] Entering finally block for cleanup.")
        if agent:
            logger.info(f"[main.py] Cleaning up agent resources. Agent state at cleanup: {agent.state.value}")
            await agent.cleanup()
            logger.info("[main.py] Agent resources cleaned up.")
        else:
            logger.info("[main.py] No agent instance to clean up.")

        # Esta é uma salvaguarda, idealmente a thread já foi parada.
        if 'keyboard_listener_thread' in locals() and keyboard_listener_thread is not None and keyboard_listener_thread.is_alive():
            logger.info("[main.py] Finally: Parando KeyboardListener remanescente...")
            if 'listener_stop_event' in locals() and listener_stop_event is not None:
                 listener_stop_event.set()
            keyboard_listener_thread.join(timeout=0.5)
            logger.info("[main.py] Finally: KeyboardListener remanescente encerrado.")


if __name__ == "__main__":
    asyncio.run(main())
