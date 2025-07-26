import os
import asyncio
import json # Import json for structured output
from typing import List, Dict, Any, Optional # Optional is already here

from app.tool.base import BaseTool, ToolResult
from app.config import config # To access workspace_root
import aiofiles # For async file operations
import logging # For logging potential issues during the tool's execution

logger = logging.getLogger(__name__)

# Developer Note:
# The rich diagnostic output from this tool (when a file/directory is not found)
# is returned as a JSON string in ToolResult.output.
# An agent could parse this JSON and use the information for more intelligent error handling.
# For example:
# - Compare `checked_path_absolute` with user-provided paths to identify discrepancies.
# - Use `parent_directory_listing` to suggest alternative files if `checked_path_original`
#   seems like a typo (e.g., "Did you mean 'prompt.txt.bkp' instead of 'prompt.txt'?").
# - Log `current_working_directory` to help diagnose issues if the agent is not running
#   in the expected directory.
class CheckFileExistenceTool(BaseTool):
    name: str = "check_file_existence"
    description: str = (
        "Verifica se um arquivo ou diretório existe no caminho especificado. "
        "Retorna SUCESSO se encontrado, ou FALHA com informações de diagnóstico detalhadas se não encontrado, "
        "incluindo o caminho absoluto verificado, o diretório de trabalho atual (CWD), "
        "e uma listagem do diretório pai."
    )

    async def _get_path_details(self, path: str) -> tuple[str, str, list[str] | str]:
        """Helper function to get absolute path, CWD, and parent directory listing."""
        try:
            # Get absolute path
            absolute_path = await asyncio.to_thread(os.path.abspath, path)
        except Exception as e:
            logger.warning(f"Error getting absolute path for {path}: {e}")
            absolute_path = f"Erro ao obter caminho absoluto: {e}"

        try:
            # Get current working directory
            current_working_directory = await asyncio.to_thread(os.getcwd)
        except Exception as e:
            logger.warning(f"Error getting CWD: {e}")
            current_working_directory = f"Erro ao obter CWD: {e}"

        parent_directory_listing: list[str] | str = []
        try:
            parent_dir = await asyncio.to_thread(os.path.dirname, absolute_path if isinstance(absolute_path, str) and not absolute_path.startswith("Erro") else path)
            if not parent_dir: # Handle cases like root or relative paths without a clear parent in the input
                 parent_dir = current_working_directory # Default to CWD if parent_dir is empty

            if await asyncio.to_thread(os.path.exists, parent_dir):
                if await asyncio.to_thread(os.path.isdir, parent_dir):
                    parent_directory_listing = await asyncio.to_thread(os.listdir, parent_dir)
                else:
                    parent_directory_listing = f"O caminho pai '{parent_dir}' não é um diretório."
            else:
                parent_directory_listing = f"O diretório pai '{parent_dir}' não foi encontrado."
        except Exception as e:
            logger.warning(f"Error listing parent directory for {path} (parent: {parent_dir if 'parent_dir' in locals() else 'N/A'}): {e}")
            parent_directory_listing = f"Erro ao listar o diretório pai: {e}"

        return absolute_path, current_working_directory, parent_directory_listing

    async def execute(self, path: str) -> ToolResult:
        path_exists = False
        error_message = None
        absolute_path_checked = ""

        try:
            # Ensure path is a string
            if not isinstance(path, str):
                return ToolResult(error=f"Erro de tipo: o caminho fornecido '{path}' não é uma string.")

            # Attempt to get absolute path early for diagnostics, even if it fails
            try:
                absolute_path_checked = await asyncio.to_thread(os.path.abspath, path)
            except Exception as e:
                absolute_path_checked = f"Não foi possível determinar o caminho absoluto para '{path}': {e}"
                logger.warning(f"Could not get abspath for {path} during execute: {e}")


            path_exists = await asyncio.to_thread(os.path.exists, path)

            if path_exists:
                output_data = {
                    "status": "SUCESSO",
                    "message": f"O arquivo ou diretório em '{path}' foi encontrado.",
                    "checked_path_original": path,
                    "checked_path_absolute": absolute_path_checked
                }
                # Attempt to convert to JSON string for output, fallback to repr
                try:
                    output_str = json.dumps(output_data, ensure_ascii=False, indent=2)
                except Exception:
                    output_str = repr(output_data)
                return ToolResult(output=output_str)
            else:
                # If not found, gather diagnostic information
                abs_path_diag, cwd_diag, parent_listing_diag = await self._get_path_details(path)

                output_data = {
                    "status": "FALHA",
                    "message": f"O arquivo ou diretório em '{path}' NÃO foi encontrado.",
                    "checked_path_original": path,
                    "checked_path_absolute": abs_path_diag, # Use the one from _get_path_details as it's more robustly attempted
                    "current_working_directory": cwd_diag,
                    "parent_directory_listing": parent_listing_diag
                }
                # Attempt to convert to JSON string for output, fallback to repr
                try:
                    output_str = json.dumps(output_data, ensure_ascii=False, indent=2)
                except Exception:
                    output_str = repr(output_data)
                return ToolResult(output=output_str)

        except Exception as e:
            logger.error(f"Erro inesperado na ferramenta CheckFileExistenceTool para o caminho '{path}': {e}", exc_info=True)
            # Gather diagnostic info even in case of an unexpected error during the check itself
            abs_path_diag, cwd_diag, parent_listing_diag = await self._get_path_details(path)

            error_output_data = {
                "status": "ERRO_INESPERADO",
                "message": f"Erro inesperado ao verificar a existência de '{path}': {str(e)}",
                "checked_path_original": path,
                "checked_path_absolute": abs_path_diag if abs_path_diag else absolute_path_checked,
                "current_working_directory": cwd_diag,
                "parent_directory_listing": parent_listing_diag
            }
            try:
                error_str = json.dumps(error_output_data, ensure_ascii=False, indent=2)
            except Exception:
                error_str = repr(error_output_data)
            return ToolResult(error=error_str)


