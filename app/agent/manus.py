import os
import uuid
from typing import Dict, List, Optional, Any

from pydantic import Field, model_validator, PrivateAttr

import json
import re
import ast # Added for AST parsing
# os is already imported
from app.agent.browser import BrowserContextHelper
from app.agent.toolcall import ToolCallAgent, ToolCall
from app.config import config
from app.logger import logger
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import AgentState, Message, Role, Function as FunctionCall
from app.sandbox.client import SANDBOX_CLIENT
from app.tool import Terminate, ToolCollection
from app.exceptions import ToolError
from app.tool.ask_human import AskHuman
from app.tool.bash import Bash
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.mcp import MCPClients, MCPClientTool
from app.tool.python_execute import PythonExecute
from app.tool.sandbox_python_executor import SandboxPythonExecutor
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.file_operators import LocalFileOperator

from app.tool.read_file_content import ReadFileContentTool
from app.tool.checklist_tools import ViewChecklistTool, AddChecklistTaskTool, UpdateChecklistTaskTool
from app.tool.file_system_tools import CheckFileExistenceTool, ListFilesTool # Added ListFilesTool
from app.agent.checklist_manager import ChecklistManager # Added for _is_checklist_complete
from .regex_patterns import re_subprocess
from app.tool.background_process_tools import ExecuteBackgroundProcessTool, CheckProcessStatusTool, GetProcessOutputTool


# Nova constante para autoanálise interna
INTERNAL_SELF_ANALYSIS_PROMPT_TEMPLATE = """Você é Manus. Você está em um ponto de verificação com o usuário.
Analise o histórico recente da conversa (últimas {X} mensagens), o estado atual do seu checklist de tarefas (fornecido abaixo), e quaisquer erros ou dificuldades que você encontrou.
Com base nisso, gere um "Relatório de Autoanálise e Planejamento" conciso em português para apresentar ao usuário.
O relatório deve incluir:
1. Um breve diagnóstico da sua situação atual, incluindo a **causa raiz de quaisquer dificuldades ou erros recentes** (ex: "Estou tentando X, mas a ferramenta Y falhou com o erro Z. Acredito que a causa raiz foi [uma má escolha de parâmetros para a ferramenta / a ferramenta não ser adequada para esta subtarefa / um problema no meu plano original / etc.]").
2. Pelo menos uma ou duas **estratégias alternativas CONCRETAS** que você pode tentar para superar essas dificuldades, incluindo **correções específicas** para erros, se aplicável (Ex: "Pensei em tentar A [descrever A, e.g., 'usar a ferramenta Y com parâmetro W corrigido'] ou B [descrever B, e.g., 'usar a ferramenta Q em vez da Y para esta etapa'] como alternativas.").
3. Uma sugestão de **como você pode evitar erros semelhantes no futuro** (Ex: "Para evitar este erro no futuro, vou [verificar X antes de usar a ferramenta Y / sempre usar a ferramenta Q para este tipo de tarefa / etc.]").
4. Opcional: Se você tiver um plano preferido ou mais elaborado para uma das alternativas, mencione-o brevemente.

Formate a resposta APENAS com o relatório. Não adicione frases introdutórias como "Claro, aqui está o relatório".
Se não houver dificuldades significativas ou alternativas claras, indique isso de forma concisa (ex: "Diagnóstico: Progresso está estável na tarefa atual. Alternativas: Nenhuma alternativa principal considerada no momento.").

Conteúdo do Checklist Principal (`checklist_principal_tarefa.md`):
{checklist_content}
"""


