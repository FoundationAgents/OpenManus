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
from app.tool.file_system_tools import CheckFileExistenceTool
from app.agent.checklist_manager import ChecklistManager # Added for _is_checklist_complete
from .regex_patterns import re_subprocess


# New constant for internal self-analysis
INTERNAL_SELF_ANALYSIS_PROMPT_TEMPLATE = """You are Manus. You are at a checkpoint with the user.
Analyze the recent conversation history (last {X} messages), the current state of your task checklist (provided below), and any errors or difficulties you encountered.
Based on this, generate a concise "Self-Analysis and Planning Report" in English to present to the user.
The report should include:
1. A brief diagnosis of your current situation, including the **root cause of any recent difficulties or errors** (e.g., "I am trying X, but tool Y failed with error Z. I believe the root cause was [a poor choice of parameters for the tool / the tool not being suitable for this subtask / an issue in my original plan / etc.]").
2. At least one or two **CONCRETE alternative strategies** you can try to overcome these difficulties, including **specific corrections** for errors, if applicable (e.g., "I thought about trying A [describe A, e.g., 'using tool Y with corrected parameter W'] or B [describe B, e.g., 'using tool Q instead of Y for this step'] as alternatives.").
3. A suggestion on **how you can avoid similar errors in the future** (e.g., "To avoid this error in the future, I will [check X before using tool Y / always use tool Q for this type of task / etc.]").
4. Optional: If you have a preferred or more elaborate plan for one of the alternatives, mention it briefly.

Format the response ONLY with the report. Do not add introductory phrases like "Sure, here is the report".
If there are no significant difficulties or clear alternatives, state this concisely (e.g., "Diagnosis: Progress is stable on the current task. Alternatives: No major alternatives considered at the moment.").

Main Checklist Content (`checklist_principal_tarefa.md`):
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
            CheckFileExistenceTool(), # <--- ADDED HERE
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
        self.available_tools = ToolCollection(
            PythonExecute(), BrowserUseTool(), StrReplaceEditor(), AskHuman(), Terminate(),
            Bash(), SandboxPythonExecutor(), FormatPythonCode(), ReplaceCodeBlock(),
            ApplyDiffPatch(), ASTRefactorTool(), ReadFileContentTool(),
            ViewChecklistTool(), AddChecklistTaskTool(), UpdateChecklistTaskTool(),
            CheckFileExistenceTool(), # <--- ADDED HERE
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

                if is_generic_decomposition_task and single_task_status == 'completed': # Changed 'concluído' to 'completed'
                    logger.warning("Manus._is_checklist_complete: Checklist only contains the initial decomposition-like task "
                                   "marked as 'Completed'. This is likely premature. " # Changed 'Concluído' to 'Completed'
                                   "Considering checklist NOT complete to enforce population of actual sub-tasks.")
                    # Optional: Add a system message to guide the LLM for the next step.
                    # This requires self.memory to be accessible and a Message class.
                    # from app.schema import Message, Role # Ensure import if used
                    # self.memory.add_message(Message.system_message(
                    #    "Reminder: The decomposition task is only truly completed after the resulting subtasks "
                    #    "are added to the checklist and work on them has begun. Please add the subtasks now."
                    # ))
                    return False
            # NEW LOGIC END

            # Proceed with the original logic if the above condition isn't met
            # The manager.are_all_tasks_complete() method itself checks if all loaded tasks are 'Completed'. # Changed 'Concluído' to 'Completed'
            # It will correctly return False if there are tasks but not all are 'Completed'. # Changed 'Concluído' to 'Completed'
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
            final_result = {"success": False, "message": f"Failed to copy script to sandbox: {e_copy}", "status_code": "SANDBOX_COPY_FAILED"}
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
            final_result = {"success": True, "message": "Script executed successfully.", "stdout": stdout, "stderr": stderr, "exit_code": exit_code}
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
ANALYSIS_PROMPT_TEMPLATE = """You are a "Python Code Analyzer and Corrector".
Your task is to analyze a Python script that failed, along with its standard output (stdout) and standard error (stderr).
You MUST return a JSON object specifying a single tool to apply the correction and the parameters for that tool.

