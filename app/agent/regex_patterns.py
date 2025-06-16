import os
import re
import sys # Import sys for stderr printing if needed

# Variable to store the compiled regex pattern
re_subprocess = None
_pattern_file_path = "" # Define for potential use in error messages outside try

try:
    # Constrói o caminho para o arquivo de forma segura
    dir_path = os.path.dirname(os.path.realpath(__file__))
    _pattern_file_path = os.path.join(dir_path, 're_subprocess_pattern.txt')

    with open(_pattern_file_path, 'r', encoding='utf-8') as f:
        pattern_str = f.read().strip()

    if not pattern_str:
        # This case means the file was empty or contained only whitespace.
        raise ValueError(f"CRITICAL: Regex pattern file '{_pattern_file_path}' is empty or invalid. "
                         "The application cannot proceed without a valid pattern.")

    # Carrega o padrão e o compila para uso na aplicação
    re_subprocess = re.compile(pattern_str)

except FileNotFoundError:
    # Lança um erro claro se o arquivo de padrão estiver faltando
    # Print to stderr for immediate visibility if possible, then raise
    error_message = f"CRITICAL ERROR: Regex pattern file 're_subprocess_pattern.txt' not found at expected path: {_pattern_file_path}. The application cannot initialize."
    print(error_message, file=sys.stderr)
    raise RuntimeError(error_message) from None # Using from None to break the chain of exceptions, as FileNotFoundError is the root cause here

except (IOError, OSError) as e:
    # Captura outros possíveis erros de leitura de arquivo
    error_message = f"CRITICAL ERROR: Failed to read or process regex pattern file '{_pattern_file_path}'. Exception: {e}"
    print(error_message, file=sys.stderr)
    raise RuntimeError(error_message) from e

except ValueError as e: # Specifically for the empty pattern check
    error_message = str(e) # The message is already well-formed in the raise statement
    print(error_message, file=sys.stderr)
    raise RuntimeError(error_message) from e

except Exception as e:
    # Captura outros possíveis erros (e.g., re.error from compile)
    err_msg_path_display = _pattern_file_path if _pattern_file_path else "unknown path"
    error_message = f"CRITICAL ERROR: An unexpected error occurred while loading/compiling the regex pattern from '{err_msg_path_display}'. Exception type: {type(e).__name__}, Exception: {e}"
    print(error_message, file=sys.stderr)
    raise RuntimeError(error_message) from e

# Final check to ensure the compiled regex is available.
if re_subprocess is None:
    # This state should ideally not be reached if the above error handling is comprehensive.
    # However, as a safeguard:
    final_err_msg_path_display = _pattern_file_path if _pattern_file_path else "path not determined"
    critical_final_error = f"CRITICAL FAILURE: Regex pattern 're_subprocess' was not successfully compiled from '{final_err_msg_path_display}' by the end of the script. This indicates an unexpected issue in the loading logic. Application cannot proceed."
    print(critical_final_error, file=sys.stderr)
    raise RuntimeError(critical_final_error)