class Manus(ToolCallAgent):
    """Um agente versátil de propósito geral com suporte para ferramentas locais e MCP."""

    name: str = "Manus"
    description: str = "Um agente versátil que pode resolver várias tarefas usando múltiplas ferramentas, incluindo ferramentas baseadas em MCP"

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20

    _mcp_clients: Optional[MCPClients] = PrivateAttr(default=None)
    _monitoring_background_task: bool = PrivateAttr(default=False)
    _background_task_log_file: Optional[str] = PrivateAttr(default=None)
    _background_task_expected_artifact: Optional[str] = PrivateAttr(default=None)
    _background_task_artifact_path: Optional[str] = PrivateAttr(default=None)
    _background_task_description: Optional[str] = PrivateAttr(default=None)
    _background_task_last_log_size: int = PrivateAttr(default=0)
    _background_task_no_change_count: int = PrivateAttr(default=0)
    _MAX_LOG_NO_CHANGE_TURNS: int = PrivateAttr(default=3)
    _just_resumed_from_feedback: bool = PrivateAttr(default=False)
    _trigger_failure_check_in: bool = PrivateAttr(default=False)
    _pending_script_after_dependency: Optional[str] = PrivateAttr(default=None)
    _original_tool_call_for_pending_script: Optional[ToolCall] = PrivateAttr(default=None)
    _workspace_script_analysis_cache: Optional[Dict[str, Dict[str, Any]]] = PrivateAttr(default=None)
    _current_sandbox_pid: Optional[int] = PrivateAttr(default=None)
    _current_sandbox_pid_file: Optional[str] = PrivateAttr(default=None)
    _current_script_tool_call_id: Optional[str] = PrivateAttr(default=None)
    _fallback_attempted_for_tool_call_id: Optional[str] = PrivateAttr(default=None)
    _pending_fallback_tool_call: Optional[ToolCall] = PrivateAttr(default=None)
    _last_ask_human_for_fallback_id: Optional[str] = PrivateAttr(default=None)
    _autonomous_mode: bool = PrivateAttr(default=False) # Flag to indicate if the agent should operate without asking for continuation feedback periodically.


    def __getstate__(self):
        logger.info(f"Manus.__getstate__ chamado para instância: {self!r}")
        state = self.__dict__.copy()
        state.pop('_mcp_clients', None)
        state.pop('available_tools', None)
        state.pop('llm', None)
        logger.info(f"Manus.__getstate__ chaves finais: {list(state.keys())}")
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        
        from app.llm import LLM
        from app.tool import ToolCollection
        from app.tool.mcp import MCPClients
        from app.tool.python_execute import PythonExecute
        from app.tool.str_replace_editor import StrReplaceEditor
        from app.tool.ask_human import AskHuman
        from app.tool.terminate import Terminate
        from app.tool.bash import Bash
        from app.tool.sandbox_python_executor import SandboxPythonExecutor
        from app.tool.browser_use_tool import BrowserUseTool
        from app.tool.code_formatter import FormatPythonCode
        from app.tool.code_editor_tools import ReplaceCodeBlock, ApplyDiffPatch, ASTRefactorTool

        from app.tool.read_file_content import ReadFileContentTool
        from app.tool.checklist_tools import ViewChecklistTool, AddChecklistTaskTool, UpdateChecklistTaskTool
        from app.tool.file_system_tools import ListFilesTool # Adicionado ListFilesTool
        # Imports for background process tools already added at the top of the file for __init__
        # No need to re-import here if they are module-level imports

        llm_config_name = "manus"
        if 'name' in state and state['name']:
            llm_config_name = state['name'].lower()
        elif hasattr(self, 'name') and self.name:
            llm_config_name = self.name.lower()
        self.llm = LLM(config_name=llm_config_name)
        self._mcp_clients = MCPClients()

        self.available_tools = ToolCollection(
            PythonExecute(), StrReplaceEditor(), AskHuman(), Terminate(), Bash(),
            SandboxPythonExecutor(), BrowserUseTool(), FormatPythonCode(),

            ReplaceCodeBlock(), ApplyDiffPatch(), ASTRefactorTool(), ReadFileContentTool(),
            ViewChecklistTool(), AddChecklistTaskTool(), UpdateChecklistTaskTool(),
            CheckFileExistenceTool(), ListFilesTool(),
            ExecuteBackgroundProcessTool(), CheckProcessStatusTool(), GetProcessOutputTool()
        )
        self._initialized = False
        self.connected_servers = {}
        
    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])
    browser_context_helper: Optional[Any] = None
    planned_tool_calls: List[ToolCall] = Field(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        self._mcp_clients = MCPClients()
        from app.tool.code_formatter import FormatPythonCode
        from app.tool.code_editor_tools import ReplaceCodeBlock, ApplyDiffPatch, ASTRefactorTool

        from app.tool.read_file_content import ReadFileContentTool
        from app.tool.checklist_tools import ViewChecklistTool, AddChecklistTaskTool, UpdateChecklistTaskTool
        from app.tool.file_system_tools import ListFilesTool # Adicionado ListFilesTool
        self.available_tools = ToolCollection(
            PythonExecute(), BrowserUseTool(), StrReplaceEditor(), AskHuman(), Terminate(),
            Bash(), SandboxPythonExecutor(), FormatPythonCode(), ReplaceCodeBlock(),
            ApplyDiffPatch(), ASTRefactorTool(), ReadFileContentTool(),
            ViewChecklistTool(), AddChecklistTaskTool(), UpdateChecklistTaskTool(),
            CheckFileExistenceTool(), ListFilesTool(),
            ExecuteBackgroundProcessTool(), CheckProcessStatusTool(), GetProcessOutputTool()
        )

    connected_servers: Dict[str, str] = Field(default_factory=dict)
    _initialized: bool = False

    @model_validator(mode="after")
    def initialize_helper(self) -> "Manus":
        self.browser_context_helper = BrowserContextHelper(self)
        return self

    @classmethod
    async def create(cls, **kwargs) -> "Manus":
        instance = cls(**kwargs)
        logger.info(f"Agente Manus criado. Prompt do sistema (primeiros 500 caracteres): {instance.system_prompt[:500]}")

        running_tasks_file = config.workspace_root / "running_tasks.json"
        if os.path.exists(running_tasks_file):
            logger.info(f"Found existing running_tasks.json at {running_tasks_file}. Attempting to load and check tasks.")
            updated_tasks_after_check = []
            tasks_loaded = False
            persisted_tasks = [] # Definir persisted_tasks com um valor padrão
            try:
                with open(running_tasks_file, 'r') as f:
                    persisted_tasks = json.load(f)
                tasks_loaded = True

                if not persisted_tasks:
                    logger.info("running_tasks.json was empty.")

                status_checker_tool = instance.available_tools.get_tool(CheckProcessStatusTool().name)

                if status_checker_tool:
                    for task_info in persisted_tasks:
                        pid = task_info.get('pid')
                        if pid:
                            logger.info(f"Checking status for persisted task PID: {pid}, Command: {task_info.get('command')}")
                            status_result = await status_checker_tool.execute(pid=pid)
                            current_status = status_result.get('status', 'unknown')
                            task_info['status'] = current_status

                            if current_status not in ['not_found', 'finished', 'error']:
                                updated_tasks_after_check.append(task_info)

                            load_message = (
                                f"Tarefa em background recuperada da sessão anterior: "
                                f"PID: {pid}, Descrição: {task_info.get('task_description', task_info.get('command', 'N/A'))}, "
                                f"Status atual: {current_status}."
                            )
                            if current_status == 'finished':
                                load_message += f" Código de saída: {status_result.get('return_code')}."

                            instance.memory.add_message(Message.system_message(load_message))
                            logger.info(load_message)
                        else:
                            # Keep tasks without PID if they somehow exist, though they shouldn't normally.
                            # Or decide to filter them out if they are considered invalid.
                            # For now, keeping them.
                            updated_tasks_after_check.append(task_info)
                else:
                    logger.error("CheckProcessStatusTool não encontrado na instância do agente durante o carregamento de tarefas.")
                    instance.memory.add_message(Message.system_message(
                        "AVISO: Não foi possível verificar o status de tarefas em background da sessão anterior (ferramenta de status não encontrada)."
                    ))
                    # If checker is not found, keep all tasks as they were, as we can't verify them.
                    updated_tasks_after_check.extend(persisted_tasks)

            except json.JSONDecodeError as e_json:
                logger.error(f"Error decoding running_tasks.json: {e_json}")
                instance.memory.add_message(Message.system_message(f"AVISO: Erro ao ler o arquivo de tarefas em background ({running_tasks_file}): {e_json}"))
            except Exception as e_load:
                logger.error(f"Unexpected error loading or checking persisted tasks: {e_load}", exc_info=True)
                instance.memory.add_message(Message.system_message(f"AVISO: Erro inesperado ao carregar tarefas em background: {e_load}"))

            if tasks_loaded:
                final_tasks_for_persistence = updated_tasks_after_check
                try:
                    with open(running_tasks_file, 'w') as f:
                        json.dump(final_tasks_for_persistence, f, indent=4)
                    logger.info(f"Persisted tasks file {running_tasks_file} updated after status check. Kept {len(final_tasks_for_persistence)} tasks.")
                except Exception as e_write_back:
                    logger.error(f"Error writing back to running_tasks.json after status check: {e_write_back}")

        await instance.initialize_mcp_servers()
        instance._initialized = True
        return instance

    async def initialize_mcp_servers(self) -> None:
        for server_id, server_config in config.mcp_config.servers.items():
            try:
                if server_config.type == "sse":
                    if server_config.url:
                        await self.connect_mcp_server(server_config.url, server_id)
                        logger.info(f"Conectado ao servidor MCP {server_id} em {server_config.url}")
                elif server_config.type == "stdio":
                    if server_config.command:
                        await self.connect_mcp_server(
                            server_config.command, server_id, use_stdio=True, stdio_args=server_config.args,
                        )
                        logger.info(f"Conectado ao servidor MCP {server_id} usando o comando {server_config.command}")
            except Exception as e:
                logger.error(f"Falha ao conectar ao servidor MCP {server_id}: {e}")

    async def connect_mcp_server(
        self, server_url: str, server_id: str = "", use_stdio: bool = False, stdio_args: List[str] = None,
    ) -> None:
        if use_stdio:
            await self._mcp_clients.connect_stdio(server_url, stdio_args or [], server_id)
            self.connected_servers[server_id or server_url] = server_url
        else:
            await self._mcp_clients.connect_sse(server_url, server_id)
            self.connected_servers[server_id or server_url] = server_url
        new_tools = [tool for tool in self._mcp_clients.tools if tool.server_id == server_id]
        self.available_tools.add_tools(*new_tools)

    async def disconnect_mcp_server(self, server_id: str = "") -> None:
        await self._mcp_clients.disconnect(server_id)
        if server_id: self.connected_servers.pop(server_id, None)
        else: self.connected_servers.clear()
        base_tools = [tool for tool in self.available_tools.tools if not isinstance(tool, MCPClientTool)]
        self.available_tools = ToolCollection(*base_tools)
        self.available_tools.add_tools(*self._mcp_clients.tools)

    async def cleanup(self):
        logger.info("Manus.cleanup: Iniciando limpeza específica do agente Manus...")
        if self.browser_context_helper:
            await self.browser_context_helper.cleanup_browser()
        if self._initialized:
            await self.disconnect_mcp_server()
            self._initialized = False
        if hasattr(self, 'available_tools') and self.available_tools:
            for tool_name, tool_instance in self.available_tools.tool_map.items():
                if hasattr(tool_instance, "cleanup") and callable(getattr(tool_instance, "cleanup")):
                    try: await tool_instance.cleanup()
                    except Exception as e: logger.error(f"Erro durante a limpeza da ferramenta {tool_name}: {e}")
        try:
            await SANDBOX_CLIENT.cleanup()
        except Exception as e: logger.error(f"Erro durante SANDBOX_CLIENT.cleanup em Manus.cleanup: {e}")
        logger.info("Limpeza do agente Manus concluída.")

    async def _internal_tool_feedback_check(self, tool_call: Optional[ToolCall] = None) -> bool: return False
    async def _is_checklist_complete(self) -> bool:
        try:
            manager = ChecklistManager()
            await manager._load_checklist()
            tasks = manager.get_tasks() # Obter tarefas uma vez

            if not tasks:
                logger.info("Manus._is_checklist_complete: Checklist não está completo porque nenhuma tarefa foi encontrada (o arquivo pode estar vazio ou ausente).")
                return False

            # INÍCIO DA NOVA LÓGICA
            # Verifica se a *única* tarefa é uma tarefa de decomposição genérica e está marcada como concluída.
            # Esta é uma heurística.
            decomposition_task_description_variations = [
                "decompor a solicitação do usuário e popular o checklist com as subtarefas",
                "decompor a tarefa do usuário em subtarefas claras",
                "decompor o pedido do usuário e preencher o checklist",
                "popular o checklist com as subtarefas da solicitação do usuário",
                "criar checklist inicial a partir da solicitação do usuário"
                # Adicionar outras variações comuns se observadas durante o teste/operação
            ]

            if len(tasks) == 1:
                single_task = tasks[0]
                # Normalizar para comparação mais segura: descrição em minúsculas e sem espaços em branco
                normalized_single_task_desc = single_task.get('description', '').strip().lower()
                # Normalizar status: em minúsculas e sem espaços em branco
                single_task_status = single_task.get('status', '').strip().lower()

                is_generic_decomposition_task = any(
                    variation.lower() in normalized_single_task_desc for variation in decomposition_task_description_variations
                )

                if is_generic_decomposition_task and single_task_status == 'concluído':
                    logger.warning("Manus._is_checklist_complete: Checklist contém apenas a tarefa inicial semelhante à decomposição "
                                   "marcada como 'Concluído'. Isso provavelmente é prematuro. "
                                   "Considerando o checklist NÃO completo para forçar o preenchimento das subtarefas reais.")
                    # Opcional: Adicionar uma mensagem de sistema para guiar o LLM para o próximo passo.
                    # Isso requer que self.memory seja acessível e uma classe Message.
                    # from app.schema import Message, Role # Garantir importação se usado
                    # self.memory.add_message(Message.system_message(
                    #    "Lembrete: A tarefa de decomposição só é verdadeiramente concluída após as subtarefas resultantes "
                    #    "serem adicionadas ao checklist e o trabalho nelas ter começado. Por favor, adicione as subtarefas agora."
                    # ))
                    return False
            # FIM DA NOVA LÓGICA

            # Prosseguir com a lógica original se a condição acima não for atendida
            # O método manager.are_all_tasks_complete() verifica se todas as tarefas carregadas são 'Concluído'.
            # Ele retornará False corretamente se houver tarefas, mas nem todas forem 'Concluído'.
            all_complete_according_to_manager = manager.are_all_tasks_complete()

            if not all_complete_according_to_manager:
                 # Log já feito por are_all_tasks_complete se retornar falso devido a tarefas incompletas
                 logger.info(f"Manus._is_checklist_complete: Checklist não está completo com base em ChecklistManager.are_all_tasks_complete() retornando False.")
                 return False

            # Se manager.are_all_tasks_complete() retornou True, significa que todas as tarefas encontradas estão completas.
            # E se passamos na nova verificação heurística (ou seja, não é uma única tarefa de decomposição concluída prematuramente),
            # então o checklist está genuinamente completo.
            logger.info(f"Manus._is_checklist_complete: Status de conclusão do checklist: True (todas as tarefas concluídas e não uma decomposição prematura).")
            return True

        except Exception as e:
            # Registrar o erro e retornar False, pois a conclusão não pode ser confirmada.
            logger.error(f"Erro ao verificar a conclusão do checklist em Manus._is_checklist_complete: {e}")
            return False

    async def should_request_feedback(self) -> bool:
        # Determines if the agent should pause and request feedback from the user.
        # This happens on failure, task completion, or after a set number of steps (unless in autonomous_mode).
        if self._trigger_failure_check_in:
            self._trigger_failure_check_in = False
            await self.periodic_user_check_in(is_failure_scenario=True)
            return True
        if self._just_resumed_from_feedback:
            self._just_resumed_from_feedback = False
            return False
        if await self._is_checklist_complete():
            last_assistant_msg = next((m for m in reversed(self.memory.messages) if m.role == Role.ASSISTANT and m.tool_calls), None)
            if last_assistant_msg and any(tc.function.name == Terminate().name for tc in last_assistant_msg.tool_calls):
                return False
            await self.periodic_user_check_in(is_final_check=True, is_failure_scenario=False)
            return True
        if not self._autonomous_mode and self.current_step > 0 and self.max_steps > 0 and self.current_step % self.max_steps == 0: # Skip periodic check-in if in autonomous mode
            continue_execution = await self.periodic_user_check_in(is_failure_scenario=False)
            return continue_execution
        return False

    def _sanitize_text_for_file(self, text_content: str) -> str:
        if not isinstance(text_content, str): return text_content
        return text_content.replace('\u0000', '')

    def _extract_python_code(self, text: str) -> str:
        if "```python" in text: return text.split("```python")[1].split("```")[0].strip()
        if "```" in text: return text.split("```")[1].split("```")[0].strip()
        return text.strip()

    async def _execute_self_coding_cycle(self, task_prompt_for_llm: str, max_attempts: int = 3) -> Dict[str, Any]:
        logger.info(f"Iniciando ciclo de auto-codificação para tarefa: {task_prompt_for_llm}")
        script_content: Optional[str] = None
        host_script_path: str = ""
        final_result: Dict[str, Any] = {"success": False, "message": "Ciclo de auto-codificação não concluído."}

        local_op = LocalFileOperator()

        for attempt in range(max_attempts):
            logger.info(f"Tentativa de auto-codificação {attempt + 1}/{max_attempts}")

            code_fixed_by_formatter = False
            targeted_edits_applied_this_attempt = False
            # analysis_failed_or_no_edits_suggested = False # Esta flag parece não utilizada com a nova lógica

            if attempt == 0:
                logger.info(f"Tentativa {attempt + 1}: Gerando script inicial para tarefa: {task_prompt_for_llm}")
                # Placeholder para chamada LLM para gerar script inicial
                generated_script_content = f"# Script Inicial - Tentativa {attempt + 1}\n# Tarefa: {task_prompt_for_llm}\nprint(\"Tentando tarefa: {task_prompt_for_llm}\")\n# Exemplo: Introduzir intencionalmente um erro de sintaxe para teste\n# print(\"Erro de sintaxe aqui\"\nwith open(\"output.txt\", \"w\") as f:\n    f.write(\"Saída da tentativa de script {attempt + 1}\")\nprint(\"Script concluiu tentativa {attempt + 1}.\")"
                script_content = self._sanitize_text_for_file(generated_script_content)
                if not script_content:
                    logger.error("LLM (simulado) falhou ao gerar conteúdo do script inicial.")
                    final_result = {"success": False, "message": "LLM (simulado) falhou ao gerar script inicial."}
                    continue
                script_filename = f"temp_manus_script_{uuid.uuid4().hex[:8]}.py"
                host_script_path = str(config.workspace_root / script_filename)
                try:
                    await local_op.write_file(host_script_path, script_content)
                    logger.info(f"Script inicial escrito no host: {host_script_path}")
                except Exception as e:
                    logger.error(f"Falha ao escrever script inicial no host: {e}")
                    final_result = {"success": False, "message": f"Falha ao escrever script inicial no host: {e}"}
                    continue
            elif not host_script_path or not os.path.exists(host_script_path):
                logger.error(f"host_script_path ('{host_script_path}') não definido ou arquivo não existe na tentativa {attempt + 1}. Erro crítico.")
                final_result = {"success": False, "message": "Erro interno: Caminho do script perdido ou arquivo ausente entre tentativas."}
                break

            sandbox_script_name_in_container = os.path.basename(host_script_path)
            sandbox_target_path_for_executor = f"/workspace/{sandbox_script_name_in_container}"

            str_editor_tool = self.available_tools.get_tool(StrReplaceEditor().name)
            if not str_editor_tool:
                logger.critical("Ferramenta StrReplaceEditor não está disponível para cópia para o sandbox.")
                final_result = {"success": False, "message": "Erro crítico: Ferramenta StrReplaceEditor ausente."}
                break

            copy_to_sandbox_succeeded = False
            try:
                await str_editor_tool.execute(command="copy_to_sandbox", path=host_script_path, container_filename=sandbox_script_name_in_container)
                logger.info(f"Cópia do script para o sandbox bem-sucedida: {host_script_path} -> {sandbox_target_path_for_executor}")
                copy_to_sandbox_succeeded = True
            except Exception as e_copy:
                logger.error(f"Falha ao copiar script para o sandbox: {e_copy}")
                final_result = {"success": False, "message": f"Falha ao copiar script para o sandbox: {e_copy}", "status_code": "SANDBOX_COPY_FAILED"}
                continue

            execution_result = {}
            if copy_to_sandbox_succeeded:
                executor_tool = self.available_tools.get_tool(SandboxPythonExecutor().name)
                if not executor_tool:
                    logger.critical("Ferramenta SandboxPythonExecutor não encontrada.")
                    final_result = {"success": False, "message": "Ferramenta SandboxPythonExecutor não encontrada."}
                    break
                
                execution_result = await executor_tool.execute(file_path=sandbox_target_path_for_executor, timeout=30)
                logger.info(f"Execução no sandbox: stdout='{execution_result.get('stdout')}', stderr='{execution_result.get('stderr')}', exit_code={execution_result.get('exit_code')}")
                final_result["last_execution_result"] = execution_result
            else:
                logger.error("Pulando execução pois a cópia para o sandbox falhou.")
                continue

            exit_code = execution_result.get("exit_code", -1)
            stderr = execution_result.get("stderr", "")
            stdout = execution_result.get("stdout", "")
            
            if exit_code == 0:
                logger.info(f"Script executado com sucesso na tentativa {attempt + 1}.")
                final_result = {"success": True, "message": "Script executado com sucesso.", "stdout": stdout, "stderr": stderr, "exit_code": exit_code}
                # Limpeza simplificada de sucesso por enquanto
                break
            else: # Execução do script falhou (exit_code != 0)
                logger.warning(f"Execução do script falhou na tentativa {attempt + 1}. Código de saída: {exit_code}, Stderr: {stderr}")
                final_result = {"success": False, "message": f"Execução falhou na tentativa {attempt+1}.", "stdout":stdout, "stderr":stderr, "exit_code":exit_code}

                if attempt >= max_attempts - 1:
                    logger.info("Última tentativa falhou. Nenhuma correção adicional será tentada.")
                    break

                # --- Funil de Depuração ---
                current_script_code_for_analysis = await local_op.read_file(host_script_path)

                if "SyntaxError:" in stderr or "IndentationError:" in stderr:
                    logger.info(f"[TENTATIVA_CORRECAO {attempt + 1}/{max_attempts}] Tentando corrigir erro de Sintaxe/Indentação usando formatador para script {host_script_path}.")
                    formatter_tool = self.available_tools.get_tool("format_python_code")
                    if formatter_tool:
                        format_result = await formatter_tool.execute(code=current_script_code_for_analysis)
                        if isinstance(format_result, str):
                            try:
                                ast.parse(format_result)
                                logger.info("Código formatado parseado com sucesso. Escrevendo de volta.")
                                await local_op.write_file(host_script_path, format_result)
                                code_fixed_by_formatter = True
                            except SyntaxError as e_ast:
                                logger.warning(f"Código formatado ainda tem erros de sintaxe: {e_ast}.")
                        else:
                            logger.warning(f"Formatador de código falhou: {format_result.get('error')}.")
                    else:
                        logger.warning("Ferramenta format_python_code não encontrada.")

                if code_fixed_by_formatter:
                    logger.info("Código corrigido pelo formatador. Tentando novamente.")
                    continue

                # LLM para Correções Complexas
                log_msg_llm_query = ""
                if "SyntaxError:" in stderr or "IndentationError:" in stderr: # Ainda um erro de sintaxe após tentativa do formatador
                    logger.info(f"[TENTATIVA_CORRECAO {attempt + 1}/{max_attempts}] Formatador não corrigiu erro de sintaxe para script {host_script_path}, ou erro não era relacionado à formatação. Consultando LLM.")
                else: # Erro de tempo de execução
                    logger.info(f"[TENTATIVA_CORRECAO {attempt + 1}/{max_attempts}] Script {host_script_path} falhou com erro de tempo de execução. Consultando LLM.")
                # O logger.info(log_msg_llm_query) foi removido pois as mensagens específicas acima o cobrem.

                current_script_code_for_analysis = await local_op.read_file(host_script_path) # Relê caso o formatador tenha feito alterações
                analysis_prompt_text = self._build_targeted_analysis_prompt(
                    script_content=current_script_code_for_analysis, stdout=stdout, stderr=stderr, original_task=task_prompt_for_llm
                )
                llm_analysis_response_str = await self.llm.ask(messages=[Message.user_message(analysis_prompt_text)], stream=False)
                extracted_json_str = self._extract_json_from_response(llm_analysis_response_str)

                if extracted_json_str:
                    try:
                        parsed_llm_suggestion = json.loads(extracted_json_str)
                        tool_to_use_name = parsed_llm_suggestion.get("tool_to_use")
                        tool_params_from_llm = parsed_llm_suggestion.get("tool_params")

                        if tool_to_use_name and isinstance(tool_params_from_llm, dict):
                            logger.info(f"[TENTATIVA_CORRECAO {attempt + 1}/{max_attempts}] LLM sugeriu ferramenta '{tool_to_use_name}' para script {host_script_path}. Tentando execução com params: {tool_params_from_llm}")
                            chosen_tool = self.available_tools.get_tool(tool_to_use_name)
                            if chosen_tool:
                                if tool_to_use_name == "format_python_code":
                                    tool_params_from_llm["code"] = current_script_code_for_analysis # Garante que 'code' é passado
                                    tool_params_from_llm.pop("path", None)
                                else:
                                    tool_params_from_llm["path"] = host_script_path

                                tool_exec_result = await chosen_tool.execute(**tool_params_from_llm)
                                if isinstance(tool_exec_result, dict) and tool_exec_result.get("error"):
                                    logger.error(f"Ferramenta sugerida pelo LLM '{tool_to_use_name}' falhou: {tool_exec_result.get('error')}")
                                else: # Sucesso assumido
                                    logger.info(f"Ferramenta sugerida pelo LLM '{tool_to_use_name}' executada com sucesso.")
                                    targeted_edits_applied_this_attempt = True
                            else:
                                logger.warning(f"Ferramenta sugerida pelo LLM '{tool_to_use_name}' não encontrada.")
                        elif tool_to_use_name is None: # LLM explicitamente disse nenhuma ferramenta
                             logger.info(f"LLM explicitamente não sugeriu nenhuma ferramenta. Comentário: {parsed_llm_suggestion.get('comment')}")
                        else: # Estrutura JSON inválida do LLM
                            logger.warning(f"Sugestão JSON do LLM inválida. Sugestão: {parsed_llm_suggestion}")
                    except json.JSONDecodeError as json_e:
                        logger.error(f"Falha ao parsear JSON da sugestão de ferramenta do LLM: {json_e}. Raw: {llm_analysis_response_str}")
                    except Exception as tool_apply_e:
                        logger.error(f"Erro ao aplicar ferramenta sugerida pelo LLM: {tool_apply_e}")
                else:
                    logger.warning("Não foi possível extrair JSON da resposta de sugestão de ferramenta do LLM.")

                if targeted_edits_applied_this_attempt:
                    logger.info("Edições sugeridas pelo LLM aplicadas. Tentando novamente execução do script.")
                    continue
                else:
                    logger.info("Correção baseada em LLM falhou ou nenhuma edição válida aplicada nesta tentativa.")
            
            # Limpa script do sandbox para esta tentativa falha (se copiado)
            if copy_to_sandbox_succeeded and SANDBOX_CLIENT.sandbox and SANDBOX_CLIENT.sandbox.container:
                try: await SANDBOX_CLIENT.run_command(f"rm -f {sandbox_target_path_for_executor}")
                except Exception as e_rm_sandbox: logger.error(f"Erro ao remover script do sandbox pós-tentativa: {e_rm_sandbox}")

        # Limpeza final do script do host se ainda existir (ex: todas as tentativas falharam)
        if host_script_path and os.path.exists(host_script_path):
            try: await local_op.delete_file(host_script_path)
            except Exception as e_final_clean: logger.error(f"Erro na exclusão final do script do host {host_script_path}: {e_final_clean}")
        
        if not final_result["success"]:
             logger.error(f"Ciclo de auto-codificação falhou totalmente após {max_attempts} tentativas. Resultado final: {final_result}")
        
        self._monitoring_background_task = False
        self._background_task_log_file = None
        self._background_task_expected_artifact = None
        self._background_task_artifact_path = None
        self._background_task_description = None
        self._background_task_last_log_size = 0
        self._background_task_no_change_count = 0
        return final_result

    def _extract_json_from_response(self, llm_response: str) -> Optional[str]:
        """Extrai uma string JSON da resposta do LLM, lidando com blocos de código markdown."""
        logger.debug(f"Tentando extrair JSON da resposta do LLM: '{llm_response[:500]}...'")
        match = re.search(r"```json\s*([\s\S]+?)\s*```", llm_response)
        if match:
            json_str = match.group(1).strip()
            logger.debug(f"String JSON extraída usando regex: '{json_str[:500]}...'")
            return json_str
        
        response_stripped = llm_response.strip()
        if response_stripped.startswith("{") and response_stripped.endswith("}"):
            logger.debug("Resposta parece um objeto JSON direto. Usando como está.")
            return response_stripped
        
        logger.warning("Nenhum bloco de código JSON encontrado, e resposta não é um objeto JSON direto.")
        return None

    def _build_targeted_analysis_prompt(self, script_content: str, stdout: str, stderr: str, original_task: str) -> str:
        """Constrói o prompt para o LLM analisar e sugerir uma correção baseada em ferramenta."""
        ANALYSIS_PROMPT_TEMPLATE = """Você é um "Python Code Analyzer and Corrector".
Sua tarefa é analisar um script Python que falhou, juntamente com sua saída padrão (stdout) e erro padrão (stderr).
Você DEVE retornar um objeto JSON especificando uma única ferramenta para aplicar a correção e os parâmetros para essa ferramenta.

**Ferramentas Disponíveis para Correção:**
1.  **`replace_code_block`**:
    *   Descrição: Substitui um bloco de código entre `start_line` e `end_line` (inclusive, 1-indexado) com `new_content`.
    *   Parâmetros: `path` (string, caminho do arquivo - **NÃO INCLUA ESTE PARÂMETRO, será adicionado automaticamente**), `start_line` (integer), `end_line` (integer), `new_content` (string).
    *   Uso: Ideal para substituir funções inteiras, blocos lógicos, ou seções maiores de código.
2.  **`apply_diff_patch`**:
    *   Descrição: Aplica um patch no formato unified diff ao arquivo.
    *   Parâmetros: `path` (string, caminho do arquivo - **NÃO INCLUA ESTE PARÂMETRO**), `patch_content` (string, conteúdo do diff).
    *   Uso: Bom para múltiplas pequenas alterações, alterações não contíguas, ou quando a lógica do diff é mais fácil de expressar. O diff deve ser gerado em relação ao script original fornecido.
3.  **`ast_refactor`**:
    *   Descrição: Realiza refatorações baseadas em AST. Operação inicial: `replace_function_body`.
    *   Parâmetros para `replace_function_body`: `path` (string - **NÃO INCLUA ESTE PARÂMETRO**), `operation` (string, fixo: "replace_function_body"), `target_node_name` (string, nome da função), `new_code_snippet` (string, novo corpo da função, sem o `def ...`).
    *   Uso: Mais seguro para refatorações estruturais, como substituir o corpo de uma função sem afetar sua assinatura ou o restante do arquivo.
4.  **`format_python_code`**:
    *   Descrição: Formata o código Python usando Ruff/Black. Pode corrigir erros de sintaxe/indentação simples.
    *   Parâmetros: `code` (string, o código completo a ser formatado - **IMPORTANTE: para esta ferramenta, em vez de "path", forneça o conteúdo do script no parâmetro "code" dentro de "tool_params"**).
    *   Uso: Tente esta ferramenta PRIMEIRO para erros de SyntaxError ou IndentationError. Se o LLM for solicitado após uma falha do formatador, não sugira `format_python_code` novamente.

**Formato JSON Obrigatório para a Resposta:**
A resposta DEVE ser uma string JSON que possa ser parseada, contendo um objeto com as seguintes chaves:
- "tool_to_use": string, o nome da ferramenta escolhida (e.g., "replace_code_block", "apply_diff_patch", "ast_refactor", "format_python_code").
- "tool_params": object, um dicionário contendo os parâmetros específicos para a ferramenta escolhida (NÃO inclua "path" aqui, exceto para "format_python_code" onde "code" é usado em vez de "path").
- "comment": string, uma breve explicação do erro e da correção que você está aplicando.

**Exemplos de Resposta JSON:**

Para `replace_code_block`:
```json
{
  "tool_to_use": "replace_code_block",
  "tool_params": {
    "start_line": 10,
    "end_line": 15,
    "new_content": "def minha_funcao_corrigida():\\n    return 'corrigido'"
  },
  "comment": "A função 'minha_funcao' original tinha um erro de lógica. Substituindo-a completamente."
}
```

Para `apply_diff_patch`:
```json
{
  "tool_to_use": "apply_diff_patch",
  "tool_params": {
    "patch_content": "--- a/script_original.py\\n+++ b/script_corrigido.py\\n@@ -1,3 +1,3 @@\\n- linha_com_erro\\n+ linha_corrigida\\n  outra_linha\\n"
  },
  "comment": "Corrigido um typo na linha 1 e ajustada uma variável na linha 5 (exemplo de diff)."
}
```

Para `ast_refactor` (operação `replace_function_body`):
```json
{
  "tool_to_use": "ast_refactor",
  "tool_params": {
    "operation": "replace_function_body",
    "target_node_name": "minha_funcao_com_erro",
    "new_code_snippet": "  # Novo corpo da função\\n  resultado = calcula_algo()\\n  return resultado"
  },
  "comment": "O corpo da função 'minha_funcao_com_erro' foi reescrito para corrigir um bug de cálculo."
}
```

Para `format_python_code` (se for um erro de sintaxe e o formatador automático ainda não foi tentado):
```json
{
  "tool_to_use": "format_python_code",
  "tool_params": {
    "code": "# Conteúdo completo do script aqui...\nprint('hello') # Exemplo"
  },
  "comment": "Tentando corrigir possível erro de sintaxe/indentação simples com o formatador."
}
```

**Importante:**
- Escolha APENAS UMA ferramenta.
- Forneça as correções no formato JSON EXATO especificado acima.
- Se o script estiver fundamentalmente errado e precisar de uma reescrita completa que não se encaixe bem em uma única chamada de ferramenta, ou se nenhuma correção for óbvia, você PODE retornar um JSON com `tool_to_use": null` e um comentário explicando. Ex: `{"tool_to_use": null, "tool_params": {}, "comment": "O script está muito quebrado, sugiro reescrevê-lo com base na tarefa original."}`.
- Analise o `stderr` cuidadosamente para identificar a causa raiz do erro.
- O objetivo é fazer a correção mais apropriada usando a ferramenta mais adequada.
- **NÃO inclua o parâmetro "path" em "tool_params" para `replace_code_block`, `apply_diff_patch`, `ast_refactor`. Ele será adicionado automaticamente. Para `format_python_code`, use o parâmetro "code" em `tool_params` para passar o conteúdo do script.**

**Script Original com Erro:**
```python
{script_content}
```

**Saída Padrão (stdout) da Execução Falha:**
```
{stdout}
```

**Erro Padrão (stderr) da Execução Falha:**
```
{stderr}
```

**Tarefa Original que o Script Tentava Realizar:**
{original_task}

Agora, forneça sua análise e a sugestão de ferramenta e parâmetros no formato JSON especificado.
"""
        return ANALYSIS_PROMPT_TEMPLATE.format(
            script_content=script_content,
            stdout=stdout,
            stderr=stderr,
            original_task=original_task
        )

    async def think(self) -> bool:
        self.planned_tool_calls = []
        if not self._initialized:
            await self.initialize_mcp_servers()
            self._initialized = True

        # Check for autonomous mode trigger in initial user prompt
        if self.current_step == 0 and not self._autonomous_mode: # Só verifica no primeiro passo prático
            first_user_message = next((msg for msg in self.memory.messages if msg.role == Role.USER), None)
            if first_user_message:
                prompt_content = first_user_message.content.strip().lower()
                if prompt_content.startswith("execute em modo autônomo:") or prompt_content.startswith("modo autônomo:"):
                    self._autonomous_mode = True
                    logger.info("Modo autônomo ativado por prompt do usuário.")
                    # Opcional: Remover a frase gatilho do prompt para não confundir o LLM depois
                    # clean_prompt = prompt_content.replace("execute em modo autônomo:", "").replace("modo autônomo:", "").strip()
                    # first_user_message.content = clean_prompt
                    # (Cuidado ao modificar self.memory.messages diretamente, pode ser melhor adicionar uma msg do sistema)
                    self.memory.add_message(Message.assistant_message("Modo autônomo ativado. Não pedirei permissão para continuar a cada ciclo de etapas."))

        # Sandbox Execution Fallback Logic: Detects sandbox creation failure and asks user for direct execution.
        last_message = self.memory.messages[-1] if self.memory.messages else None
        # Etapa A: Detectar falha do SandboxPythonExecutor e perguntar ao usuário
        if (
            last_message
            and last_message.role == Role.TOOL
            and hasattr(last_message, 'name') and last_message.name == SandboxPythonExecutor().name
            and hasattr(last_message, 'tool_call_id') # Garantir que tool_call_id existe
        ):
            tool_call_id_from_message = last_message.tool_call_id
            if tool_call_id_from_message != self._fallback_attempted_for_tool_call_id:
                try:
                    # O conteúdo da mensagem da ferramenta DEVE ser um dicionário Python aqui,
                    # pois é o resultado direto da execução da ferramenta, não uma string JSON do LLM.
                    tool_result_content = json.loads(last_message.content) # Se content é string JSON
                    # Se last_message.content já é um dict, json.loads não é necessário.
                    # O log original indicava "Failed to parse tool result content for fallback logic",
                    # então é provável que `last_message.content` seja uma string JSON.

                    if isinstance(tool_result_content, dict) and tool_result_content.get("exit_code") == -2:
                        logger.warning(
                            f"SandboxPythonExecutor falhou com exit_code -2 (erro de criação do sandbox) para tool_call_id {tool_call_id_from_message}. "
                            "Iniciando lógica de fallback."
                        )

                        # Encontrar a ToolCall original que invocou o SandboxPythonExecutor
                        original_tool_call_for_sandbox = None
                        for msg_idx in range(len(self.memory.messages) - 2, -1, -1):
                            prev_msg = self.memory.messages[msg_idx]
                            if prev_msg.role == Role.ASSISTANT and prev_msg.tool_calls:
                                for tc in prev_msg.tool_calls:
                                    if tc.id == tool_call_id_from_message:
                                        original_tool_call_for_sandbox = tc
                                        break
                                if original_tool_call_for_sandbox:
                                    break

                        if original_tool_call_for_sandbox:
                            self._pending_fallback_tool_call = original_tool_call_for_sandbox

                            ask_human_question = (
                                "A execução segura no sandbox falhou devido a um problema de ambiente "
                                "(Docker não disponível ou imagem incorreta). Deseja tentar executar o script "
                                "diretamente na máquina do agente? ATENÇÃO: Isso pode ser um risco de segurança "
                                "se o script for desconhecido ou malicioso. Responda 'sim' para executar "
                                "diretamente ou 'não' para cancelar."
                            )
                            self.memory.add_message(Message.assistant_message(
                                "Alerta: Problema ao executar script em ambiente seguro (sandbox)."
                            )) # Mensagem curta antes de AskHuman

                            ask_human_tool_call_id = str(uuid.uuid4())
                            self._last_ask_human_for_fallback_id = ask_human_tool_call_id
                            self.tool_calls = [
                                ToolCall(
                                    id=ask_human_tool_call_id,
                                    function=FunctionCall(
                                        name=AskHuman().name,
                                        arguments=json.dumps({"inquire": ask_human_question})
                                    )
                                )
                            ]
                            logger.info(f"Solicitando permissão do usuário para fallback da tool_call {tool_call_id_from_message} para PythonExecute.")
                            return True # Retorna para executar AskHuman
                        else:
                            logger.error(f"Não foi possível encontrar a ToolCall original do assistente para o tool_call_id {tool_call_id_from_message} que falhou no sandbox.")

                except json.JSONDecodeError as e:
                    logger.error(f"Falha ao parsear o conteúdo do resultado da ferramenta para lógica de fallback (Sandbox): {last_message.content}. Erro: {e}")
                except Exception as e_fallback_init:
                    logger.error(f"Erro inesperado durante a inicialização do fallback do sandbox: {e_fallback_init}", exc_info=True)

        # Etapa B: Processar resposta do usuário para fallback
        if (
            last_message
            and last_message.role == Role.USER
            and self._pending_fallback_tool_call # Havia uma pergunta pendente
            # Verifica se a mensagem do usuário é uma resposta à pergunta de fallback
            # Isso pode ser melhorado se AskHuman ToolCall/ToolMessage tiverem IDs que possam ser rastreados.
            # Por enquanto, confiamos que a última mensagem do usuário após _pending_fallback_tool_call ser setado é a resposta.
            # Adicionamos _last_ask_human_for_fallback_id para uma verificação mais robusta se a mensagem anterior foi o AskHuman
        ):
            # Verificar se a mensagem ANTERIOR foi o AskHuman que fizemos
            if len(self.memory.messages) >= 2:
                potential_ask_human_tool_msg = self.memory.messages[-2]
                if not (potential_ask_human_tool_msg.role == Role.TOOL and \
                        hasattr(potential_ask_human_tool_msg, 'name') and potential_ask_human_tool_msg.name == AskHuman().name and \
                        hasattr(potential_ask_human_tool_msg, 'tool_call_id') and potential_ask_human_tool_msg.tool_call_id == self._last_ask_human_for_fallback_id):
                    # A última mensagem do usuário não é uma resposta direta à nossa pergunta de fallback específica.
                    # Resetar _pending_fallback_tool_call para evitar processamento incorreto se o usuário apenas digitou algo.
                    # self._pending_fallback_tool_call = None # Comentado por enquanto, pode ser muito agressivo.
                    # logger.info("A última mensagem do usuário não parece ser uma resposta direta à pergunta de fallback. Ignorando para fins de fallback.")
                    pass # Não faz nada aqui, deixa o fluxo normal do `think` continuar.

            user_response_text = last_message.content.strip().lower()
            original_failed_tool_call = self._pending_fallback_tool_call

            if user_response_text == "sim":
                logger.info(f"Usuário aprovou fallback para PythonExecute para a tool_call original ID: {original_failed_tool_call.id}")
                try:
                    original_args = json.loads(original_failed_tool_call.function.arguments)
                    fallback_args = {}

                    if "code" in original_args and original_args["code"]:
                        fallback_args["code"] = original_args["code"]
                    elif "file_path" in original_args and original_args["file_path"]:
                        # Não podemos fazer fallback direto para PythonExecute com file_path
                        self.memory.add_message(Message.assistant_message(
                            f"Entendido. No entanto, a tentativa original era executar um arquivo (`{original_args['file_path']}`) no sandbox. "
                            "A execução direta alternativa (`PythonExecute`) requer o conteúdo do código, não o caminho do arquivo. "
                            "Não posso realizar este fallback automaticamente. Por favor, forneça o conteúdo do script se desejar executá-lo diretamente, "
                            "ou considere outra ferramenta para ler o arquivo primeiro."
                        ))
                        self.tool_calls = [] # Limpa quaisquer chamadas de ferramentas planejadas
                        self._fallback_attempted_for_tool_call_id = original_failed_tool_call.id # Marcar como tentado/tratado
                        self._pending_fallback_tool_call = None
                        self._last_ask_human_for_fallback_id = None
                        return True # Volta para o LLM pensar
                    else: # Nem 'code' nem 'file_path'
                         logger.error(f"Não foi possível realizar fallback para PythonExecute: 'code' ou 'file_path' não encontrado nos args originais: {original_args}")
                         self.memory.add_message(Message.assistant_message("Erro interno: não foi possível encontrar o código ou caminho do arquivo para a execução de fallback."))
                         self.tool_calls = []
                         self._fallback_attempted_for_tool_call_id = original_failed_tool_call.id
                         self._pending_fallback_tool_call = None
                         self._last_ask_human_for_fallback_id = None
                         return True

                    # Se chegamos aqui, é porque fallback_args["code"] foi definido
                    fallback_timeout = original_args.get("timeout", 120) # Usar timeout do sandbox ou o novo default de PythonExecute
                    fallback_args["timeout"] = fallback_timeout

                    new_fallback_tool_call = ToolCall(
                        id=str(uuid.uuid4()), # Novo ID para a tentativa de fallback
                        function=FunctionCall(
                            name=PythonExecute().name,
                            arguments=json.dumps(fallback_args)
                        )
                    )
                    self.tool_calls = [new_fallback_tool_call]
                    self._fallback_attempted_for_tool_call_id = original_failed_tool_call.id

                    self.memory.add_message(Message.assistant_message(
                        f"Ok, tentando executar o código diretamente usando '{PythonExecute().name}'. "
                        "Lembre-se dos riscos de segurança."
                    ))
                    logger.info(f"ToolCall de fallback planejada para PythonExecute: {new_fallback_tool_call}")

                except json.JSONDecodeError as e:
                    logger.error(f"Falha ao parsear argumentos da tool_call original durante o fallback: {original_failed_tool_call.function.arguments}. Erro: {e}")
                    self.memory.add_message(Message.assistant_message("Erro interno ao preparar a execução de fallback. Não é possível continuar com esta tentativa."))
                    self.tool_calls = []
                except Exception as e_fallback_exec:
                    logger.error(f"Erro inesperado durante a execução do fallback para PythonExecute: {e_fallback_exec}", exc_info=True)
                    self.memory.add_message(Message.assistant_message(f"Erro inesperado ao tentar fallback: {e_fallback_exec}"))
                    self.tool_calls = []

                self._pending_fallback_tool_call = None
                self._last_ask_human_for_fallback_id = None
                return True # Executar a tool_call de fallback (PythonExecute)

            elif user_response_text == "não":
                logger.info(f"Usuário negou fallback para PythonExecute para a tool_call original ID: {original_failed_tool_call.id}")
                self.memory.add_message(Message.assistant_message(
                    "Entendido. A execução do script foi cancelada conforme sua solicitação."
                ))
                self.tool_calls = []
                self._fallback_attempted_for_tool_call_id = original_failed_tool_call.id # Marcar como tratado
                self._pending_fallback_tool_call = None
                self._last_ask_human_for_fallback_id = None
                return True # Deixar o LLM decidir o que fazer após o cancelamento
            else:
                logger.info(f"Resposta não reconhecida do usuário ('{user_response_text}') para a pergunta de fallback. Solicitando novamente ou tratando como 'não'.")
                self.memory.add_message(Message.assistant_message(
                    f"Resposta '{last_message.content}' não reconhecida. Assumindo 'não' para a execução direta. A execução do script foi cancelada."
                ))
                self.tool_calls = []
                self._fallback_attempted_for_tool_call_id = original_failed_tool_call.id
                self._pending_fallback_tool_call = None
                self._last_ask_human_for_fallback_id = None
                return True

        # --- Fim da Lógica de Fallback ---
        
        user_prompt_message = next((msg for msg in reversed(self.memory.messages) if msg.role == Role.USER), None)
        user_prompt_content = user_prompt_message.content if user_prompt_message else ""
        SELF_CODING_TRIGGER = "execute self coding cycle: "
        if user_prompt_content.startswith(SELF_CODING_TRIGGER):
            if self._monitoring_background_task:
                logger.info("Novo ciclo de auto-codificação iniciado, parando monitoramento de tarefa em background anterior.")
                self._monitoring_background_task = False
                self._background_task_log_file = None
                self._background_task_expected_artifact = None
                self._background_task_artifact_path = None
                self._background_task_description = None
                self._background_task_last_log_size = 0
                self._background_task_no_change_count = 0
            task_description = user_prompt_content[len(SELF_CODING_TRIGGER):].strip()
            if not task_description:
                self.memory.add_message(Message.assistant_message("Por favor, forneça uma descrição da tarefa para o ciclo de auto-codificação."))
                self.tool_calls = []
                return True
            logger.info(f"Acionando ciclo de auto-codificação para a tarefa: {task_description}")
            self.memory.add_message(Message.assistant_message(f"Iniciando ciclo de auto-codificação para: {task_description}. Vou relatar o resultado."))
            cycle_result = await self._execute_self_coding_cycle(task_description)
            if cycle_result.get("status_code") == "SANDBOX_CREATION_FAILED":
                self.memory.add_message(Message.assistant_message(
                    f"Falha ao executar o ciclo de auto-codificação para '{task_description}'.\n"
                    f"Motivo: Não foi possível criar o ambiente seguro (sandbox) para execução do código.\n"
                    f"Detalhes: {cycle_result.get('details', 'Erro desconhecido na criação do sandbox.')}\n"
                    f"Por favor, verifique se o Docker está em execução e se a imagem '{config.sandbox.image_name}' está disponível ou pode ser baixada."
                ))
            elif cycle_result.get("status_code") == "SANDBOX_COPY_FAILED":
                self.memory.add_message(Message.assistant_message(
                    f"Falha ao executar o ciclo de auto-codificação para '{task_description}'.\n"
                    f"Motivo: Não foi possível copiar o script para o ambiente seguro (sandbox).\n"
                    f"Detalhes: {cycle_result.get('message', 'Erro desconhecido na cópia para o sandbox.')}"
                ))
            elif cycle_result.get("success"):
                success_message = f"Ciclo de auto-codificação concluído com sucesso para '{task_description}'.\n\n"
                success_message += f"Saída (stdout) do script:\n{cycle_result.get('stdout', 'Sem saída stdout.')}\n"
                if cycle_result.get("workspace_listing"):
                    success_message += f"\nConteúdo atual do diretório de trabalho principal ({config.workspace_root}):\n{cycle_result.get('workspace_listing')}\n"
                success_message += f"\nQuaisquer arquivos mencionados como 'salvos' ou 'gerados' pelo script (e copiados de /tmp do sandbox, se aplicável) devem estar visíveis acima ou diretamente no diretório {config.workspace_root}."
                self.memory.add_message(Message.assistant_message(success_message))
            else:
                error_details = cycle_result.get('stderr', cycle_result.get('last_execution_result', {}).get('stderr', 'Sem saída stderr.'))
                self.memory.add_message(Message.assistant_message(
                    f"Ciclo de auto-codificação falhou para '{task_description}'.\n"
                    f"Motivo: {cycle_result.get('message', 'Erro desconhecido.')}\n"
                    f"Última saída de erro (stderr):\n{error_details}"
                ))
            self.tool_calls = []
            return True

        original_prompt = self.next_step_prompt
        recent_messages_for_browser = self.memory.messages[-3:] if self.memory.messages else []
        browser_in_use = any(
            tc.function.name == BrowserUseTool().name
            for msg in recent_messages_for_browser # Nome da variável corrigido
            if msg.tool_calls
            for tc in msg.tool_calls
        )
        if browser_in_use:
            if self.browser_context_helper:
                self.next_step_prompt = (
                    await self.browser_context_helper.format_next_step_prompt()
                )
            else:
                logger.warning("BrowserContextHelper não inicializado, não é possível formatar next_step_prompt para o navegador.")

        result = await super().think()
        self.next_step_prompt = original_prompt

        # Sobrescrever chamadas PythonExecute que executam scripts externos para usar SandboxPythonExecutor
        if self.tool_calls:
            new_tool_calls = []
            for tool_call in self.tool_calls:
                # Linha original onde o erro ocorre:
                if tool_call.function.name == "python_execute":
                    try:
                        args = json.loads(tool_call.function.arguments)
                        code_to_execute = args.get("code")
                        original_timeout = args.get("timeout")

                        if isinstance(code_to_execute, str) and code_to_execute:
                            script_path_match = None
                            # Regex para subprocess.run(['python3', 'script.py', ...])
                            # Permite variações como "python", "python3", "python3.x"
                            # Captura o caminho do script ('([^']+\.py)')
                            # Usando o padrão regex externalizado
                            # re_subprocess agora é importado diretamente
                            # Regex para os.system('python3 script.py ...')
                            # Nota: Este regex para os.system pode precisar de externalização semelhante se se tornar complexo ou causar problemas.
                            re_os_system = r"os\.system\s*\(\s*['\"](?:python|python3)(?:\.[\d]+)?\s+([^'\" ]+\.py)['\"].*?\)"

                            match_subprocess = re.search(re_subprocess, code_to_execute) # re_subprocess é agora o padrão compilado
                            if match_subprocess:
                                script_path_match = match_subprocess.group(1)
                            else:
                                match_os_system = re.search(re_os_system, code_to_execute)
                                if match_os_system:
                                    script_path_match = match_os_system.group(1)

                            if script_path_match:
                                resolved_script_path = ""
                                if os.path.isabs(script_path_match):
                                    resolved_script_path = os.path.normpath(script_path_match)
                                else:
                                    resolved_script_path = str(config.workspace_root / script_path_match)

                                # Verificação de segurança: Garante que o caminho resolvido está dentro do workspace
                                if os.path.abspath(resolved_script_path).startswith(str(config.workspace_root)):
                                    logger.info(f"Sobrescrevendo chamada PythonExecute para script '{script_path_match}' para SandboxPythonExecutor com caminho '{resolved_script_path}'.")
                                    new_arguments = {"file_path": resolved_script_path}
                                    if original_timeout is not None:
                                        new_arguments["timeout"] = original_timeout

                                    # Cria um novo objeto ToolCall para a sobrescrita
                                    overridden_tool_call = ToolCall(
                                        id=tool_call.id, # Mantém o mesmo ID
                                        function=Function(
                                            name=SandboxPythonExecutor.name,
                                            arguments=json.dumps(new_arguments)
                                        )
                                    )
                                    new_tool_calls.append(overridden_tool_call)
                                    continue # Passa para a próxima tool_call
                                else:
                                    logger.warning(f"Chamada PythonExecute para script '{script_path_match}' resolvida para '{resolved_script_path}', que está fora do workspace. Não sobrescrevendo.")
                            else:
                                logger.info(f"Chamada PythonExecute com código não correspondeu a padrões de execução de script. Código: {code_to_execute[:100]}...")
                        else:
                            logger.warning("Chamada PythonExecute não tinha argumento 'code' válido.")
                    except json.JSONDecodeError:
                        logger.warning(f"Falha ao parsear argumentos para PythonExecute: {tool_call.function.arguments}. Usando chamada de ferramenta original.")
                    except Exception as e:
                        logger.error(f"Erro durante lógica de sobrescrita de PythonExecute: {e}. Usando chamada de ferramenta original.")

                new_tool_calls.append(tool_call) # Adiciona tool_call original ou não-PythonExecute
            self.tool_calls = new_tool_calls

        if self.tool_calls and self.tool_calls[0].function.name == Bash().name: # Verifica a primeira chamada de ferramenta
            try:
                args = json.loads(self.tool_calls[0].function.arguments)
                command_str = args.get("command", "")
                log_file_pattern = re.escape(str(config.workspace_root)) + r"/[^\s]+\.log"
                match = re.match(r"^\s*(.+?)\s*>\s*(" + log_file_pattern + r")\s*2>&1\s*&\s*$", command_str)
                if match:
                    actual_command = match.group(1).strip()
                    log_file = match.group(2).strip()
                    self._monitoring_background_task = True
                    self._background_task_log_file = log_file
                    self._background_task_description = f"Execução do comando: {actual_command}"
                    self._background_task_last_log_size = 0
                    self._background_task_no_change_count = 0
                    actual_command_lower = actual_command.lower()
                    script_name_match = re.search(r"python\d*\s+([^\s]+\.py)", actual_command)
                    if script_name_match:
                        script_path_in_command = script_name_match.group(1)
                        base_script_name = os.path.basename(script_path_in_command).replace(".py", "")
                        if "csv" in self._background_task_description.lower() or "csv" in actual_command_lower:
                            self._background_task_expected_artifact = f"{base_script_name}.csv"
                        elif "report" in self._background_task_description.lower() or "report" in actual_command_lower:
                            self._background_task_expected_artifact = f"{base_script_name}_report.txt"
                        else:
                            self._background_task_expected_artifact = f"{base_script_name}_output.txt"
                    else:
                        command_parts = actual_command.split()
                        first_part = os.path.basename(command_parts[0]) if command_parts else "command"
                        self._background_task_expected_artifact = f"{first_part}_artifact.out"
                    self._background_task_artifact_path = str(config.workspace_root / self._background_task_expected_artifact)
                    logger.info(f"Artefato esperado definido como: {self._background_task_artifact_path} (Arquivo de log: {log_file})")
                    self.memory.add_message(Message.assistant_message(
                        f"Comando '{actual_command}' iniciado em background. "
                        f"Logs serão enviados para '{os.path.basename(log_file)}' (localizado em {config.workspace_root}). "
                        f"Procurando pelo artefato esperado '{self._background_task_expected_artifact}' em '{config.workspace_root}'. "
                        "Vou monitorar o progresso."
                    ))
            except json.JSONDecodeError:
                logger.error("Erro ao decodificar argumentos JSON para Bash ao tentar iniciar monitoramento.")
            except Exception as e_parse:
                logger.error(f"Erro ao processar comando bash para monitoramento: {e_parse}")

        if self.tool_calls:
            new_tool_calls = []
            terminate_failure_detected = False
            for tc in self.tool_calls:
                if tc.function.name == Terminate().name:
                    try:
                        args = json.loads(tc.function.arguments)
                        if args.get("status") == "failure":
                            logger.info(f"Interceptada ToolCall para Terminate com status 'failure'. Argumentos: {args}")
                            terminate_failure_detected = True
                        else:
                            new_tool_calls.append(tc)
                    except json.JSONDecodeError:
                        logger.warning(f"Erro ao decodificar argumentos JSON para Terminate ToolCall: {tc.function.arguments}. Mantendo a chamada.")
                        new_tool_calls.append(tc)
                    except Exception as e_json_parse:
                        logger.warning(f"Erro inesperado ao analisar argumentos de Terminate: {e_json_parse}. Mantendo a chamada.")
                        new_tool_calls.append(tc)
                else:
                    new_tool_calls.append(tc)

            if terminate_failure_detected:
                logger.info("Sinalizando para _trigger_failure_check_in devido à interceptação de terminate(failure).")
                self._trigger_failure_check_in = True
                self.tool_calls = new_tool_calls
                self.memory.add_message(Message.system_message(
                    "Nota interna: Uma tentativa de finalizar a tarefa devido a uma falha foi interceptada. "
                    "O usuário será consultado antes da finalização."
                ))
                if not self.tool_calls:
                     logger.info("Nenhuma outra ferramenta planejada além do terminate(failure) interceptado. Indo para o feedback de falha.")
                else:
                     logger.warning("Outras ferramentas foram planejadas junto com terminate(failure). Isso é inesperado. O feedback de falha ocorrerá após estas ferramentas.")

        if self._pending_script_after_dependency and self.tool_calls:
            last_tool_response = next((msg for msg in reversed(self.memory.messages) if msg.role == Role.TOOL and msg.tool_call_id == self.tool_calls[0].id), None)
            dependency_succeeded_and_file_generated = False
            expected_generated_file_name = None
            if self._original_tool_call_for_pending_script:
                try:
                    original_args = json.loads(self._original_tool_call_for_pending_script.function.arguments)
                    original_script_path = original_args.get("file_path")
                    if original_script_path:
                        original_script_analysis = await self._analyze_python_script(original_script_path)
                        if original_script_analysis.get("inputs"):
                            expected_generated_file_name = original_script_analysis["inputs"][0]
                except Exception as e_inner_analysis:
                    logger.error(f"Erro ao reanalisar script original para nome de arquivo esperado: {e_inner_analysis}")

            if last_tool_response and isinstance(last_tool_response.content, str) and \
               any(err_keyword in last_tool_response.content.lower() for err_keyword in ["error", "traceback", "failed", "exception"]):
                logger.warning(f"Script de dependência parece ter falhado. Resposta: {last_tool_response.content}")
                self.memory.add_message(Message.assistant_message(
                    f"O script que tentei executar como dependência ('{self.tool_calls[0].function.name}') parece ter falhado em gerar o arquivo necessário para '{os.path.basename(self._pending_script_after_dependency)}'. Detalhes do erro: {last_tool_response.content}. Não tentarei executar o script pendente."
                ))
            elif not expected_generated_file_name:
                logger.warning("Não foi possível determinar o nome do arquivo esperado da dependência. Assumindo falha na geração.")
                self.memory.add_message(Message.assistant_message(
                    f"Não consegui determinar qual arquivo o script de dependência deveria gerar para '{os.path.basename(self._pending_script_after_dependency)}'. Não tentarei executar o script pendente."
                ))
            else:
                try:
                    expected_file_path = str(config.workspace_root / expected_generated_file_name)
                    editor = self.available_tools.get_tool(StrReplaceEditor().name)
                    await editor.execute(command="view", path=expected_file_path)
                    logger.info(f"Arquivo esperado '{expected_generated_file_name}' gerado com sucesso pela dependência.")
                    dependency_succeeded_and_file_generated = True
                except ToolError:
                    logger.warning(f"Script de dependência executado, mas o arquivo esperado '{expected_generated_file_name}' NÃO foi encontrado.")
                    self.memory.add_message(Message.assistant_message(
                        f"O script de dependência foi executado, mas o arquivo esperado '{expected_generated_file_name}' para '{os.path.basename(self._pending_script_after_dependency)}' não foi encontrado. Não tentarei executar o script pendente."
                    ))
                except Exception as e_check:
                    logger.error(f"Erro ao verificar arquivo gerado pela dependência '{expected_generated_file_name}': {e_check}")
                    self.memory.add_message(Message.assistant_message(
                        f"Ocorreu um erro ao verificar se o arquivo esperado '{expected_generated_file_name}' foi gerado. Não tentarei executar o script pendente."
                    ))

            if dependency_succeeded_and_file_generated:
                logger.info(f"Script de dependência concluído e arquivo gerado. Tentando executar o script pendente: {self._pending_script_after_dependency}")
                self.memory.add_message(Message.assistant_message(
                    f"A execução do script de dependência e a geração do arquivo '{expected_generated_file_name}' parecem ter sido bem-sucedidas. Agora vou tentar executar o script original: {os.path.basename(self._pending_script_after_dependency)}."
                ))
                if self._original_tool_call_for_pending_script:
                    self.tool_calls = [self._original_tool_call_for_pending_script]
                else:
                    logger.error("Não foi possível encontrar a tool_call original para o script pendente.")
                    self.tool_calls = []
                self._pending_script_after_dependency = None
                self._original_tool_call_for_pending_script = None
            else:
                self._pending_script_after_dependency = None
                self._original_tool_call_for_pending_script = None
                self.tool_calls = []

        if self.tool_calls and not self._pending_script_after_dependency:
            tool_call_to_check = self.tool_calls[0]
            required_file = None
            script_to_run_if_dependency_succeeds = None

            if tool_call_to_check.function.name in [SandboxPythonExecutor().name, PythonExecute().name] or \
               (tool_call_to_check.function.name == Bash().name and "python" in tool_call_to_check.function.arguments):
                try:
                    args = json.loads(tool_call_to_check.function.arguments)
                    script_path_from_args = args.get("file_path")
                    if not script_path_from_args and tool_call_to_check.function.name == Bash().name:
                        command_str = args.get("command", "")
                        match = re.search(r"python\d*\s+([^\s]+\.py)", command_str)
                        if match: script_path_from_args = match.group(1)
                        if script_path_from_args and not os.path.isabs(script_path_from_args):
                            script_path_from_args = str(config.workspace_root / script_path_from_args)

                    script_to_run_if_dependency_succeeds = script_path_from_args
                    if script_to_run_if_dependency_succeeds:
                        logger.info(f"Analisando inputs para o script planejado: {script_to_run_if_dependency_succeeds}")
                        script_analysis = await self._analyze_python_script(script_path_from_args)
                        if script_analysis.get("inputs"):
                            for inp_file_name in script_analysis["inputs"]:
                                expected_input_path = str(config.workspace_root / inp_file_name)
                                try:
                                    editor = self.available_tools.get_tool(StrReplaceEditor().name)
                                    await editor.execute(command="view", path=expected_input_path)
                                    logger.info(f"Arquivo de input '{expected_input_path}' para '{script_to_run_if_dependency_succeeds}' encontrado.")
                                except ToolError:
                                    logger.info(f"Arquivo de input '{expected_input_path}' para '{script_to_run_if_dependency_succeeds}' NÃO encontrado. Iniciando análise de dependência.")
                                    required_file = inp_file_name
                                    break
                        else:
                            logger.info(f"Nenhum input declarado encontrado para {script_to_run_if_dependency_succeeds} na análise.")
                except Exception as e:
                    logger.error(f"Erro ao analisar argumentos da tool call para dependências: {e}")

            if required_file and script_to_run_if_dependency_succeeds:
                logger.info(f"Arquivo '{required_file}' necessário para '{script_to_run_if_dependency_succeeds}' está faltando. Analisando workspace...")
                workspace_analysis = await self._analyze_workspace()
                found_generating_script = None
                for gen_script_name, analysis_info in workspace_analysis.items():
                    if required_file in analysis_info.get("outputs", []):
                        if os.path.basename(gen_script_name) == os.path.basename(script_to_run_if_dependency_succeeds):
                            logger.info(f"Script '{gen_script_name}' parece gerar seu próprio input '{required_file}'. Não considerar como dependência.")
                            continue
                        found_generating_script = gen_script_name
                        break
                if found_generating_script:
                    self.memory.add_message(Message.assistant_message(
                        f"O arquivo '{required_file}' necessário para '{os.path.basename(script_to_run_if_dependency_succeeds)}' não foi encontrado. "
                        f"Verifiquei que '{os.path.basename(found_generating_script)}' pode gerá-lo. Tentarei executar '{os.path.basename(found_generating_script)}' primeiro."
                    ))
                    self._pending_script_after_dependency = script_to_run_if_dependency_succeeds
                    self._original_tool_call_for_pending_script = tool_call_to_check
                    new_tool_call_args = {"file_path": str(config.workspace_root / found_generating_script)}
                    self.tool_calls = [ToolCall(
                        id=str(uuid.uuid4()),
                        function=FunctionCall(name=SandboxPythonExecutor().name, arguments=json.dumps(new_tool_call_args))
                    )]
                    logger.info(f"Execução de '{os.path.basename(script_to_run_if_dependency_succeeds)}' adiada. Executando dependência '{os.path.basename(found_generating_script)}' primeiro.")
                else:
                    self.memory.add_message(Message.assistant_message(
                        f"O arquivo '{required_file}' necessário para '{os.path.basename(script_to_run_if_dependency_succeeds)}' não foi encontrado, e não identifiquei um script no workspace que o gere. "
                        "Vou precisar que você forneça este arquivo ou um script para gerá-lo."
                    ))
                    self.tool_calls = []
                    logger.info(f"Nenhum script gerador encontrado para '{required_file}'. O LLM deverá usar AskHuman.")
        return result

    async def _analyze_python_script(self, script_path: str, script_content: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"Analisando script Python: {script_path}")
        analysis = {"inputs": [], "outputs": [], "libraries": []}

        if not script_content:
            try:
                editor_tool = self.available_tools.get_tool(StrReplaceEditor().name)
                if not editor_tool:
                    logger.error("Ferramenta StrReplaceEditor não encontrada para _analyze_python_script.")
                    return analysis
                script_content_result = await editor_tool.execute(command="view", path=script_path)
                if isinstance(script_content_result, str):
                    script_content = script_content_result
                else:
                    logger.error(f"Falha ao ler o conteúdo de {script_path} para análise: {script_content_result}")
                    return analysis
            except ToolError as e:
                logger.error(f"ToolError ao ler {script_path} para análise: {e}")
                return analysis
            except Exception as e:
                logger.error(f"Erro inesperado ao ler {script_path} para análise: {e}")
                return analysis

        if not script_content:
            return analysis

        input_patterns = [
            r"pd\.read_csv\s*\(\s*['\"]([^'\"]+)['\"]",
            r"pd\.read_excel\s*\(\s*['\"]([^'\"]+)['\"]",
            r"open\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]r[^'\"]*['\"]",
            r"json\.load\s*\(\s*open\s*\(\s*['\"]([^'\"]+)['\"]",
            r"np\.load\s*\(\s*['\"]([^'\"]+)['\"]",
        ]
        for pattern in input_patterns:
            for match in re.finditer(pattern, script_content):
                analysis["inputs"].append(os.path.basename(match.group(1)))

        output_patterns = [
            r"df\.to_csv\s*\(\s*['\"]([^'\"]+)['\"]",
            r"df\.to_excel\s*\(\s*['\"]([^'\"]+)['\"]",
            r"open\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]w[^'\"]*['\"]",
            r"open\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]a[^'\"]*['\"]",
            r"json\.dump\s*\(.*,\s*open\s*\(\s*['\"]([^'\"]+)['\"]",
            r"plt\.savefig\s*\(\s*['\"]([^'\"]+)['\"]",
            r"np\.save\s*\(\s*['\"]([^'\"]+)['\"]",
        ]
        for pattern in output_patterns:
            for match in re.finditer(pattern, script_content):
                analysis["outputs"].append(os.path.basename(match.group(1)))

        library_patterns = [
            r"^\s*import\s+([a-zA-Z0-9_]+)",
            r"^\s*from\s+([a-zA-Z0-9_]+)\s+import"
        ]
        for pattern in library_patterns:
            for match in re.finditer(pattern, script_content, re.MULTILINE):
                lib_name = match.group(1)
                if lib_name not in analysis["libraries"]:
                    analysis["libraries"].append(lib_name)

        analysis["inputs"] = sorted(list(set(analysis["inputs"])))
        analysis["outputs"] = sorted(list(set(analysis["outputs"])))
        analysis["libraries"] = sorted(list(set(analysis["libraries"])))

        logger.info(f"Análise de {script_path}: Inputs: {analysis['inputs']}, Outputs: {analysis['outputs']}, Bibliotecas: {analysis['libraries']}")
        return analysis

    async def _analyze_workspace(self) -> Dict[str, Dict[str, Any]]:
        logger.info("Analisando scripts Python no workspace...")
        if self._workspace_script_analysis_cache:
             logger.info("Retornando análise de workspace do cache.")
             return self._workspace_script_analysis_cache

        workspace_scripts_analysis: Dict[str, Dict[str, Any]] = {}
        editor_tool = self.available_tools.get_tool(StrReplaceEditor().name)
        if not editor_tool:
            logger.error("Ferramenta StrReplaceEditor não encontrada para _analyze_workspace.")
            return workspace_scripts_analysis

        try:
            workspace_path_str = str(config.workspace_root)
            dir_listing_result = await editor_tool.execute(command="view", path=workspace_path_str)

            if isinstance(dir_listing_result, str):
                python_files = [line.strip() for line in dir_listing_result.splitlines() if line.strip().endswith(".py")]
                logger.info(f"Scripts Python encontrados no workspace ({workspace_path_str}): {python_files}")
                for script_name in python_files:
                    full_script_path = str(config.workspace_root / script_name)
                    workspace_scripts_analysis[script_name] = await self._analyze_python_script(full_script_path)
            else:
                logger.error(f"Falha ao listar arquivos do workspace para análise: {dir_listing_result}")

        except ToolError as e:
            logger.error(f"ToolError ao listar arquivos do workspace para análise: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao analisar workspace: {e}")

        self._workspace_script_analysis_cache = workspace_scripts_analysis
        return workspace_scripts_analysis

    async def _initiate_sandbox_script_cancellation(self):
        """Tenta ler um PID do arquivo de PID rastreado e enviar um sinal SIGTERM para ele no sandbox."""
        if not self._current_sandbox_pid_file:
            logger.warning("_initiate_sandbox_script_cancellation chamado sem _current_sandbox_pid_file definido.")
            return

        if self._current_sandbox_pid is None:
            try:
                pid_str = await SANDBOX_CLIENT.read_file(self._current_sandbox_pid_file)
                pid = int(pid_str.strip())
                self._current_sandbox_pid = pid
                logger.info(f"PID {pid} lido com sucesso de {self._current_sandbox_pid_file}")
            except FileNotFoundError:
                logger.warning(f"Arquivo PID {self._current_sandbox_pid_file} não encontrado. O script pode já ter terminado.")
                self.memory.add_message(Message.assistant_message("Não foi possível encontrar o arquivo de PID para cancelamento; o script pode já ter terminado."))
                # Tenta limpar o registro do arquivo PID inexistente chamando o helper de limpeza existente
                # Isso também limpará os atributos relacionados se o ID da chamada de ferramenta atual corresponder.
                # No entanto, neste estágio, a chamada de ferramenta ainda não "terminou", então a limpeza direta é melhor.
                if hasattr(self, '_cleanup_sandbox_file') and callable(getattr(self, '_cleanup_sandbox_file')):
                    # Chama a limpeza principal para este caminho de arquivo que também deve limpar atributos
                     await self._cleanup_sandbox_file(self._current_sandbox_pid_file) # Isso registrará seu próprio sucesso/falha
                # Limpa explicitamente os atributos aqui porque o script é considerado desaparecido ou seu estado desconhecido.
                self._current_sandbox_pid_file = None
                self._current_script_tool_call_id = None
                self._current_sandbox_pid = None
                return
            except (ValueError, TypeError) as e:
                logger.error(f"Conteúdo inválido no arquivo PID {self._current_sandbox_pid_file}: {pid_str if 'pid_str' in locals() else 'conteúdo desconhecido'}. Erro: {e}")
                self.memory.add_message(Message.assistant_message(f"Conteúdo inválido no arquivo de PID ({self._current_sandbox_pid_file}). Não é possível cancelar."))
                if hasattr(self, '_cleanup_sandbox_file') and callable(getattr(self, '_cleanup_sandbox_file')):
                     await self._cleanup_sandbox_file(self._current_sandbox_pid_file)
                self._current_sandbox_pid_file = None
                self._current_script_tool_call_id = None
                self._current_sandbox_pid = None
                return
            except Exception as e: # Captura outros erros do SANDBOX_CLIENT como problemas de permissão ou sandbox inativo
                logger.error(f"Erro ao ler arquivo PID {self._current_sandbox_pid_file}: {e}")
                self.memory.add_message(Message.assistant_message(f"Erro ao ler o arquivo de PID para cancelamento: {e}"))
                # Não limpe _current_sandbox_pid_file aqui, pois o arquivo ainda pode existir, apenas ilegível temporariamente.
                # A chamada de ferramenta original ainda pode ser concluída e acionar a limpeza adequada através do bloco finally de execute_tool.
                return

        if self._current_sandbox_pid is not None:
            try:
                kill_command = f"kill -SIGTERM {self._current_sandbox_pid}"
                logger.info(f"Tentando executar comando kill no sandbox: {kill_command}")
                # Adiciona mensagem antes de enviar kill, para que o usuário veja mesmo se o agente/sandbox tiver problemas durante o comando
                self.memory.add_message(Message.assistant_message(f"Enviando sinal de cancelamento (SIGTERM) para o processo {self._current_sandbox_pid} no sandbox..."))
                result = await SANDBOX_CLIENT.run_command(kill_command, timeout=10) # Usando SIGTERM

                if result.get("exit_code") == 0:
                    logger.info(f"SIGTERM enviado com sucesso para PID {self._current_sandbox_pid}. Saída stdout do comando kill: '{result.get('stdout','').strip()}', stderr: '{result.get('stderr','').strip()}'")
                    # Mensagem do usuário para envio de sinal bem-sucedido já foi adicionada.
                else:
                    # Isso pode acontecer se o processo já terminou entre a leitura do PID e o comando kill.
                    logger.warning(f"Comando kill para PID {self._current_sandbox_pid} falhou ou PID não encontrado. Código de saída: {result.get('exit_code')}. Stderr: '{result.get('stderr','').strip()}'")
                    # self.memory.add_message(Message.assistant_message(f"Falha ao enviar sinal de cancelamento para o script (PID: {self._current_sandbox_pid}), ou o script já havia terminado. Detalhes: {result.get('stderr','').strip()}"))
                    # Não há necessidade de outra mensagem se a anterior indicou uma tentativa. O log é suficiente.
            except Exception as e:
                logger.error(f"Exceção ao tentar matar PID {self._current_sandbox_pid}: {e}")
                self.memory.add_message(Message.assistant_message(f"Erro ao tentar cancelar o script (PID: {self._current_sandbox_pid}): {e}"))
        # Conforme o plano, não limpe as informações do PID aqui; isso é tratado pelo bloco finally de ToolCallAgent.execute_tool.

    async def _cleanup_sandbox_file(self, file_path_in_sandbox: str):
        """Auxiliar para remover um arquivo do sandbox."""
        if not file_path_in_sandbox:
            return
        try:
            logger.info(f"Tentando limpar arquivo do sandbox: {file_path_in_sandbox}")
            # Garante que SANDBOX_CLIENT está disponível e run_command é awaitable
            cleanup_result = await SANDBOX_CLIENT.run_command(f"rm -f {file_path_in_sandbox}", timeout=10)
            if cleanup_result.get("exit_code") != 0:
                logger.warning(f"Falha ao limpar arquivo do sandbox '{file_path_in_sandbox}'. Erro: {cleanup_result.get('stderr')}")
            else:
                logger.info(f"Arquivo do sandbox limpo com sucesso: {file_path_in_sandbox}")
        except Exception as e:
            logger.error(f"Exceção durante a limpeza do arquivo do sandbox para '{file_path_in_sandbox}': {e}")

    async def periodic_user_check_in(self, is_final_check: bool = False, is_failure_scenario: bool = False) -> bool:
        user_interaction_tool_name = AskHuman().name
        if user_interaction_tool_name not in self.available_tools.tool_map:
            logger.warning(f"Ferramenta de interação com o usuário '{user_interaction_tool_name}' não disponível. Continuando execução.")
            self.memory.add_message(Message.system_message(f"Interação periódica com usuário pulada: ferramenta '{user_interaction_tool_name}' não encontrada."))
            return True

        checklist_content_str = "Checklist não encontrado ou vazio."
        checklist_path = str(config.workspace_root / "checklist_principal_tarefa.md")
        local_file_op = LocalFileOperator()
        try:
            checklist_content_str = await local_file_op.read_file(checklist_path)
            if not checklist_content_str.strip():
                checklist_content_str = "Checklist encontrado, mas está vazio."
            logger.info(f"Conteúdo do checklist lido localmente para autoanálise: {checklist_content_str[:200]}...")
        except ToolError as e_tool_error:
            logger.info(f"Checklist '{checklist_path}' não encontrado (ou erro ao ler localmente) para autoanálise: {str(e_tool_error)}. Usando mensagem padrão.")
        except Exception as e_checklist:
            logger.error(f"Erro inesperado ao ler checklist localmente para autoanálise: {str(e_checklist)}")
            checklist_content_str = f"Erro inesperado ao ler checklist: {str(e_checklist)}"

        prompt_messages_list = [Message(role=Role.SYSTEM, content=self.system_prompt)]
        num_messages_for_context = 7
        mensagens_recentes_raw = self.memory.messages[-num_messages_for_context:]
        
        present_tool_response_ids = set()
        for msg_scan_tool_responses in mensagens_recentes_raw:
            if msg_scan_tool_responses.role == Role.TOOL and hasattr(msg_scan_tool_responses, 'tool_call_id') and msg_scan_tool_responses.tool_call_id:
                present_tool_response_ids.add(msg_scan_tool_responses.tool_call_id)

        final_filtered_messages: List[Message] = []
        assistant_tool_call_map: Dict[str, int] = {}
        for i, msg_map_assistant in enumerate(mensagens_recentes_raw):
            if msg_map_assistant.role == Role.ASSISTANT and msg_map_assistant.tool_calls:
                for tc_map in msg_map_assistant.tool_calls:
                    assistant_tool_call_map[tc_map.id] = i

        for i, msg_original in enumerate(mensagens_recentes_raw):
            msg = msg_original.model_copy(deep=True)

            if msg.role == Role.ASSISTANT and msg.tool_calls:
                all_tool_calls_have_responses = True
                temp_tool_calls_for_current_assistant_msg = []

                for tc_assistant in msg.tool_calls:
                    if tc_assistant.id not in present_tool_response_ids:
                        all_tool_calls_have_responses = False
                    else:
                        temp_tool_calls_for_current_assistant_msg.append(tc_assistant)

                if not all_tool_calls_have_responses:
                    msg.tool_calls = None
                elif not temp_tool_calls_for_current_assistant_msg:
                    msg.tool_calls = None
            elif msg.role == Role.TOOL:
                if not (hasattr(msg, 'tool_call_id') and msg.tool_call_id and msg.tool_call_id in assistant_tool_call_map):
                    continue
            final_filtered_messages.append(msg)
        
        prompt_messages_list.extend(final_filtered_messages)
        
        internal_prompt_text = INTERNAL_SELF_ANALYSIS_PROMPT_TEMPLATE.format(
            X=num_messages_for_context, 
            checklist_content=checklist_content_str
        )
        prompt_messages_list.append(Message(role=Role.USER, content=internal_prompt_text))

        relatorio_autoanalise = "Não foi possível gerar o relatório de autoanálise devido a um erro interno."
        try:
            logger.info("Iniciando chamada LLM interna para autoanálise...")
            if hasattr(self, 'llm') and self.llm:
                 relatorio_autoanalise = await self.llm.ask(messages=prompt_messages_list, stream=False) 
                 logger.info(f"Relatório de autoanálise recebido do LLM: {relatorio_autoanalise[:300]}...")
            else:
                logger.error("Instância LLM (self.llm) não disponível para autoanálise.")
        except Exception as e_llm_call:
            logger.error(f"Erro durante chamada LLM interna para autoanálise: {e_llm_call}")
            relatorio_autoanalise = f"Não foi possível gerar o relatório de autoanálise devido a um erro: {e_llm_call}"
        
        pergunta = ""
        if is_failure_scenario:
            last_llm_thought = ""
            if self.memory.messages and self.memory.messages[-1].role == Role.ASSISTANT:
                last_llm_thought = self.memory.messages[-1].content
            error_details_for_prompt = f"Detalhes do erro (conforme meu último pensamento): {last_llm_thought}" if last_llm_thought else "Não consegui obter detalhes específicos do erro do meu processamento interno."
            pergunta = (
                f"Encontrei um problema que me impede de continuar a tarefa como planejado.\n"
                f"Relatório de Autoanálise (sobre a falha):\n{relatorio_autoanalise}\n\n"
                f"{error_details_for_prompt}\n\n"
                f"Você gostaria que eu finalizasse a tarefa agora devido a esta dificuldade?\n\n"
                f"Por favor, responda com:\n"
                f"- 'sim, finalizar' (para encerrar a tarefa com falha)\n"
                f"- 'não, tentar outra abordagem: [suas instruções]' (se você tiver uma sugestão ou quiser que eu tente algo diferente)"
            )
        elif is_final_check:
            pergunta = (
                f"Todos os itens do checklist foram concluídos. Aqui está meu relatório de autoanálise final:\n{relatorio_autoanalise}\n\n"
                f"Você está satisfeito com o resultado e deseja que eu finalize a tarefa?\n\n"
                f"Por favor, responda com:\n"
                f"- 'sim' (para finalizar a tarefa com sucesso)\n"
                f"- 'revisar: [suas instruções para revisão]' (se algo precisa ser ajustado antes de finalizar)"
            )
        else:
            pergunta = (
                f"Aqui está meu relatório de autoanálise e planejamento:\n{relatorio_autoanalise}\n\n"
                f"Considerando isso, completei um ciclo de {self.max_steps} etapas (total de etapas realizadas: {self.current_step}).\n"
                f"Você quer que eu continue por mais {self.max_steps} etapas (possivelmente seguindo o plano sugerido, se houver)? Ou você prefere parar ou me dar novas instruções?\n\n"
                f"Por favor, responda com:\n"
                f"- 'continuar' (para prosseguir por mais {self.max_steps} etapas)\n"
                f"- 'parar' (para encerrar a tarefa atual)\n"
                f"- 'mudar: [suas novas instruções]' (para fornecer uma nova direção)"
            )
        
        # Verifica script cancelável antes de pedir entrada do usuário no caso geral
        if not is_failure_scenario and not is_final_check:
            if hasattr(self, '_current_sandbox_pid_file') and self._current_sandbox_pid_file:
                logger.info(f"Pausa solicitada pelo usuário. Script atualmente em execução com arquivo PID: {self._current_sandbox_pid_file}. Tentando cancelamento.")
                # Assumindo que _initiate_sandbox_script_cancellation será um método assíncrono
                # Idealmente, também deveria adicionar uma mensagem à memória sobre seu resultado.
                # Por enquanto, adicionamos uma mensagem genérica aqui.
                self.memory.add_message(Message.assistant_message("Tentativa de cancelamento do script em execução no sandbox devido à solicitação de pausa..."))
                if hasattr(self, '_initiate_sandbox_script_cancellation') and callable(getattr(self, '_initiate_sandbox_script_cancellation')):
                    await self._initiate_sandbox_script_cancellation()
                else:
                    logger.warning("Método _initiate_sandbox_script_cancellation não encontrado, não é possível cancelar script.")
                    self.memory.add_message(Message.assistant_message("AVISO: Funcionalidade de cancelamento de script não implementada neste agente."))

        logger.info(f"Manus: Solicitando feedback do usuário com prompt: {pergunta[:500]}...")
        self.memory.add_message(Message.assistant_message(content=pergunta))

        user_response_text = ""
        user_response_content_for_memory = ""
        try:
            tool_instance = self.available_tools.get_tool(user_interaction_tool_name)
            if tool_instance:
                user_response_content_from_tool = await tool_instance.execute(inquire=pergunta)
                if isinstance(user_response_content_from_tool, str):
                    user_response_content_for_memory = user_response_content_from_tool
                    user_response_text = user_response_content_from_tool.strip().lower()
                    self.memory.add_message(Message.user_message(content=user_response_content_for_memory))
                else:
                    logger.warning(f"Resposta inesperada da ferramenta {user_interaction_tool_name}: {user_response_content_from_tool}")
                    user_response_content_for_memory = str(user_response_content_from_tool)
                    user_response_text = ""
                    self.memory.add_message(Message.user_message(content=user_response_content_for_memory))
            else:
                logger.error(f"Falha ao obter instância da ferramenta {user_interaction_tool_name} novamente.")
                return True
        except Exception as e:
            logger.error(f"Erro ao usar a ferramenta '{user_interaction_tool_name}': {e}")
            self.memory.add_message(Message.system_message(f"Erro durante interação periódica com usuário: {e}. Continuando execução."))
            return True

        if is_failure_scenario:
            if user_response_text == "sim, finalizar":
                self.memory.add_message(Message.assistant_message("Entendido. Vou finalizar a tarefa agora devido à falha."))
                self.tool_calls = [ToolCall(id=str(uuid.uuid4()), function=FunctionCall(name=Terminate().name, arguments='{"status": "failure", "message": "Usuário consentiu finalizar devido a falha irrecuperável."}'))]
                self.state = AgentState.TERMINATED
                self._just_resumed_from_feedback = False
                return False
            elif user_response_text.startswith("não, tentar outra abordagem:"):
                nova_instrucao = user_response_content_for_memory.replace("não, tentar outra abordagem:", "").strip()
                logger.info(f"Manus: Usuário forneceu novas instruções após falha: {nova_instrucao}")
                self.memory.add_message(Message.assistant_message(f"Entendido. Vou tentar a seguinte abordagem: {nova_instrucao}"))
                self._just_resumed_from_feedback = True
                return True
            else:
                logger.info(f"Manus: Usuário forneceu entrada não reconhecida ('{user_response_text}') durante verificação de falha. Solicitando novamente.")
                self.memory.add_message(Message.assistant_message(f"Não entendi sua resposta ('{user_response_content_for_memory}'). Por favor, use 'sim, finalizar' ou 'não, tentar outra abordagem: [instruções]'."))
                self._just_resumed_from_feedback = True
                return True
        elif is_final_check:
            if user_response_text == "sim":
                self.memory.add_message(Message.assistant_message("Ótimo! Vou finalizar a tarefa agora com sucesso."))
                self.tool_calls = [ToolCall(id=str(uuid.uuid4()), function=FunctionCall(name=Terminate().name, arguments='{"status": "success", "message": "Tarefa concluída com sucesso com aprovação do usuário."}'))]
                self.state = AgentState.TERMINATED
                self._just_resumed_from_feedback = False
                return False
            elif user_response_text.startswith("revisar:"):
                nova_instrucao = user_response_content_for_memory.replace("revisar:", "").strip()
                logger.info(f"Manus: Usuário forneceu novas instruções para revisão final: {nova_instrucao}")
                self.memory.add_message(Message.assistant_message(f"Entendido. Vou revisar com base nas suas instruções: {nova_instrucao}"))
                self._just_resumed_from_feedback = True
                return True
            else:
                logger.info(f"Manus: Usuário forneceu entrada não reconhecida ('{user_response_text}') durante verificação final. Solicitando novamente.")
                self.memory.add_message(Message.assistant_message(f"Não entendi sua resposta ('{user_response_content_for_memory}'). Por favor, use 'sim' para finalizar ou 'revisar: [instruções]'."))
                self._just_resumed_from_feedback = True
                return True
        else:
            if user_response_text == "parar":
                self.state = AgentState.USER_HALTED
                self._just_resumed_from_feedback = False
                return False
            elif user_response_text.startswith("mudar:"):
                nova_instrucao = user_response_content_for_memory.replace("mudar:", "").strip()
                logger.info(f"Manus: Usuário forneceu novas instruções: {nova_instrucao}")
                self.memory.add_message(Message.assistant_message(f"Entendido. Vou seguir suas novas instruções: {nova_instrucao}"))
                self._just_resumed_from_feedback = True
                return True
            else: # Padrão para continuar para qualquer outra entrada ou entrada vazia.
                if user_response_text == "continuar":
                    logger.info("Manus: Usuário escolheu CONTINUAR execução.")
                    self.memory.add_message(Message.assistant_message("Entendido. Continuando com a tarefa."))
                elif not user_response_text and user_response_content_for_memory is not None : # Captura string vazia se user_response_content_for_memory foi preenchido
                     logger.info("Manus: Usuário forneceu resposta vazia, interpretada como 'CONTINUAR'.")
                     self.memory.add_message(Message.assistant_message("Resposta vazia recebida. Continuando com a tarefa."))
                else: # Captura qualquer outra resposta não vazia e não específica
                     logger.info(f"Manus: Usuário respondeu '{user_response_text}', interpretado como 'CONTINUAR'.")
                     self.memory.add_message(Message.assistant_message(f"Resposta '{user_response_content_for_memory}' recebida. Continuando com a tarefa."))

                self._just_resumed_from_feedback = True # Define isso para não pedirmos feedback novamente imediatamente
                return True