**Available Tools for Correction:**
1.  **`replace_code_block`**:
    *   Description: Replaces a block of code between `start_line` and `end_line` (inclusive, 1-indexed) with `new_content`.
    *   Parameters: `path` (string, file path - **DO NOT INCLUDE THIS PARAMETER, it will be added automatically**), `start_line` (integer), `end_line` (integer), `new_content` (string).
    *   Usage: Ideal for replacing entire functions, logical blocks, or larger sections of code.
2.  **`apply_diff_patch`**:
    *   Description: Applies a patch in unified diff format to the file.
    *   Parameters: `path` (string, file path - **DO NOT INCLUDE THIS PARAMETER**), `patch_content` (string, content of the diff).
    *   Usage: Good for multiple small changes, non-contiguous changes, or when diff logic is easier to express. The diff should be generated relative to the original script provided.
3.  **`ast_refactor`**:
    *   Description: Performs AST-based refactoring. Initial operation: `replace_function_body`.
    *   Parameters for `replace_function_body`: `path` (string - **DO NOT INCLUDE THIS PARAMETER**), `operation` (string, fixed: "replace_function_body"), `target_node_name` (string, function name), `new_code_snippet` (string, new function body, without the `def ...`).
    *   Usage: Safer for structural refactoring, such as replacing a function's body without affecting its signature or the rest of the file.
4.  **`format_python_code`**:
    *   Description: Formats Python code using Ruff/Black. Can fix simple syntax/indentation errors.
    *   Parameters: `code` (string, the full code to be formatted - **IMPORTANT: for this tool, instead of "path", provide the script content in the "code" parameter within "tool_params"**).
    *   Usage: Try this tool FIRST for SyntaxError or IndentationError errors. If the LLM is prompted after a formatter failure, do not suggest `format_python_code` again.

**Mandatory JSON Format for the Response:**
The response MUST be a parsable JSON string, containing an object with the following keys:
- "tool_to_use": string, the name of the chosen tool (e.g., "replace_code_block", "apply_diff_patch", "ast_refactor", "format_python_code").
- "tool_params": object, a dictionary containing the specific parameters for the chosen tool (DO NOT include "path" here, except for "format_python_code" where "code" is used instead of "path").
- "comment": string, a brief explanation of the error and the correction you are applying.

**JSON Response Examples:**

For `replace_code_block`:
```json
{
  "tool_to_use": "replace_code_block",
  "tool_params": {
    "start_line": 10,
    "end_line": 15,
    "new_content": "def my_corrected_function():\\n    return 'corrected'"
  },
  "comment": "The original 'my_function' had a logic error. Replacing it completely."
}
```

For `apply_diff_patch`:
```json
{
  "tool_to_use": "apply_diff_patch",
  "tool_params": {
    "patch_content": "--- a/original_script.py\\n+++ b/corrected_script.py\\n@@ -1,3 +1,3 @@\\n- error_line\\n+ corrected_line\\n  another_line\\n"
  },
  "comment": "Corrected a typo on line 1 and adjusted a variable on line 5 (example of diff)."
}
```

For `ast_refactor` (operation `replace_function_body`):
```json
{
  "tool_to_use": "ast_refactor",
  "tool_params": {
    "operation": "replace_function_body",
    "target_node_name": "my_function_with_error",
    "new_code_snippet": "  # New function body\\n  result = calculate_something()\\n  return result"
  },
  "comment": "The body of the function 'my_function_with_error' was rewritten to fix a calculation bug."
}
```

For `format_python_code` (if it's a syntax error and the auto-formatter hasn't been tried yet):
```json
{
  "tool_to_use": "format_python_code",
  "tool_params": {
    "code": "# Full script content here...\nprint('hello') # Example"
  },
  "comment": "Attempting to fix possible simple syntax/indentation error with the formatter."
}
```