class ListFilesTool(BaseTool):
    name: str = "list_files"
    description: str = (
        "Lista arquivos e diretórios em um caminho especificado, de forma recursiva até uma profundidade definida. "
        "Use esta ferramenta para obter consciência situacional do workspace ou para ver quais arquivos estão disponíveis."
    )
    args_schema: dict = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string", # Em JSON schema, 'null' pode ser um tipo ou usar anyOf para opcionalidade, mas aqui o campo é opcional pela ausencia em 'required'
                "description": "O caminho do diretório a ser listado. Se não fornecido, lista o diretório de trabalho atual do agente (config.workspace_root).",
            },
            "depth": {
                "type": "integer",
                "default": 1,
                "description": "Profundidade máxima da listagem recursiva. 0 para profundidade ilimitada (use com cautela), 1 para listar apenas o conteúdo do diretório especificado (sem recursão).",
            },
        },
        "required": [], # path e depth são opcionais, seus defaults são tratados na lógica da ferramenta
    }

    async def execute(self, path: Optional[str] = None, depth: int = 1) -> ToolResult:
        try:
            if path is None:
                start_path = str(config.workspace_root)
                logger.info(f"Nenhum caminho fornecido, usando o workspace_root: {start_path}")
            else:
                # Verificar se o caminho é absoluto. Se não, considerar relativo ao workspace_root.
                if not await asyncio.to_thread(os.path.isabs, path):
                    start_path = str(config.workspace_root / path)
                    logger.info(f"Caminho relativo fornecido '{path}', resolvido para: {start_path}")
                else:
                    start_path = path
                    logger.info(f"Caminho absoluto fornecido: {start_path}")

            # Validar se o start_path está dentro do workspace_root para segurança
            # Convertendo ambos para caminhos absolutos resolvidos antes de comparar
            resolved_start_path = await asyncio.to_thread(os.path.realpath, start_path)
            resolved_workspace_root = await asyncio.to_thread(os.path.realpath, str(config.workspace_root))

            if not resolved_start_path.startswith(resolved_workspace_root):
                logger.warning(f"Tentativa de listar arquivos fora do workspace: {resolved_start_path}")
                return ToolResult(error=f"Erro: O caminho especificado '{path}' está fora do diretório de trabalho permitido.")

            if not await asyncio.to_thread(os.path.exists, start_path):
                return ToolResult(error=f"Erro: O caminho '{start_path}' não existe.")
            if not await asyncio.to_thread(os.path.isdir, start_path):
                return ToolResult(error=f"Erro: O caminho '{start_path}' não é um diretório.")

            result_tree: Dict[str, Any] = {"path": os.path.basename(start_path), "type": "directory", "children": []}

            # Usar asyncio.to_thread para rodar os.walk em um thread separado
            # já que os.walk é bloqueante.
            # A lógica de profundidade precisa ser gerenciada manualmente dentro do loop.

            # Normalizar start_path para garantir que a contagem de profundidade seja consistente
            normalized_start_path = await asyncio.to_thread(os.path.normpath, start_path)
            start_depth = normalized_start_path.count(os.sep)

            # Para evitar TimeoutError com asyncio.to_thread em operações longas,
            # podemos precisar de uma abordagem mais granular ou um executor de threadpool customizado.
            # Para este caso, vamos confiar que os.walk não será excessivamente longo para profundidades razoáveis.

            loop = asyncio.get_event_loop()
            # Precisamos coletar os resultados de os.walk, que é um gerador.
            # O wrapper to_thread não lida bem com geradores diretamente para consumo assíncrono.
            # Uma forma é converter o gerador para uma lista dentro do thread.

            def walk_and_collect(root_dir, max_depth):
                collected_items = []
                for root, dirs, files in os.walk(root_dir, topdown=True):
                    current_rel_path = os.path.relpath(root, normalized_start_path)
                    current_depth = current_rel_path.count(os.sep) if current_rel_path != '.' else 0

                    if max_depth == 0 or current_depth < max_depth:
                        # Processa diretórios
                        dir_children_map = {d: [] for d in dirs}
                        # Processa arquivos
                        file_children = [{"path": f, "type": "file"} for f in files]

                        collected_items.append({
                            "root": root,
                            "dirs": dirs,
                            "files": files,
                            "current_depth": current_depth,
                            "rel_path": current_rel_path
                        })

                        # Controlar a recursão podando a lista dirs se a profundidade atual + 1 == max_depth
                        if max_depth > 0 and current_depth + 1 >= max_depth:
                            dirs[:] = [] # Modifica dirs in-place para parar a descida
                    elif current_depth >= max_depth and max_depth > 0 : # Se já estivermos na profundidade máxima, não desça mais
                        dirs[:] = []


                return collected_items

            collected_walk_results = await loop.run_in_executor(None, walk_and_collect, normalized_start_path, depth)

            # Agora, construa a árvore JSON a partir dos resultados coletados
            # Esta parte é um pouco complexa para reconstruir a árvore a partir de uma lista plana de resultados de os.walk
            # Uma abordagem mais simples para a saída JSON pode ser uma lista de caminhos ou uma estrutura mais plana.
            # Por simplicidade, vamos retornar uma lista de caminhos por enquanto,
            # e podemos revisitar a estrutura de árvore se necessário.

            output_list = []
            if not collected_walk_results and depth == 1: # Caso especial para profundidade 1 e sem subdiretórios
                # os.walk pode não entrar no loop principal se o diretório estiver vazio ou depth=1 e só houver arquivos
                # Vamos listar manualmente para depth=1
                 try:
                    entries = await asyncio.to_thread(os.listdir, normalized_start_path)
                    for entry in entries:
                        entry_path = os.path.join(normalized_start_path, entry)
                        entry_type = "directory" if await asyncio.to_thread(os.path.isdir, entry_path) else "file"
                        output_list.append({"path": entry, "type": entry_type, "depth": 1})
                 except Exception as e_listdir:
                    logger.error(f"Erro ao listar manualmente {normalized_start_path} para depth=1: {e_listdir}")
                    return ToolResult(error=f"Erro ao listar diretório: {e_listdir}")


            for item in collected_walk_results:
                # rel_path '.' significa o diretório raiz que está sendo listado
                base_path_for_item = item['rel_path'] if item['rel_path'] != '.' else ''

                for d_name in item['dirs']:
                    # Adicionar apenas se a profundidade do diretório em si estiver dentro do limite
                    # A poda em walk_and_collect já deve cuidar disso, mas uma verificação dupla não faz mal.
                    if depth == 0 or item['current_depth'] < depth:
                         output_list.append({
                            "path": os.path.join(base_path_for_item, d_name) if base_path_for_item else d_name,
                            "type": "directory",
                            "depth": item['current_depth'] + 1
                        })
                for f_name in item['files']:
                    if depth == 0 or item['current_depth'] < depth :
                        output_list.append({
                            "path": os.path.join(base_path_for_item, f_name) if base_path_for_item else f_name,
                            "type": "file",
                            "depth": item['current_depth'] + 1
                        })

            # Se depth é 0 (ilimitado), e a lista está vazia, mas o diretório existe (verificado no início),
            # isso significa que o diretório está realmente vazio.
            # Se depth > 0 e a lista está vazia, também pode significar que o diretório está vazio.
            if not output_list and await asyncio.to_thread(os.path.isdir, normalized_start_path):
                 # Verifica se o diretório está realmente vazio
                if not await asyncio.to_thread(os.listdir, normalized_start_path):
                    return ToolResult(output=json.dumps({"path": os.path.basename(normalized_start_path), "type": "directory", "children": [], "message": "O diretório está vazio."}, ensure_ascii=False, indent=2))


            # A estrutura de árvore JSON é mais complexa de construir iterativamente a partir de os.walk.
            # Vamos retornar uma lista achatada de arquivos e diretórios com seus caminhos relativos e tipos.
            # A profundidade também será incluída para cada item.
            # Ex: [{"path": "file.txt", "type": "file", "depth": 1}, {"path": "subdir/file2.txt", "type": "file", "depth": 2}]
            # Se output_list ainda estiver vazia aqui, significa que o diretório pode estar vazio ou algo deu errado.
            # Mas as verificações iniciais devem cobrir a existência do diretório.

            # Se a lista de saída estiver vazia e o diretório não estiver (verificado por listdir anteriormente para depth=1),
            # pode indicar um problema na lógica de coleta. No entanto, se o diretório estiver realmente vazio,
            # a mensagem de "O diretório está vazio" já terá sido retornada.

            final_output_structure = {
                "listed_path": os.path.basename(normalized_start_path),
                "base_path_absolute": normalized_start_path,
                "requested_depth": depth,
                "items": sorted(output_list, key=lambda x: (x['depth'], x['type'], x['path'])) # Ordenar para consistência
            }
            return ToolResult(output=json.dumps(final_output_structure, ensure_ascii=False, indent=2))

        except Exception as e:
            logger.error(f"Erro inesperado na ferramenta ListFilesTool para o caminho '{path}' e profundidade '{depth}': {e}", exc_info=True)
            return ToolResult(error=f"Erro inesperado ao listar arquivos: {str(e)}")
