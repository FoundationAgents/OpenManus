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


# New constant for internal self-analysis
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
    """A versatile general-purpose agent with support for both local and MCP tools."""

    name: str = "Manus"
    description: str = "A versatile agent that can solve various tasks using multiple tools including MCP-based tools"

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


    def __getstate__(self):
        logger.info(f"Manus.__getstate__ called for instance: {self!r}")
        state = self.__dict__.copy()
        state.pop('_mcp_clients', None)
        state.pop('available_tools', None)
        state.pop('llm', None)
        logger.info(f"Manus.__getstate__ final keys: {list(state.keys())}")
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
        from app.tool.file_system_tools import ListFilesTool # Added ListFilesTool

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
            CheckFileExistenceTool(), ListFilesTool() # Added ListFilesTool
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
        from app.tool.file_system_tools import ListFilesTool # Added ListFilesTool
        self.available_tools = ToolCollection(
            PythonExecute(), BrowserUseTool(), StrReplaceEditor(), AskHuman(), Terminate(),
            Bash(), SandboxPythonExecutor(), FormatPythonCode(), ReplaceCodeBlock(),
            ApplyDiffPatch(), ASTRefactorTool(), ReadFileContentTool(),
            ViewChecklistTool(), AddChecklistTaskTool(), UpdateChecklistTaskTool(),
            CheckFileExistenceTool(), ListFilesTool() # Added ListFilesTool
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
        logger.info(f"Manus agent created. System prompt (first 500 chars): {instance.system_prompt[:500]}")
        await instance.initialize_mcp_servers()
        instance._initialized = True
        return instance

    async def initialize_mcp_servers(self) -> None:
        for server_id, server_config in config.mcp_config.servers.items():
            try:
                if server_config.type == "sse":
                    if server_config.url:
                        await self.connect_mcp_server(server_config.url, server_id)
                        logger.info(f"Connected to MCP server {server_id} at {server_config.url}")
                elif server_config.type == "stdio":
                    if server_config.command:
                        await self.connect_mcp_server(
                            server_config.command, server_id, use_stdio=True, stdio_args=server_config.args,
                        )
                        logger.info(f"Connected to MCP server {server_id} using command {server_config.command}")
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server_id}: {e}")

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
        logger.info("Manus.cleanup: Starting Manus agent specific cleanup...")
        if self.browser_context_helper:
            await self.browser_context_helper.cleanup_browser()
        if self._initialized:
            await self.disconnect_mcp_server()
            self._initialized = False
        if hasattr(self, 'available_tools') and self.available_tools:
            for tool_name, tool_instance in self.available_tools.tool_map.items():
                if hasattr(tool_instance, "cleanup") and callable(getattr(tool_instance, "cleanup")):
                    try: await tool_instance.cleanup()
                    except Exception as e: logger.error(f"Error during cleanup of tool {tool_name}: {e}")
        try:
            await SANDBOX_CLIENT.cleanup()
        except Exception as e: logger.error(f"Error during SANDBOX_CLIENT.cleanup in Manus.cleanup: {e}")
        logger.info("Manus agent cleanup finished.")

    async def _internal_tool_feedback_check(self, tool_call: Optional[ToolCall] = None) -> bool: return False
    async def _is_checklist_complete(self) -> bool:
        try:
            manager = ChecklistManager()
            await manager._load_checklist()
            tasks = manager.get_tasks() # Get tasks once

            if not tasks:
                logger.info("Manus._is_checklist_complete: Checklist is not complete because no tasks were found (file might be empty or missing).")
                return False

            # NEW LOGIC START
            # Check if the *only* task is a generic decomposition task and it's marked completed.
            # This is a heuristic.
            decomposition_task_description_variations = [
                "decompor a solicitação do usuário e popular o checklist com as subtarefas",
                "decompor a tarefa do usuário em subtarefas claras",
                "decompor o pedido do usuário e preencher o checklist",
                "popular o checklist com as subtarefas da solicitação do usuário",
                "criar checklist inicial a partir da solicitação do usuário"
                # Add other common variations if observed during testing/operation
            ]

            if len(tasks) == 1:
                single_task = tasks[0]
                # Normalize for safer comparison: lowercased and stripped description
                normalized_single_task_desc = single_task.get('description', '').strip().lower()
                # Normalize status: lowercased and stripped
                single_task_status = single_task.get('status', '').strip().lower()

                is_generic_decomposition_task = any(
                    variation.lower() in normalized_single_task_desc for variation in decomposition_task_description_variations
                )

                if is_generic_decomposition_task and single_task_status == 'concluído':
                    logger.warning("Manus._is_checklist_complete: Checklist only contains the initial decomposition-like task "
                                   "marked as 'Concluído'. This is likely premature. "
                                   "Considering checklist NOT complete to enforce population of actual sub-tasks.")
                    # Optional: Add a system message to guide the LLM for the next step.
                    # This requires self.memory to be accessible and a Message class.
                    # from app.schema import Message, Role # Ensure import if used
                    # self.memory.add_message(Message.system_message(
                    #    "Lembrete: A tarefa de decomposição só é verdadeiramente concluída após as subtarefas resultantes "
                    #    "serem adicionadas ao checklist e o trabalho nelas ter começado. Por favor, adicione as subtarefas agora."
                    # ))
                    return False
            # NEW LOGIC END

            # Proceed with the original logic if the above condition isn't met
            # The manager.are_all_tasks_complete() method itself checks if all loaded tasks are 'Concluído'.
            # It will correctly return False if there are tasks but not all are 'Concluído'.
            all_complete_according_to_manager = manager.are_all_tasks_complete()

            if not all_complete_according_to_manager:
                 # Log already done by are_all_tasks_complete if it returns false due to incomplete tasks
                 logger.info(f"Manus._is_checklist_complete: Checklist is not complete based on ChecklistManager.are_all_tasks_complete() returning False.")
                 return False

            # If manager.are_all_tasks_complete() returned True, it means all tasks it found are complete.
            # And if we passed the new heuristic check (i.e., it's not a single, prematurely completed decomposition task),
            # then the checklist is genuinely complete.
            logger.info(f"Manus._is_checklist_complete: Checklist completion status: True (all tasks complete and not a premature decomposition).")
            return True

        except Exception as e:
            # Log the error and return False, as completion cannot be confirmed.
            logger.error(f"Error checking checklist completion in Manus._is_checklist_complete: {e}")
            return False

    async def should_request_feedback(self) -> bool:
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
        if self.current_step > 0 and self.max_steps > 0 and self.current_step % self.max_steps == 0:
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
        logger.info(f"Starting self-coding cycle for task: {task_prompt_for_llm}")
        script_content: Optional[str] = None
        host_script_path: str = ""
        final_result: Dict[str, Any] = {"success": False, "message": "Self-coding cycle not completed."}

        local_op = LocalFileOperator()

        for attempt in range(max_attempts):
            logger.info(f"Self-coding attempt {attempt + 1}/{max_attempts}")

            code_fixed_by_formatter = False
            targeted_edits_applied_this_attempt = False
            # analysis_failed_or_no_edits_suggested = False # This flag seems unused with new logic

            if attempt == 0:
                logger.info(f"Attempt {attempt + 1}: Generating initial script for task: {task_prompt_for_llm}")
                # Placeholder for LLM call to generate initial script
                generated_script_content = f"# Initial Script - Attempt {attempt + 1}\n# Task: {task_prompt_for_llm}\nprint(\"Attempting task: {task_prompt_for_llm}\")\n# Example: Intentionally introduce a syntax error for testing\n# print(\"Syntax error here\"\nwith open(\"output.txt\", \"w\") as f:\n    f.write(\"Output from script attempt {attempt + 1}\")\nprint(\"Script finished attempt {attempt + 1}.\")"
                script_content = self._sanitize_text_for_file(generated_script_content)
                if not script_content:
                    logger.error("LLM (simulated) failed to generate initial script content.")
                    final_result = {"success": False, "message": "LLM (simulated) failed to generate initial script."}
                    continue
                script_filename = f"temp_manus_script_{uuid.uuid4().hex[:8]}.py"
                host_script_path = str(config.workspace_root / script_filename)
                try:
                    await local_op.write_file(host_script_path, script_content)
                    logger.info(f"Initial script written to host: {host_script_path}")
                except Exception as e:
                    logger.error(f"Failed to write initial script to host: {e}")
                    final_result = {"success": False, "message": f"Failed to write initial script to host: {e}"}
                    continue
            elif not host_script_path or not os.path.exists(host_script_path):
                logger.error(f"host_script_path ('{host_script_path}') not defined or file does not exist on attempt {attempt + 1}. Critical error.")
                final_result = {"success": False, "message": "Internal error: Script path lost or file missing between attempts."}
                break

            sandbox_script_name_in_container = os.path.basename(host_script_path)
            sandbox_target_path_for_executor = f"/workspace/{sandbox_script_name_in_container}"

            str_editor_tool = self.available_tools.get_tool(StrReplaceEditor().name)
            if not str_editor_tool:
                logger.critical("StrReplaceEditor tool is not available for sandbox copy.")
                final_result = {"success": False, "message": "Critical error: StrReplaceEditor tool missing."}
                break

            copy_to_sandbox_succeeded = False
            try:
                await str_editor_tool.execute(command="copy_to_sandbox", path=host_script_path, container_filename=sandbox_script_name_in_container)
                logger.info(f"Script copy to sandbox successful: {host_script_path} -> {sandbox_target_path_for_executor}")
                copy_to_sandbox_succeeded = True
            except Exception as e_copy:
                logger.error(f"Failed to copy script to sandbox: {e_copy}")
                final_result = {"success": False, "message": f"Falha ao copiar script para o sandbox: {e_copy}", "status_code": "SANDBOX_COPY_FAILED"}
                continue

            execution_result = {}
            if copy_to_sandbox_succeeded:
                executor_tool = self.available_tools.get_tool(SandboxPythonExecutor().name)
                if not executor_tool:
                    logger.critical("SandboxPythonExecutor tool not found.")
                    final_result = {"success": False, "message": "SandboxPythonExecutor tool not found."}
                    break
                
                execution_result = await executor_tool.execute(file_path=sandbox_target_path_for_executor, timeout=30)
                logger.info(f"Sandbox execution: stdout='{execution_result.get('stdout')}', stderr='{execution_result.get('stderr')}', exit_code={execution_result.get('exit_code')}")
                final_result["last_execution_result"] = execution_result
            else:
                logger.error("Skipping execution as copy to sandbox failed.")
                continue

            exit_code = execution_result.get("exit_code", -1)
            stderr = execution_result.get("stderr", "")
            stdout = execution_result.get("stdout", "")
            
            if exit_code == 0:
                logger.info(f"Script executed successfully in attempt {attempt + 1}.")
                final_result = {"success": True, "message": "Script executado com sucesso.", "stdout": stdout, "stderr": stderr, "exit_code": exit_code}
                # Simplified success cleanup for now
                break
            else: # Script execution failed (exit_code != 0)
                logger.warning(f"Script execution failed in attempt {attempt + 1}. Exit code: {exit_code}, Stderr: {stderr}")
                final_result = {"success": False, "message": f"Execution failed in attempt {attempt+1}.", "stdout":stdout, "stderr":stderr, "exit_code":exit_code}

                if attempt >= max_attempts - 1:
                    logger.info("Last attempt failed. No more fixes will be tried.")
                    break

                # --- Debugging Funnel ---
                current_script_code_for_analysis = await local_op.read_file(host_script_path)

                if "SyntaxError:" in stderr or "IndentationError:" in stderr:
                    logger.info(f"[CORRECTION_ATTEMPT {attempt + 1}/{max_attempts}] Attempting to fix Syntax/Indentation error using formatter for script {host_script_path}.")
                    formatter_tool = self.available_tools.get_tool("format_python_code")
                    if formatter_tool:
                        format_result = await formatter_tool.execute(code=current_script_code_for_analysis)
                        if isinstance(format_result, str):
                            try:
                                ast.parse(format_result)
                                logger.info("Formatted code parsed successfully. Writing back.")
                                await local_op.write_file(host_script_path, format_result)
                                code_fixed_by_formatter = True
                            except SyntaxError as e_ast:
                                logger.warning(f"Formatted code still has syntax errors: {e_ast}.")
                        else:
                            logger.warning(f"Code formatter failed: {format_result.get('error')}.")
                    else:
                        logger.warning("format_python_code tool not found.")

                if code_fixed_by_formatter:
                    logger.info("Code fixed by formatter. Retrying.")
                    continue

                # LLM for Complex Fixes
                log_msg_llm_query = ""
                if "SyntaxError:" in stderr or "IndentationError:" in stderr: # Still a syntax error after formatter attempt
                    logger.info(f"[CORRECTION_ATTEMPT {attempt + 1}/{max_attempts}] Formatter did not fix syntax error for script {host_script_path}, or error was not format-related. Querying LLM.")
                else: # Runtime error
                    logger.info(f"[CORRECTION_ATTEMPT {attempt + 1}/{max_attempts}] Script {host_script_path} failed with runtime error. Querying LLM.")
                # The logger.info(log_msg_llm_query) was removed as the specific messages above cover it.

                current_script_code_for_analysis = await local_op.read_file(host_script_path) # Re-read in case formatter made changes
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
                            logger.info(f"[CORRECTION_ATTEMPT {attempt + 1}/{max_attempts}] LLM suggested tool '{tool_to_use_name}' for script {host_script_path}. Attempting execution with params: {tool_params_from_llm}")
                            chosen_tool = self.available_tools.get_tool(tool_to_use_name)
                            if chosen_tool:
                                if tool_to_use_name == "format_python_code":
                                    tool_params_from_llm["code"] = current_script_code_for_analysis # Ensure 'code' is passed
                                    tool_params_from_llm.pop("path", None)
                                else:
                                    tool_params_from_llm["path"] = host_script_path

                                tool_exec_result = await chosen_tool.execute(**tool_params_from_llm)
                                if isinstance(tool_exec_result, dict) and tool_exec_result.get("error"):
                                    logger.error(f"LLM-suggested tool '{tool_to_use_name}' failed: {tool_exec_result.get('error')}")
                                else: # Assumed success
                                    logger.info(f"LLM-suggested tool '{tool_to_use_name}' executed successfully.")
                                    targeted_edits_applied_this_attempt = True
                            else:
                                logger.warning(f"LLM suggested tool '{tool_to_use_name}' not found.")
                        elif tool_to_use_name is None: # LLM explicitly said no tool
                             logger.info(f"LLM explicitly suggested no tool. Comment: {parsed_llm_suggestion.get('comment')}")
                        else: # Invalid JSON structure from LLM
                            logger.warning(f"LLM suggestion JSON invalid. Suggestion: {parsed_llm_suggestion}")
                    except json.JSONDecodeError as json_e:
                        logger.error(f"Failed to parse JSON from LLM tool suggestion: {json_e}. Raw: {llm_analysis_response_str}")
                    except Exception as tool_apply_e:
                        logger.error(f"Error applying LLM suggested tool: {tool_apply_e}")
                else:
                    logger.warning("Could not extract JSON from LLM tool suggestion response.")

                if targeted_edits_applied_this_attempt:
                    logger.info("LLM-suggested edits applied. Retrying script execution.")
                    continue
                else:
                    logger.info("LLM-based correction failed or no valid edits applied this attempt.")
            
            # Cleanup sandbox script for this failed attempt (if copied)
            if copy_to_sandbox_succeeded and SANDBOX_CLIENT.sandbox and SANDBOX_CLIENT.sandbox.container:
                try: await SANDBOX_CLIENT.run_command(f"rm -f {sandbox_target_path_for_executor}")
                except Exception as e_rm_sandbox: logger.error(f"Error removing sandbox script post-attempt: {e_rm_sandbox}")

        # Final cleanup of host script if it still exists (e.g., all attempts failed)
        if host_script_path and os.path.exists(host_script_path):
            try: await local_op.delete_file(host_script_path)
            except Exception as e_final_clean: logger.error(f"Error in final deletion of host script {host_script_path}: {e_final_clean}")
        
        if not final_result["success"]:
             logger.error(f"Self-coding cycle ultimately failed after {max_attempts} attempts. Final result: {final_result}")
        
        self._monitoring_background_task = False
        self._background_task_log_file = None
        self._background_task_expected_artifact = None
        self._background_task_artifact_path = None
        self._background_task_description = None
        self._background_task_last_log_size = 0
        self._background_task_no_change_count = 0
        return final_result

    def _extract_json_from_response(self, llm_response: str) -> Optional[str]:
        """Extracts a JSON string from the LLM's response, handling markdown code blocks."""
        logger.debug(f"Attempting to extract JSON from LLM response: '{llm_response[:500]}...'")
        match = re.search(r"```json\s*([\s\S]+?)\s*```", llm_response)
        if match:
            json_str = match.group(1).strip()
            logger.debug(f"Extracted JSON string using regex: '{json_str[:500]}...'")
            return json_str
        
        response_stripped = llm_response.strip()
        if response_stripped.startswith("{") and response_stripped.endswith("}"):
            logger.debug("Response looks like a direct JSON object. Using as is.")
            return response_stripped
        
        logger.warning("No JSON code block found, and response is not a direct JSON object.")
        return None

    def _build_targeted_analysis_prompt(self, script_content: str, stdout: str, stderr: str, original_task: str) -> str:
        """Builds the prompt for the LLM to analyze and suggest a tool-based correction."""
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

        # --- Início da Lógica de Fallback para SandboxPythonExecutor ---
        last_message = self.memory.messages[-1] if self.memory.messages else None
        if (
            last_message
            and last_message.role == Role.TOOL
            and hasattr(last_message, "name") # O atributo 'name' pode não existir em todas as mensagens de TOOL
            and last_message.name == SandboxPythonExecutor().name
            and last_message.tool_call_id != self._fallback_attempted_for_tool_call_id
        ):
            try:
                tool_result_content = json.loads(last_message.content)
                if tool_result_content.get("exit_code") == -2:
                    logger.warning(
                        f"SandboxPythonExecutor failed with exit_code -2 (sandbox creation error) for tool_call_id {last_message.tool_call_id}. "
                        "Attempting fallback to PythonExecute."
                    )

                    original_assistant_message_with_tool_call = None
                    for msg in reversed(self.memory.messages):
                        if msg.role == Role.ASSISTANT and msg.tool_calls:
                            for tc in msg.tool_calls:
                                if tc.id == last_message.tool_call_id:
                                    original_assistant_message_with_tool_call = msg
                                    break
                            if original_assistant_message_with_tool_call:
                                break

                    if original_assistant_message_with_tool_call:
                        original_tool_call = next(
                            (tc for tc in original_assistant_message_with_tool_call.tool_calls if tc.id == last_message.tool_call_id),
                            None
                        )
                        if original_tool_call:
                            original_args = json.loads(original_tool_call.function.arguments)
                            fallback_args = {}

                            # Priorizar 'code' se existir nos argumentos originais da chamada ao SandboxPythonExecutor.
                            # Se não, usar 'file_path'. Se o LLM chamou SandboxPythonExecutor diretamente, pode ter 'code'.
                            if "code" in original_args and original_args["code"]:
                                fallback_args["code"] = original_args["code"]
                            elif "file_path" in original_args and original_args["file_path"]:
                                # PythonExecute espera 'code', então precisamos ler o conteúdo do arquivo.
                                # No entanto, PythonExecute também aceita 'file_path' diretamente em algumas versões/configurações.
                                # Para simplificar e alinhar com a intenção original de executar um script,
                                # vamos assumir que PythonExecute pode lidar com file_path se for o caso,
                                # ou idealmente, o LLM teria fornecido 'code' se era para ser código direto.
                                # A ferramenta PythonExecute em si pode precisar de lógica para carregar o código do file_path.
                                # Por agora, vamos passar o file_path se 'code' não estiver disponível.
                                # Esta parte pode precisar de ajuste dependendo da implementação exata de PythonExecute.
                                # Se PythonExecute SÓ aceita 'code', precisaremos ler o arquivo aqui.
                                # Para esta implementação, vamos assumir que PythonExecute pode receber file_path
                                # ou que a chamada original para python_execute (antes do override) tinha 'code'.

                                # Tentativa de encontrar a chamada original para python_execute que foi convertida
                                was_overridden = False
                                for prev_msg_idx in range(len(self.memory.messages) - 2, -1, -1):
                                    prev_msg = self.memory.messages[prev_msg_idx]
                                    if prev_msg.role == Role.ASSISTANT and prev_msg.tool_calls:
                                        for prev_tc in prev_msg.tool_calls:
                                            if prev_tc.id == original_tool_call.id and prev_tc.function.name == PythonExecute().name:
                                                logger.info(f"Found original PythonExecute call that was overridden to SandboxPythonExecutor (ID: {original_tool_call.id}). Reverting.")
                                                original_python_execute_args = json.loads(prev_tc.function.arguments)
                                                fallback_args = original_python_execute_args # Usar os args originais do python_execute
                                                was_overridden = True
                                                break
                                        if was_overridden:
                                            break

                                if not was_overridden: # Se não foi um override, mas uma chamada direta ao SandboxPythonExecutor
                                    if "file_path" in original_args:
                                         # Se PythonExecute só aceita 'code', precisamos ler o arquivo aqui.
                                         # Para manter simples, vamos apenas logar um aviso e não fazer fallback se não tivermos 'code'.
                                        logger.warning(f"SandboxPythonExecutor was called directly with file_path '{original_args['file_path']}'. "
                                                       "Fallback to PythonExecute requires 'code'. Cannot automatically read file content here. "
                                                       "Skipping fallback for this specific case unless original call was python_execute with 'code'.")
                                        fallback_args = None # Sinaliza que não podemos fazer fallback
                                    else: # Não tem 'code' nem 'file_path' nos args do SandboxPythonExecutor
                                        logger.error(f"Cannot perform fallback for SandboxPythonExecutor call {original_tool_call.id}: neither 'code' nor 'file_path' found in original arguments.")
                                        fallback_args = None


                            elif "code" in original_args and original_args["code"]: # Caso onde 'code' está nos args do SandboxPYExecutor
                                fallback_args["code"] = original_args["code"]
                            else: # Não tem 'code' nem 'file_path'
                                logger.error(f"Cannot perform fallback for SandboxPythonExecutor call {original_tool_call.id}: neither 'code' nor 'file_path' found in original arguments.")
                                fallback_args = None

                            if fallback_args:
                                fallback_timeout = original_args.get("timeout", 60) # Usar timeout original ou default
                                fallback_args["timeout"] = fallback_timeout

                                new_fallback_tool_call = ToolCall(
                                    id=str(uuid.uuid4()), # Novo ID para a tentativa de fallback
                                    function=FunctionCall(
                                        name=PythonExecute().name,
                                        arguments=json.dumps(fallback_args)
                                    )
                                )
                                self.tool_calls = [new_fallback_tool_call]
                                self._fallback_attempted_for_tool_call_id = last_message.tool_call_id

                                fallback_message = (
                                    f"A execução segura no sandbox falhou (erro de criação do sandbox). "
                                    f"Tentando executar o script diretamente com '{PythonExecute().name}'. "
                                    "AVISO: Executar scripts fora do sandbox pode apresentar riscos de segurança se o script for malicioso."
                                )
                                self.memory.add_message(Message.assistant_message(fallback_message))
                                logger.info(f"Planned fallback ToolCall: {new_fallback_tool_call}")
                                return True # Executar a tool_call de fallback
                            else:
                                logger.warning(f"Could not construct fallback arguments for tool_call_id {last_message.tool_call_id}. Fallback aborted.")
                        else:
                            logger.error(f"Could not find original ToolCall with id {last_message.tool_call_id} in assistant message {original_assistant_message_with_tool_call.id} for fallback.")
                    else:
                        logger.error(f"Could not find original assistant message for tool_call_id {last_message.tool_call_id} for fallback.")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool result content for fallback logic: {last_message.content}. Error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during sandbox fallback logic: {e}", exc_info=True)
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
            for msg in recent_messages_for_browser # Corrected variable name
            if msg.tool_calls
            for tc in msg.tool_calls
        )
        if browser_in_use:
            if self.browser_context_helper:
                self.next_step_prompt = (
                    await self.browser_context_helper.format_next_step_prompt()
                )
            else:
                logger.warning("BrowserContextHelper not initialized, cannot format next_step_prompt for browser.")

        result = await super().think()
        self.next_step_prompt = original_prompt

        # Override PythonExecute calls that execute external scripts to use SandboxPythonExecutor
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
                            # Regex for subprocess.run(['python3', 'script.py', ...])
                            # Allows for variations like "python", "python3", "python3.x"
                            # Captures the script path ('([^']+\.py)')
                            # Using the externalized regex pattern
                            # re_subprocess is now directly imported
                            # Regex for os.system('python3 script.py ...')
                            # Note: This regex for os.system might need similar externalization if it becomes complex or causes issues.
                            re_os_system = r"os\.system\s*\(\s*['\"](?:python|python3)(?:\.[\d]+)?\s+([^'\" ]+\.py)['\"].*?\)"

                            match_subprocess = re.search(re_subprocess, code_to_execute) # re_subprocess is now the compiled pattern
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

                                # Security check: Ensure the resolved path is within the workspace
                                if os.path.abspath(resolved_script_path).startswith(str(config.workspace_root)):
                                    logger.info(f"Overriding PythonExecute call for script '{script_path_match}' to SandboxPythonExecutor with path '{resolved_script_path}'.")
                                    new_arguments = {"file_path": resolved_script_path}
                                    if original_timeout is not None:
                                        new_arguments["timeout"] = original_timeout

                                    # Create a new ToolCall object for the override
                                    overridden_tool_call = ToolCall(
                                        id=tool_call.id, # Keep the same ID
                                        function=Function(
                                            name=SandboxPythonExecutor.name,
                                            arguments=json.dumps(new_arguments)
                                        )
                                    )
                                    new_tool_calls.append(overridden_tool_call)
                                    continue # Move to the next tool_call
                                else:
                                    logger.warning(f"PythonExecute call for script '{script_path_match}' resolved to '{resolved_script_path}', which is outside the workspace. Not overriding.")
                            else:
                                logger.info(f"PythonExecute call with code did not match script execution patterns. Code: {code_to_execute[:100]}...")
                        else:
                            logger.warning("PythonExecute call had no valid 'code' argument.")
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse arguments for PythonExecute: {tool_call.function.arguments}. Using original tool call.")
                    except Exception as e:
                        logger.error(f"Error during PythonExecute override logic: {e}. Using original tool call.")

                new_tool_calls.append(tool_call) # Add original or non-PythonExecute tool_call
            self.tool_calls = new_tool_calls

        if self.tool_calls and self.tool_calls[0].function.name == Bash().name: # Check the first tool call
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
                    logger.info(f"Artefato esperado definido como: {self._background_task_artifact_path} (Log file: {log_file})")
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
                    logger.error("StrReplaceEditor tool não encontrado para _analyze_python_script.")
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

        logger.info(f"Análise de {script_path}: Inputs: {analysis['inputs']}, Outputs: {analysis['outputs']}, Libraries: {analysis['libraries']}")
        return analysis

    async def _analyze_workspace(self) -> Dict[str, Dict[str, Any]]:
        logger.info("Analisando scripts Python no workspace...")
        if self._workspace_script_analysis_cache:
             logger.info("Retornando análise de workspace do cache.")
             return self._workspace_script_analysis_cache

        workspace_scripts_analysis: Dict[str, Dict[str, Any]] = {}
        editor_tool = self.available_tools.get_tool(StrReplaceEditor().name)
        if not editor_tool:
            logger.error("StrReplaceEditor tool não encontrado para _analyze_workspace.")
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
        """Attempts to read a PID from the tracked PID file and send a SIGTERM signal to it in the sandbox."""
        if not self._current_sandbox_pid_file:
            logger.warning("_initiate_sandbox_script_cancellation called without _current_sandbox_pid_file set.")
            return

        if self._current_sandbox_pid is None:
            try:
                pid_str = await SANDBOX_CLIENT.read_file(self._current_sandbox_pid_file)
                pid = int(pid_str.strip())
                self._current_sandbox_pid = pid
                logger.info(f"Successfully read PID {pid} from {self._current_sandbox_pid_file}")
            except FileNotFoundError:
                logger.warning(f"PID file {self._current_sandbox_pid_file} not found. Script might have already finished.")
                self.memory.add_message(Message.assistant_message("Não foi possível encontrar o arquivo de PID para cancelamento; o script pode já ter terminado."))
                # Attempt to clean up the non-existent PID file record by calling the existing cleanup helper
                # This will also clear the related attributes if the current tool call ID matches.
                # However, at this stage, the tool call hasn't "finished" yet, so direct cleanup is better.
                if hasattr(self, '_cleanup_sandbox_file') and callable(getattr(self, '_cleanup_sandbox_file')):
                    # Call the main cleanup for this file path which should also clear attributes
                     await self._cleanup_sandbox_file(self._current_sandbox_pid_file) # This will log its own success/failure
                # Explicitly clear attributes here because the script is considered gone or its state unknown.
                self._current_sandbox_pid_file = None
                self._current_script_tool_call_id = None
                self._current_sandbox_pid = None
                return
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid content in PID file {self._current_sandbox_pid_file}: {pid_str if 'pid_str' in locals() else 'unknown content'}. Error: {e}")
                self.memory.add_message(Message.assistant_message(f"Conteúdo inválido no arquivo de PID ({self._current_sandbox_pid_file}). Não é possível cancelar."))
                if hasattr(self, '_cleanup_sandbox_file') and callable(getattr(self, '_cleanup_sandbox_file')):
                     await self._cleanup_sandbox_file(self._current_sandbox_pid_file)
                self._current_sandbox_pid_file = None
                self._current_script_tool_call_id = None
                self._current_sandbox_pid = None
                return
            except Exception as e: # Catch other SANDBOX_CLIENT errors like permission issues or sandbox down
                logger.error(f"Error reading PID file {self._current_sandbox_pid_file}: {e}")
                self.memory.add_message(Message.assistant_message(f"Erro ao ler o arquivo de PID para cancelamento: {e}"))
                # Do not clear _current_sandbox_pid_file here, as the file might still exist, just unreadable temporarily.
                # The original tool call might still complete and trigger proper cleanup via execute_tool's finally block.
                return

        if self._current_sandbox_pid is not None:
            try:
                kill_command = f"kill -SIGTERM {self._current_sandbox_pid}"
                logger.info(f"Attempting to execute kill command in sandbox: {kill_command}")
                # Add message before sending kill, so user sees it even if agent/sandbox has issues during the command
                self.memory.add_message(Message.assistant_message(f"Enviando sinal de cancelamento (SIGTERM) para o processo {self._current_sandbox_pid} no sandbox..."))
                result = await SANDBOX_CLIENT.run_command(kill_command, timeout=10) # Using SIGTERM

                if result.get("exit_code") == 0:
                    logger.info(f"Successfully sent SIGTERM to PID {self._current_sandbox_pid}. Kill command stdout: '{result.get('stdout','').strip()}', stderr: '{result.get('stderr','').strip()}'")
                    # User message for successful signal send was already added.
                else:
                    # This can happen if the process already exited between PID read and kill command.
                    logger.warning(f"Kill command for PID {self._current_sandbox_pid} failed or PID not found. Exit code: {result.get('exit_code')}. Stderr: '{result.get('stderr','').strip()}'")
                    # self.memory.add_message(Message.assistant_message(f"Falha ao enviar sinal de cancelamento para o script (PID: {self._current_sandbox_pid}), ou o script já havia terminado. Detalhes: {result.get('stderr','').strip()}"))
                    # No need for another message if the previous one indicated an attempt. The log is sufficient.
            except Exception as e:
                logger.error(f"Exception while trying to kill PID {self._current_sandbox_pid}: {e}")
                self.memory.add_message(Message.assistant_message(f"Erro ao tentar cancelar o script (PID: {self._current_sandbox_pid}): {e}"))
        # As per plan, do not clear PID info here; it's handled by ToolCallAgent.execute_tool's finally block.

    async def _cleanup_sandbox_file(self, file_path_in_sandbox: str):
        """Helper to remove a file from the sandbox."""
        if not file_path_in_sandbox:
            return
        try:
            logger.info(f"Attempting to clean up sandbox file: {file_path_in_sandbox}")
            # Ensure SANDBOX_CLIENT is available and run_command is awaitable
            cleanup_result = await SANDBOX_CLIENT.run_command(f"rm -f {file_path_in_sandbox}", timeout=10)
            if cleanup_result.get("exit_code") != 0:
                logger.warning(f"Failed to clean up sandbox file '{file_path_in_sandbox}'. Error: {cleanup_result.get('stderr')}")
            else:
                logger.info(f"Successfully cleaned up sandbox file: {file_path_in_sandbox}")
        except Exception as e:
            logger.error(f"Exception during sandbox file cleanup for '{file_path_in_sandbox}': {e}")

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
        
        # Check for cancellable script before asking for user input in the general case
        if not is_failure_scenario and not is_final_check:
            if hasattr(self, '_current_sandbox_pid_file') and self._current_sandbox_pid_file:
                logger.info(f"Pause requested by user. Currently running script with PID file: {self._current_sandbox_pid_file}. Attempting cancellation.")
                # Assuming _initiate_sandbox_script_cancellation will be an async method
                # It should also ideally add a message to memory about its outcome.
                # For now, we add a generic message here.
                self.memory.add_message(Message.assistant_message("Tentativa de cancelamento do script em execução no sandbox devido à solicitação de pausa..."))
                if hasattr(self, '_initiate_sandbox_script_cancellation') and callable(getattr(self, '_initiate_sandbox_script_cancellation')):
                    await self._initiate_sandbox_script_cancellation()
                else:
                    logger.warning("_initiate_sandbox_script_cancellation method not found, cannot cancel script.")
                    self.memory.add_message(Message.assistant_message("AVISO: Funcionalidade de cancelamento de script não implementada neste agente."))

        logger.info(f"Manus: Asking user for feedback with prompt: {pergunta[:500]}...")
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
                logger.info(f"Manus: User provided new instructions after failure: {nova_instrucao}")
                self.memory.add_message(Message.assistant_message(f"Entendido. Vou tentar a seguinte abordagem: {nova_instrucao}"))
                self._just_resumed_from_feedback = True
                return True
            else:
                logger.info(f"Manus: User provided unrecognized input ('{user_response_text}') during failure check. Re-prompting.")
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
                logger.info(f"Manus: User provided new instructions for final review: {nova_instrucao}")
                self.memory.add_message(Message.assistant_message(f"Entendido. Vou revisar com base nas suas instruções: {nova_instrucao}"))
                self._just_resumed_from_feedback = True
                return True
            else:
                logger.info(f"Manus: User provided unrecognized input ('{user_response_text}') during final check. Re-prompting.")
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
                logger.info(f"Manus: User provided new instructions: {nova_instrucao}")
                self.memory.add_message(Message.assistant_message(f"Entendido. Vou seguir suas novas instruções: {nova_instrucao}"))
                self._just_resumed_from_feedback = True
                return True
            else: # Default to continue for any other input or empty input.
                if user_response_text == "continuar":
                    logger.info("Manus: User chose to CONTINUE execution.")
                    self.memory.add_message(Message.assistant_message("Entendido. Continuando com a tarefa."))
                elif not user_response_text and user_response_content_for_memory is not None : # Catches empty string if user_response_content_for_memory was populated
                     logger.info("Manus: User provided empty response, interpreted as 'CONTINUE'.")
                     self.memory.add_message(Message.assistant_message("Resposta vazia recebida. Continuando com a tarefa."))
                else: # Catches any other non-empty, non-specific response
                     logger.info(f"Manus: User responded '{user_response_text}', interpreted as 'CONTINUE'.")
                     self.memory.add_message(Message.assistant_message(f"Resposta '{user_response_content_for_memory}' recebida. Continuando com a tarefa."))

                self._just_resumed_from_feedback = True # Set this so we don't immediately ask for feedback again
                return True
