import sys
from datetime import datetime

from loguru import logger as _logger

# --- Import GUI log streaming components ---
import asyncio # Moved asyncio import to top as it's used by DB logging too
import sys # Ensure sys is imported
from pathlib import Path
# Assuming app/logger.py, so PROJECT_ROOT is parent.parent
# Adjust if this assumption is wrong for the worker's execution context.
PROJECT_ROOT_PATH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT_PATH))

try:
    from gui.backend.log_streamer import get_log_queue, format_log_record
except ImportError as e:
    # This allows the rest of the application to function if the GUI part is missing,
    # though logs won't go to the GUI queue.
    print(f"INFO: GUI log streaming components not found or import error: {e}. GUI logging will be disabled.", file=sys.stderr) # Make sure to import sys for stderr
    # Define dummy functions so logger setup doesn't crash
    def get_log_queue(): return None
    def format_log_record(record): return None # This was missing in my plan, but it is in the instructions
    # Optionally, set a flag to avoid adding the sink if components are missing
    _gui_logging_enabled = False
else:
    _gui_logging_enabled = True
# --- End GUI log streaming components ---

# --- Import GUI database components ---
try:
    from gui.backend.database import AsyncSessionLocal, LogEntry
    # If log_streamer components are missing, database logging for GUI also doesn't make sense
    if not _gui_logging_enabled: # Assuming _gui_logging_enabled is set by log_streamer import
        raise ImportError("GUI logging disabled, so database logging for GUI is also disabled.")
except ImportError as e:
    print(f"INFO: GUI database components not found or import error: {e}. GUI database logging will be disabled.", file=sys.stderr)
    _gui_db_logging_enabled = False
    # Define dummy LogEntry if needed for the rest of the file not to break, though sink won't use it.
    class LogEntry: pass 
else:
    _gui_db_logging_enabled = True
# --- End GUI database components ---

from app.config import PROJECT_ROOT


_print_level = "INFO"