**Important:**
- Choose ONLY ONE tool.
- Provide corrections in the EXACT JSON format specified above.
- If the script is fundamentally flawed and needs a complete rewrite that doesn't fit well into a single tool call, or if no correction is obvious, you MAY return a JSON with `"tool_to_use": null` and a comment explaining. E.g., `{"tool_to_use": null, "tool_params": {}, "comment": "The script is too broken, I suggest rewriting it based on the original task."}`.
- Analyze `stderr` carefully to identify the root cause of the error.
- The goal is to make the most appropriate correction using the most suitable tool.
- **DO NOT include the "path" parameter in "tool_params" for `replace_code_block`, `apply_diff_patch`, `ast_refactor`. It will be added automatically. For `format_python_code`, use the "code" parameter in `tool_params` to pass the script content.**

**Original Script with Error:**
```python
{script_content}
```

**Standard Output (stdout) from Failed Execution:**
```
{stdout}
```

**Standard Error (stderr) from Failed Execution:**
```
{stderr}
```

**Original Task the Script Was Trying to Perform:**
{original_task}

Now, provide your analysis and the tool and parameter suggestion in the specified JSON format.
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
                self.memory.add_message(Message.assistant_message("Please provide a task description for the self-coding cycle."))
                self.tool_calls = []
                return True
            logger.info(f"Triggering self-coding cycle for task: {task_description}")
            self.memory.add_message(Message.assistant_message(f"Starting self-coding cycle for: {task_description}. I will report the result."))
            cycle_result = await self._execute_self_coding_cycle(task_description)
            if cycle_result.get("status_code") == "SANDBOX_CREATION_FAILED":
                self.memory.add_message(Message.assistant_message(
                    f"Failed to execute self-coding cycle for '{task_description}'.\n"
                    f"Reason: Could not create the secure environment (sandbox) for code execution.\n"
                    f"Details: {cycle_result.get('details', 'Unknown error during sandbox creation.')}\n"
                    f"Please check if Docker is running and if the image '{config.sandbox.image_name}' is available or can be downloaded."
                ))
            elif cycle_result.get("status_code") == "SANDBOX_COPY_FAILED":
                self.memory.add_message(Message.assistant_message(
                    f"Failed to execute self-coding cycle for '{task_description}'.\n"
                    f"Reason: Could not copy the script to the secure environment (sandbox).\n"
                    f"Details: {cycle_result.get('message', 'Unknown error during copy to sandbox.')}"
                ))
            elif cycle_result.get("success"):
                success_message = f"Self-coding cycle completed successfully for '{task_description}'.\n\n"
                success_message += f"Script output (stdout):\n{cycle_result.get('stdout', 'No stdout output.')}\n"
                if cycle_result.get("workspace_listing"):
                    success_message += f"\nCurrent content of the main working directory ({config.workspace_root}):\n{cycle_result.get('workspace_listing')}\n"
                success_message += f"\nAny files mentioned as 'saved' or 'generated' by the script (and copied from sandbox /tmp, if applicable) should be visible above or directly in the {config.workspace_root} directory."
                self.memory.add_message(Message.assistant_message(success_message))
            else:
                error_details = cycle_result.get('stderr', cycle_result.get('last_execution_result', {}).get('stderr', 'No stderr output.'))
                self.memory.add_message(Message.assistant_message(
                    f"Self-coding cycle failed for '{task_description}'.\n"
                    f"Reason: {cycle_result.get('message', 'Unknown error.')}\n"
                    f"Last error output (stderr):\n{error_details}"
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
                logger.info(f"Expected artifact set to: {self._background_task_artifact_path} (Log file: {log_file})") # Translated
                    self.memory.add_message(Message.assistant_message(
                    f"Command '{actual_command}' started in background. "
                    f"Logs will be sent to '{os.path.basename(log_file)}' (located in {config.workspace_root}). "
                    f"Looking for the expected artifact '{self._background_task_expected_artifact}' in '{config.workspace_root}'. "
                    "I will monitor the progress."
                    ))
            except json.JSONDecodeError:
                logger.error("Error decoding JSON arguments for Bash when trying to start monitoring.") # Translated
            except Exception as e_parse:
                logger.error(f"Error processing bash command for monitoring: {e_parse}") # Translated

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
                    "Internal note: An attempt to terminate the task due to a failure was intercepted. " # Translated
                    "The user will be consulted before termination."
                ))
                if not self.tool_calls:
                     logger.info("No other tools planned besides the intercepted terminate(failure). Proceeding to failure feedback.") # Translated
                else:
                     logger.warning("Other tools were planned along with terminate(failure). This is unexpected. Failure feedback will occur after these tools.") # Translated

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
                logger.warning(f"Dependency script seems to have failed. Response: {last_tool_response.content}") # Translated
                self.memory.add_message(Message.assistant_message(
                    f"The script I tried to run as a dependency ('{self.tool_calls[0].function.name}') seems to have failed to generate the necessary file for '{os.path.basename(self._pending_script_after_dependency)}'. Error details: {last_tool_response.content}. I will not attempt to run the pending script." # Translated
                ))
            elif not expected_generated_file_name:
                logger.warning("Could not determine the expected file name from the dependency. Assuming generation failure.") # Translated
                self.memory.add_message(Message.assistant_message(
                    f"I could not determine which file the dependency script was supposed to generate for '{os.path.basename(self._pending_script_after_dependency)}'. I will not attempt to run the pending script." # Translated
                ))
            else:
                try:
                    expected_file_path = str(config.workspace_root / expected_generated_file_name)
                    editor = self.available_tools.get_tool(StrReplaceEditor().name)
                    await editor.execute(command="view", path=expected_file_path)
                    logger.info(f"Expected file '{expected_generated_file_name}' successfully generated by dependency.") # Translated
                    dependency_succeeded_and_file_generated = True
                except ToolError:
                    logger.warning(f"Dependency script executed, but expected file '{expected_generated_file_name}' was NOT found.") # Translated
                    self.memory.add_message(Message.assistant_message(
                        f"The dependency script was executed, but the expected file '{expected_generated_file_name}' for '{os.path.basename(self._pending_script_after_dependency)}' was not found. I will not attempt to run the pending script." # Translated
                    ))
                except Exception as e_check:
                    logger.error(f"Error checking file generated by dependency '{expected_generated_file_name}': {e_check}") # Translated
                    self.memory.add_message(Message.assistant_message(
                        f"An error occurred while checking if the expected file '{expected_generated_file_name}' was generated. I will not attempt to run the pending script." # Translated
                    ))

            if dependency_succeeded_and_file_generated:
                logger.info(f"Dependency script completed and file generated. Attempting to run pending script: {self._pending_script_after_dependency}") # Translated
                self.memory.add_message(Message.assistant_message(
                    f"The execution of the dependency script and generation of file '{expected_generated_file_name}' seem to have been successful. Now I will try to run the original script: {os.path.basename(self._pending_script_after_dependency)}." # Translated
                ))
                if self._original_tool_call_for_pending_script:
                    self.tool_calls = [self._original_tool_call_for_pending_script]
                else:
                    logger.error("Could not find the original tool_call for the pending script.") # Translated
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
                            logger.info(f"Script '{gen_script_name}' seems to generate its own input '{required_file}'. Not considering as dependency.") # Translated
                            continue
                        found_generating_script = gen_script_name
                        break
                if found_generating_script:
                    self.memory.add_message(Message.assistant_message(
                        f"The file '{required_file}' needed for '{os.path.basename(script_to_run_if_dependency_succeeds)}' was not found. " # Translated
                        f"I found that '{os.path.basename(found_generating_script)}' can generate it. I will try to run '{os.path.basename(found_generating_script)}' first."
                    ))
                    self._pending_script_after_dependency = script_to_run_if_dependency_succeeds
                    self._original_tool_call_for_pending_script = tool_call_to_check
                    new_tool_call_args = {"file_path": str(config.workspace_root / found_generating_script)}
                    self.tool_calls = [ToolCall(
                        id=str(uuid.uuid4()),
                        function=FunctionCall(name=SandboxPythonExecutor().name, arguments=json.dumps(new_tool_call_args))
                    )]
                    logger.info(f"Execution of '{os.path.basename(script_to_run_if_dependency_succeeds)}' postponed. Running dependency '{os.path.basename(found_generating_script)}' first.") # Translated
                else:
                    self.memory.add_message(Message.assistant_message(
                        f"The file '{required_file}' needed for '{os.path.basename(script_to_run_if_dependency_succeeds)}' was not found, and I did not identify a script in the workspace that generates it. " # Translated
                        "I will need you to provide this file or a script to generate it."
                    ))
                    self.tool_calls = []
                    logger.info(f"No generating script found for '{required_file}'. LLM should use AskHuman.") # Translated
        return result

    async def _analyze_python_script(self, script_path: str, script_content: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"Analyzing Python script: {script_path}") # Translated
        analysis = {"inputs": [], "outputs": [], "libraries": []}

        if not script_content:
            try:
                editor_tool = self.available_tools.get_tool(StrReplaceEditor().name)
                if not editor_tool:
                    logger.error("StrReplaceEditor tool not found for _analyze_python_script.") # Translated
                    return analysis
                script_content_result = await editor_tool.execute(command="view", path=script_path, view_range=[1, 200])
                if isinstance(script_content_result, str):
                    script_content = script_content_result
                else:
                    logger.error(f"Failed to read content of {script_path} for analysis: {script_content_result}") # Translated
                    return analysis
            except ToolError as e:
                logger.error(f"ToolError reading {script_path} for analysis: {e}") # Translated
                return analysis
            except Exception as e:
                logger.error(f"Unexpected error reading {script_path} for analysis: {e}") # Translated
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
             logger.info("Returning workspace analysis from cache.") # Translated
             return self._workspace_script_analysis_cache

        workspace_scripts_analysis: Dict[str, Dict[str, Any]] = {}
        editor_tool = self.available_tools.get_tool(StrReplaceEditor().name)
        if not editor_tool:
            logger.error("StrReplaceEditor tool not found for _analyze_workspace.") # Translated
            return workspace_scripts_analysis

        try:
            workspace_path_str = str(config.workspace_root)
            dir_listing_result = await editor_tool.execute(command="view", path=workspace_path_str)

            if isinstance(dir_listing_result, str):
                python_files = [line.strip() for line in dir_listing_result.splitlines() if line.strip().endswith(".py")]
                logger.info(f"Python scripts found in workspace ({workspace_path_str}): {python_files}") # Translated
                for script_name in python_files:
                    full_script_path = str(config.workspace_root / script_name)
                    workspace_scripts_analysis[script_name] = await self._analyze_python_script(full_script_path)
            else:
                logger.error(f"Failed to list workspace files for analysis: {dir_listing_result}") # Translated

        except ToolError as e:
            logger.error(f"ToolError listing workspace files for analysis: {e}") # Translated
        except Exception as e:
            logger.error(f"Unexpected error analyzing workspace: {e}") # Translated

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
                self.memory.add_message(Message.assistant_message("Could not find the PID file for cancellation; the script may have already finished.")) # Translated
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
                self.memory.add_message(Message.assistant_message(f"Invalid content in PID file ({self._current_sandbox_pid_file}). Cannot cancel.")) # Translated
                if hasattr(self, '_cleanup_sandbox_file') and callable(getattr(self, '_cleanup_sandbox_file')):
                     await self._cleanup_sandbox_file(self._current_sandbox_pid_file)
                self._current_sandbox_pid_file = None
                self._current_script_tool_call_id = None
                self._current_sandbox_pid = None
                return
            except Exception as e: # Catch other SANDBOX_CLIENT errors like permission issues or sandbox down
                logger.error(f"Error reading PID file {self._current_sandbox_pid_file}: {e}")
                self.memory.add_message(Message.assistant_message(f"Error reading PID file for cancellation: {e}")) # Translated
                # Do not clear _current_sandbox_pid_file here, as the file might still exist, just unreadable temporarily.
                # The original tool call might still complete and trigger proper cleanup via execute_tool's finally block.
                return

        if self._current_sandbox_pid is not None:
            try:
                kill_command = f"kill -SIGTERM {self._current_sandbox_pid}"
                logger.info(f"Attempting to execute kill command in sandbox: {kill_command}")
                # Add message before sending kill, so user sees it even if agent/sandbox has issues during the command
                self.memory.add_message(Message.assistant_message(f"Sending cancellation signal (SIGTERM) to process {self._current_sandbox_pid} in the sandbox...")) # Translated
                result = await SANDBOX_CLIENT.run_command(kill_command, timeout=10) # Using SIGTERM

                if result.get("exit_code") == 0:
                    logger.info(f"Successfully sent SIGTERM to PID {self._current_sandbox_pid}. Kill command stdout: '{result.get('stdout','').strip()}', stderr: '{result.get('stderr','').strip()}'")
                    # User message for successful signal send was already added.
                else:
                    # This can happen if the process already exited between PID read and kill command.
                    logger.warning(f"Kill command for PID {self._current_sandbox_pid} failed or PID not found. Exit code: {result.get('exit_code')}. Stderr: '{result.get('stderr','').strip()}'")
                    # self.memory.add_message(Message.assistant_message(f"Failed to send cancellation signal to script (PID: {self._current_sandbox_pid}), or script had already finished. Details: {result.get('stderr','').strip()}")) # Translated
                    # No need for another message if the previous one indicated an attempt. The log is sufficient.
            except Exception as e:
                logger.error(f"Exception while trying to kill PID {self._current_sandbox_pid}: {e}")
                self.memory.add_message(Message.assistant_message(f"Error trying to cancel script (PID: {self._current_sandbox_pid}): {e}")) # Translated
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
            logger.warning(f"User interaction tool '{user_interaction_tool_name}' not available. Continuing execution.") # Translated
            self.memory.add_message(Message.system_message(f"Periodic user interaction skipped: tool '{user_interaction_tool_name}' not found.")) # Translated
            return True

        checklist_content_str = "Checklist not found or empty." # Translated
        checklist_path = str(config.workspace_root / "checklist_principal_tarefa.md")
        local_file_op = LocalFileOperator()
        try:
            checklist_content_str = await local_file_op.read_file(checklist_path)
            if not checklist_content_str.strip():
                checklist_content_str = "Checklist found, but it is empty." # Translated
            logger.info(f"Checklist content read locally for self-analysis: {checklist_content_str[:200]}...") # Translated
        except ToolError as e_tool_error:
            logger.info(f"Checklist '{checklist_path}' not found (or error reading locally) for self-analysis: {str(e_tool_error)}. Using default message.") # Translated
        except Exception as e_checklist:
            logger.error(f"Unexpected error reading checklist locally for self-analysis: {str(e_checklist)}") # Translated
            checklist_content_str = f"Unexpected error reading checklist: {str(e_checklist)}" # Translated

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

        self_analysis_report = "Could not generate self-analysis report due to an internal error." # Translated
        try:
            logger.info("Initiating internal LLM call for self-analysis...") # Translated
            if hasattr(self, 'llm') and self.llm:
                 self_analysis_report = await self.llm.ask(messages=prompt_messages_list, stream=False) # Translated variable name
                 logger.info(f"Self-analysis report received from LLM: {self_analysis_report[:300]}...") # Translated variable name
            else:
                logger.error("LLM instance (self.llm) not available for self-analysis.") # Translated
        except Exception as e_llm_call:
            logger.error(f"Error during internal LLM call for self-analysis: {e_llm_call}") # Translated
            self_analysis_report = f"Could not generate self-analysis report due to an error: {e_llm_call}" # Translated variable name
        
        question_to_user = "" # Translated variable name
        if is_failure_scenario:
            last_llm_thought = ""
            if self.memory.messages and self.memory.messages[-1].role == Role.ASSISTANT:
                last_llm_thought = self.memory.messages[-1].content
            error_details_for_prompt = f"Error details (according to my last thought): {last_llm_thought}" if last_llm_thought else "I could not get specific error details from my internal processing." # Translated
            question_to_user = ( # Translated variable name
                f"I encountered a problem that prevents me from continuing the task as planned.\n"
                f"Self-Analysis Report (on the failure):\n{self_analysis_report}\n\n" # Translated variable name
                f"{error_details_for_prompt}\n\n"
                f"Would you like me to terminate the task now due to this difficulty?\n\n"
                f"Please respond with:\n"
                f"- 'yes, terminate' (to end the task with failure)\n"
                f"- 'no, try another approach: [your instructions]' (if you have a suggestion or want me to try something different)"
            )
        elif is_final_check:
            question_to_user = ( # Translated variable name
                f"All checklist items have been completed. Here is my final self-analysis report:\n{self_analysis_report}\n\n" # Translated variable name
                f"Are you satisfied with the result and do you want me to finalize the task?\n\n"
                f"Please respond with:\n"
                f"- 'yes' (to finalize the task successfully)\n"
                f"- 'review: [your instructions for review]' (if something needs to be adjusted before finalizing)"
            )
        else:
            question_to_user = ( # Translated variable name
                f"Here is my self-analysis and planning report:\n{self_analysis_report}\n\n" # Translated variable name
                f"Considering this, I have completed a cycle of {self.max_steps} steps (total steps taken: {self.current_step}).\n"
                f"Do you want me to continue for another {self.max_steps} steps (possibly following the suggested plan, if any)? Or do you prefer to stop or give me new instructions?\n\n"
                f"Please respond with:\n"
                f"- 'continue' (to proceed for another {self.max_steps} steps)\n"
                f"- 'stop' (to end the current task)\n"
                f"- 'change: [your new instructions]' (to provide a new direction)"
            )
        
        # Check for cancellable script before asking for user input in the general case
        if not is_failure_scenario and not is_final_check:
            if hasattr(self, '_current_sandbox_pid_file') and self._current_sandbox_pid_file:
                logger.info(f"Pause requested by user. Currently running script with PID file: {self._current_sandbox_pid_file}. Attempting cancellation.")
                # Assuming _initiate_sandbox_script_cancellation will be an async method
                # It should also ideally add a message to memory about its outcome.
                # For now, we add a generic message here.
                self.memory.add_message(Message.assistant_message("Attempting to cancel the script running in the sandbox due to pause request...")) # Translated
                if hasattr(self, '_initiate_sandbox_script_cancellation') and callable(getattr(self, '_initiate_sandbox_script_cancellation')):
                    await self._initiate_sandbox_script_cancellation()
                else:
                    logger.warning("_initiate_sandbox_script_cancellation method not found, cannot cancel script.")
                    self.memory.add_message(Message.assistant_message("WARNING: Script cancellation functionality not implemented in this agent.")) # Translated

        logger.info(f"Manus: Asking user for feedback with prompt: {question_to_user[:500]}...") # Translated variable name
        self.memory.add_message(Message.assistant_message(content=question_to_user)) # Translated variable name

        user_response_text = ""
        user_response_content_for_memory = ""
        try:
            tool_instance = self.available_tools.get_tool(user_interaction_tool_name)
            if tool_instance:
                user_response_content_from_tool = await tool_instance.execute(inquire=question_to_user) # Translated variable name
                if isinstance(user_response_content_from_tool, str):
                    user_response_content_for_memory = user_response_content_from_tool
                    user_response_text = user_response_content_from_tool.strip().lower()
                    self.memory.add_message(Message.user_message(content=user_response_content_for_memory))
                else:
                    logger.warning(f"Unexpected response from tool {user_interaction_tool_name}: {user_response_content_from_tool}") # Translated
                    user_response_content_for_memory = str(user_response_content_from_tool)
                    user_response_text = ""
                    self.memory.add_message(Message.user_message(content=user_response_content_for_memory))
            else:
                logger.error(f"Failed to get instance of tool {user_interaction_tool_name} again.") # Translated
                return True
        except Exception as e:
            logger.error(f"Error using tool '{user_interaction_tool_name}': {e}") # Translated
            self.memory.add_message(Message.system_message(f"Error during periodic user interaction: {e}. Continuing execution.")) # Translated
            return True

        if is_failure_scenario:
            if user_response_text == "yes, terminate": # Translated
                self.memory.add_message(Message.assistant_message("Understood. I will terminate the task now due to failure.")) # Translated
                self.tool_calls = [ToolCall(id=str(uuid.uuid4()), function=FunctionCall(name=Terminate().name, arguments='{"status": "failure", "message": "User consented to terminate due to unrecoverable failure."}'))] # Translated
                self.state = AgentState.TERMINATED
                self._just_resumed_from_feedback = False
                return False
            elif user_response_text.startswith("no, try another approach:"): # Translated
                new_instruction = user_response_content_for_memory.replace("no, try another approach:", "").strip() # Translated
                logger.info(f"Manus: User provided new instructions after failure: {new_instruction}") # Translated
                self.memory.add_message(Message.assistant_message(f"Understood. I will try the following approach: {new_instruction}")) # Translated
                self._just_resumed_from_feedback = True
                return True
            else:
                logger.info(f"Manus: User provided unrecognized input ('{user_response_text}') during failure check. Re-prompting.")
                self.memory.add_message(Message.assistant_message(f"I didn't understand your response ('{user_response_content_for_memory}'). Please use 'yes, terminate' or 'no, try another approach: [instructions]'.")) # Translated
                self._just_resumed_from_feedback = True
                return True
        elif is_final_check:
            if user_response_text == "yes": # Translated
                self.memory.add_message(Message.assistant_message("Great! I will finalize the task now with success.")) # Translated
                self.tool_calls = [ToolCall(id=str(uuid.uuid4()), function=FunctionCall(name=Terminate().name, arguments='{"status": "success", "message": "Task completed successfully with user approval."}'))] # Translated
                self.state = AgentState.TERMINATED
                self._just_resumed_from_feedback = False
                return False
            elif user_response_text.startswith("review:"): # Translated
                new_instruction = user_response_content_for_memory.replace("review:", "").strip() # Translated
                logger.info(f"Manus: User provided new instructions for final review: {new_instruction}") # Translated
                self.memory.add_message(Message.assistant_message(f"Understood. I will review based on your instructions: {new_instruction}")) # Translated
                self._just_resumed_from_feedback = True
                return True
            else:
                logger.info(f"Manus: User provided unrecognized input ('{user_response_text}') during final check. Re-prompting.")
                self.memory.add_message(Message.assistant_message(f"I didn't understand your response ('{user_response_content_for_memory}'). Please use 'yes' to finalize or 'review: [instructions]'.")) # Translated
                self._just_resumed_from_feedback = True
                return True
        else:
            if user_response_text == "stop": # Translated
                self.state = AgentState.USER_HALTED
                self._just_resumed_from_feedback = False
                return False
            elif user_response_text.startswith("change:"): # Translated
                new_instruction = user_response_content_for_memory.replace("change:", "").strip() # Translated
                logger.info(f"Manus: User provided new instructions: {new_instruction}") # Translated
                self.memory.add_message(Message.assistant_message(f"Understood. I will follow your new instructions: {new_instruction}")) # Translated
                self._just_resumed_from_feedback = True
                return True
            else: # Default to continue for any other input or empty input.
                if user_response_text == "continue": # Translated
                    logger.info("Manus: User chose to CONTINUE execution.")
                    self.memory.add_message(Message.assistant_message("Understood. Continuing with the task.")) # Translated
                elif not user_response_text and user_response_content_for_memory is not None : # Catches empty string if user_response_content_for_memory was populated
                     logger.info("Manus: User provided empty response, interpreted as 'CONTINUE'.")
                     self.memory.add_message(Message.assistant_message("Empty response received. Continuing with the task.")) # Translated
                else: # Catches any other non-empty, non-specific response
                     logger.info(f"Manus: User responded '{user_response_text}', interpreted as 'CONTINUE'.")
                     self.memory.add_message(Message.assistant_message(f"Response '{user_response_content_for_memory}' received. Continuing with the task.")) # Translated

                self._just_resumed_from_feedback = True # Set this so we don't immediately ask for feedback again
                return True