def define_log_level(print_level="INFO", logfile_level="DEBUG", name: str = None):
    """Adjust the log level to above level"""
    global _print_level
    _print_level = print_level

    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y%m%d%H%M%S")
    log_name = (
        f"{name}_{formatted_date}" if name else formatted_date
    )  # name a log with prefix name

    _logger.remove()
    _logger.add(sys.stderr, level=print_level)
    _logger.add(PROJECT_ROOT / f"logs/{log_name}.log", level=logfile_level)

    # --- Add GUI sink ---
    if _gui_logging_enabled and get_log_queue() is not None:
        log_queue_instance = get_log_queue() # Keep this if get_log_queue() is light and needed for check

        def gui_sink(message):
            # Acessar message.record uma única vez no início
            try:
                record_data = message.record # Keep the full record for flexibility
                record_message_text = record_data["message"]
                # Check if this log record is itself an exception record from Loguru
                is_internal_loguru_error_log = record_data.get("exception") is not None
            except (TypeError, KeyError) as e_record_access:
                # Handles cases where message.record is not a dict or essential keys are missing.
                # This might happen if Loguru internally logs a message that doesn't conform to the standard record structure.
                print(f"Loguru gui_sink: Incapaz de processar registro de log não padrão (erro acesso inicial): {message} | Erro: {e_record_access}", file=sys.stderr)
                return

            try:
                # --- Streaming to WebSocket queue ---
                if _gui_logging_enabled and get_log_queue() is not None: # Check _gui_logging_enabled too
                    # format_log_record is expected to return a serializable dict or None
                    # It should ideally use record_data which we got above.
                    # For safety, pass record_data if format_log_record expects the raw record dict
                    formatted_log_for_ws = format_log_record(record_data)

                    if formatted_log_for_ws is not None:
                        current_loop = None
                        try:
                            current_loop = asyncio.get_event_loop_policy().get_event_loop()
                        except RuntimeError as e_get_loop: # No loop in current thread
                            if not is_internal_loguru_error_log:
                                print(f"Loguru gui_sink (WebSocket): Sem loop asyncio ativo na thread atual para '{record_message_text}'. Erro: {e_get_loop}", file=sys.stderr)
                                print(f"Loguru gui_sink (Fallback): Missed GUI log from thread without asyncio loop: [{record_data.get('level', {}).get('name', 'UNKNOWN')}] {record_message_text}", file=sys.stderr)
                                return
                            # Cannot proceed with queueing if no loop.

                        if current_loop: # If loop was successfully obtained
                            try:
                                # Attempt to get the main running loop for thread-safe operations if needed.
                                main_running_loop = asyncio.get_running_loop()

                                if current_loop is main_running_loop and current_loop.is_running():
                                    get_log_queue().put_nowait(formatted_log_for_ws)
                                elif main_running_loop.is_running():
                                    main_running_loop.call_soon_threadsafe(get_log_queue().put_nowait, formatted_log_for_ws)
                                else: # Main loop not running, or current_loop is not main and not running.
                                    if not is_internal_loguru_error_log:
                                        print(f"Loguru gui_sink (WebSocket): Loop principal/atual do asyncio não está rodando. Log para WebSocket pulado para: '{record_message_text}'", file=sys.stderr)

                            except RuntimeError: # Catches asyncio.get_running_loop() if no loop is set as running
                                if not is_internal_loguru_error_log:
                                     print(f"Loguru gui_sink (WebSocket): Loop principal do asyncio não disponível/rodando para log via WebSocket. Log: '{record_message_text}'", file=sys.stderr)
                            except asyncio.QueueFull:
                                if not is_internal_loguru_error_log:
                                    print(f"Loguru gui_sink (WebSocket): Fila de log para GUI cheia. Log de {record_data.get('name', 'N/A')}:{record_data.get('line', 'N/A')} pode ser perdido: '{record_message_text}'", file=sys.stderr)
                            except Exception as e_ws_put: # Catch other potential errors from put_nowait
                                if not is_internal_loguru_error_log:
                                    print(f"Loguru gui_sink (WebSocket): Erro ao colocar log na fila da GUI: {e_ws_put}. Log: '{record_message_text}'", file=sys.stderr)
                
                # --- Database logging (mantendo desabilitado como no original, mas com estrutura robusta) ---
                if _gui_db_logging_enabled: # Check the new flag
                    # This part is currently disabled in the original code.
                    # If it were enabled, similar loop handling would be needed.
                    # For now, we just acknowledge its state.
                    if False: # Explicitly keeping DB logging disabled
                        async def write_log_to_db():
                            # return # Original disablement
                            async with AsyncSessionLocal() as session:
                                async with session.begin():
                                    try:
                                        db_log_entry = LogEntry(
                                            timestamp=record_data['time'],
                                            level=record_data['level'].name,
                                            message=record_message_text, # Use pre-fetched message
                                            logger_name=record_data['name'],
                                            module=record_data['module'],
                                            function=record_data['function'],
                                            line=record_data['line'],
                                            execution_id=record_data['extra'].get("execution_id")
                                        )
                                        session.add(db_log_entry)
                                        await session.commit()
                                    except Exception as e_db:
                                        if not is_internal_loguru_error_log:
                                            print(f"Loguru gui_sink (DB): Erro ao escrever log no BD: {e_db}. Log: '{record_message_text}'", file=sys.stderr)
                                        await session.rollback()

                        # Logic to call write_log_to_db using appropriate loop (similar to WebSocket)
                        # This would need careful implementation if DB logging is re-enabled.
                        # For now, this part remains effectively disabled.
                        pass # Placeholder if the 'if False' is removed.

            except RuntimeError as e_runtime:
                # Captura "There is no current event loop in thread" ou "Event loop is closed"
                # Esta exceção seria mais provável de asyncio.get_event_loop_policy().get_event_loop() se falhar de forma inesperada
                # ou de asyncio.get_running_loop()
                if "no current event loop" in str(e_runtime).lower() or "event loop is closed" in str(e_runtime).lower():
                    if not is_internal_loguru_error_log:
                        print(f"Loguru gui_sink: Sem loop asyncio ativo ou loop fechado. Log para DB/GUI pulado para: '{record_message_text}'. Erro: {e_runtime}", file=sys.stderr)
                else:
                    if not is_internal_loguru_error_log:
                        print(f"Loguru gui_sink: RuntimeError inesperado: {e_runtime}. Log: '{record_message_text}'", file=sys.stderr)
            except Exception as e_general:
                if not is_internal_loguru_error_log:
                    print(f"Loguru gui_sink: Exceção inesperada ao processar log: {e_general}. Log: '{record_message_text}'", file=sys.stderr)

        _logger.add(gui_sink, level="DEBUG") # Or use logfile_level.
    # --- End GUI sink ---

    return _logger


logger = define_log_level()

# asyncio is now imported at the top.

if __name__ == "__main__":
    logger.info("Starting application")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
