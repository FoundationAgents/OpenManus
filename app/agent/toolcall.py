import asyncio
import json
from typing import Any, List, Optional, Union

from pydantic import Field

from app.config import config
from app.agent.react import ReActAgent
from app.exceptions import TokenLimitExceeded, AgentEnvironmentError
from app.logger import logger
from app.sandbox.client import SANDBOX_CLIENT
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice, Function, Role
from app.agent.critic_agent import CriticAgent
from app.core.environment_validator import EnvironmentValidator

from app.tool import CreateChatCompletion, Terminate, ToolCollection
from app.tool.base import ToolResult
from app.tool.file_operators import LocalFileOperator
from app.tool.code_formatter import FormatPythonCode
from app.tool.code_editor_tools import ReplaceCodeBlock, ApplyDiffPatch, ASTRefactorTool


TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class ToolCallAgent(ReActAgent):
    """Base agent class for handling tool/function calls with enhanced abstraction"""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = ToolCollection(
        CreateChatCompletion(), Terminate(), FormatPythonCode(), ReplaceCodeBlock(), ApplyDiffPatch(), ASTRefactorTool()
    )
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)
    _current_base64_image: Optional[str] = None
    critic_agent: Optional[CriticAgent] = None
    steps_since_last_critic_review: int = 0
    initial_user_prompt_for_critic: Optional[str] = None

    max_steps: int = 30
    max_observe: Optional[Union[int, bool]] = None

    def __init__(self, **data: Any):
        super().__init__(**data)
        if self.llm:
            self.critic_agent = CriticAgent(llm_client=self.llm)
        else:
            logger.warning("LLM não disponível para ToolCallAgent no momento da inicialização do CriticAgent.")
        self.initial_user_prompt_for_critic = None

    async def think(self) -> bool:
        if self.current_step == 1:
            checklist_filename = "checklist_principal_tarefa.md"
            checklist_path_str = str(config.workspace_root / checklist_filename)
            local_op = LocalFileOperator()
            checklist_exists = False
            try:
                checklist_exists = await local_op.exists(checklist_path_str)
            except Exception as e:
                logger.error(f"Error checking for checklist existence: {e}. Proceeding with LLM thought.")
                checklist_exists = False 

            if not checklist_exists:
                logger.info(f"Checklist file '{checklist_path_str}' not found or error during check at step 1. Enforcing creation.")
                initial_checklist_content = "- [Pendente] Decompor a solicitação do usuário e popular o checklist com as subtarefas."
                escaped_checklist_path_str = json.dumps(checklist_path_str)
                escaped_initial_checklist_content = json.dumps(initial_checklist_content)
                arguments_json_string = f'{{"command": "create", "path": {escaped_checklist_path_str}, "file_text": {escaped_initial_checklist_content}}}'
                forced_tool_call = ToolCall(
                    id="forced_checklist_creation_001",
                    function=Function(name="str_replace_editor", arguments=arguments_json_string)
                )
                self.tool_calls = [forced_tool_call]
                assistant_thought_content = "A primeira ação é criar o checklist da tarefa para organizar o trabalho."
                self.memory.add_message(
                    Message.from_tool_calls(content=assistant_thought_content, tool_calls=self.tool_calls)
                )
                return True

        if self.next_step_prompt:
            user_msg = Message.user_message(self.next_step_prompt)
            self.messages += [user_msg]

        try:
            response = await self.llm.ask_tool(
                messages=self.messages,
                system_msgs=(
                    [Message.system_message(self.system_prompt.format(directory=str(config.workspace_root)))]
                    if self.system_prompt
                    else None
                ),
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except ValueError:
            raise
        except Exception as e:
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(f"🚨 Token limit error (from RetryError): {token_limit_error}")
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False
            raise

        raw_openai_tool_calls = response.tool_calls if response and response.tool_calls else []
        converted_tool_calls = []
        if raw_openai_tool_calls:
            for openai_tc in raw_openai_tool_calls:
                if openai_tc.function:
                    app_function = Function(
                        name=openai_tc.function.name,
                        arguments=openai_tc.function.arguments
                    )
                    app_tc = ToolCall(
                        id=openai_tc.id,
                        type=openai_tc.type if openai_tc.type else "function",
                        function=app_function
                    )
                    converted_tool_calls.append(app_tc)
                else:
                    logger.warning(f"OpenAI tool_call (ID: {openai_tc.id}) missing function component, skipping conversion.")

        self.tool_calls = converted_tool_calls
        tool_calls = self.tool_calls
        content = response.content if response and response.content else ""

        logger.info(f"✨ {self.name}'s thoughts: {content}")
        logger.info(f"🛠️ {self.name} selected {len(self.tool_calls) if self.tool_calls else 0} tools to use")
        if self.tool_calls:
            logger.info(f"🧰 Tools being prepared: {[call.function.name for call in self.tool_calls]}")
            if self.tool_calls:
                 logger.info(f"🔧 Tool arguments: {self.tool_calls[0].function.arguments}")

        try:
            if response is None:
                raise RuntimeError("No response received from the LLM")

            if self.tool_choices == ToolChoice.NONE:
                if tool_calls:
                    logger.warning(f"🤔 Hmm, {self.name} tried to use tools when they weren't available!")
                if content:
                    self.memory.add_message(Message.assistant_message(content))
                    return True
                return False

            assistant_msg = (
                Message.from_tool_calls(content=content, tool_calls=self.tool_calls)
                if self.tool_calls
                else Message.assistant_message(content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True

            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(content)

            return bool(self.tool_calls)
        except Exception as e:
            logger.error(f"🚨 Oops! The {self.name}'s thinking process hit a snag: {e}")
            self.memory.add_message(Message.assistant_message(f"Error encountered while processing: {str(e)}"))
            return False

    async def act(self) -> str:
        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)
            return self.messages[-1].content or "No content or commands to execute"

        results = []
        for command in self.tool_calls:
            self._current_base64_image = None
            result = await self.execute_tool(command)
            if self.max_observe and isinstance(result, str):
                result = result[: self.max_observe]
            logger.info(f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}")
            tool_msg = Message.tool_message(
                content=result,
                tool_call_id=command.id,
                name=command.function.name,
                base64_image=self._current_base64_image,
            )
            self.memory.add_message(tool_msg)
            results.append(result)
        return "\n\n".join(results)

    async def execute_tool(self, command: ToolCall) -> str:
        from app.tool.sandbox_python_executor import SandboxPythonExecutor

        if not command:
            logger.error("execute_tool: Command object is None.")
            return "Error: Invalid command object (None)."
        if not isinstance(command, ToolCall):
            logger.error(f"execute_tool: Command object is not a ToolCall instance, got {type(command)}.")
            return f"Error: Invalid command object type ({type(command)})."

        current_function = command.function
        if not current_function:
            logger.error(f"execute_tool: command.function is None for command ID {command.id}.")
            return "Error: Command function is None."
        if not isinstance(current_function, Function):
            logger.error(f"execute_tool: command.function is not a Function instance for command ID {command.id}, got {type(current_function)}.")
            return f"Error: Invalid command function type ({type(current_function)})."

        name = ""
        try:
            name = current_function.name
            if not name:
                logger.error(f"execute_tool: command.function.name is None or empty for command ID {command.id}.")
                return "Error: Command function name is missing or empty."
        except AttributeError as e_name_access:
            logger.error(f"execute_tool: AttributeError while accessing command.function.name for command ID {command.id}. Error: {e_name_access}", exc_info=True)
            return "Error: Failed to access function name due to AttributeError."
        except Exception as e_general_name_access:
            logger.error(f"execute_tool: Unexpected error while accessing command.function.name for command ID {command.id}. Error: {e_general_name_access}", exc_info=True)
            return "Error: Unexpected error accessing function name."

        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        try:
            args = json.loads(command.function.arguments or "{}")
            if name == "str_replace_editor":
                if 'path' not in args and 'path_absoluto' in args:
                    args['path'] = args.pop('path_absoluto')
                elif 'path' not in args and 'caminho_completo_do_arquivo' in args:
                    args['path'] = args.pop('caminho_completo_do_arquivo')
                elif 'path' not in args and 'script_internal_file_path' in args:
                    args['path'] = args.pop('script_internal_file_path')

            logger.info(f"[TOOL_START] Activating tool '{name}' with args: {args}")
            tool_output = await self.available_tools.execute(name=name, tool_input=args)
            logger.info(f"[TOOL_END] Tool '{name}' executed successfully.")

            if name == SandboxPythonExecutor().name:
                if isinstance(tool_output, ToolResult):
                    if tool_output.error:
                        logger.warning(f"SandboxPythonExecutor returned an error: {tool_output.error}. Not expecting pid_file_path.")
                    elif isinstance(tool_output.output, dict) and "pid_file_path" in tool_output.output:
                        self._current_sandbox_pid_file = tool_output.output["pid_file_path"]
                        self._current_script_tool_call_id = command.id
                        self._current_sandbox_pid = None
                        logger.info(f"Stored PID file path '{self._current_sandbox_pid_file}' for tool call ID '{command.id}'.")
                    else:
                        logger.warning(
                            f"Tool {name} (ToolResult) did not contain 'pid_file_path' in its 'output' dictionary "
                            f"or 'output' was not a dictionary. Output: {tool_output.output}"
                        )
                else:
                    logger.error(f"SandboxPythonExecutor returned an unexpected type: {type(tool_output)}, esperava ToolResult.")

            await self._handle_special_tool(name=name, result=tool_output)

            current_output_str = ""
            observation = ""

            if isinstance(tool_output, ToolResult):
                if tool_output.base64_image:
                    self._current_base64_image = tool_output.base64_image

                if tool_output.error:
                    current_output_str = f"Error: {tool_output.error}"
                    if tool_output.output is not None:
                        output_detail = json.dumps(tool_output.output) if isinstance(tool_output.output, dict) else str(tool_output.output)
                        current_output_str += f"\nAdditional output: {output_detail}"
                elif tool_output.output is not None:
                    if isinstance(tool_output.output, dict):
                        current_output_str = json.dumps(tool_output.output)
                    else:
                        current_output_str = str(tool_output.output)
                # else current_output_str remains "" (empty string)

                if current_output_str:
                    observation = f"Observed output of cmd `{name}` executed:\n{current_output_str}"
                else:
                    observation = f"Cmd `{name}` completed with no observable output or error."
                # Explicit return for ToolResult case
                return observation

            # This elif will only be hit if tool_output is not a ToolResult
            elif isinstance(tool_output, dict):
                self._current_base64_image = None
                try:
                    current_output_str = json.dumps(tool_output)
                    observation = f"Observed output of cmd `{name}` executed (dict converted to JSON):\n{current_output_str}"
                except TypeError as e:
                    logger.error(f"Falha ao serializar a saída do dicionário da ferramenta '{name}' para JSON: {e}. Usando str() como fallback.")
                    current_output_str = str(tool_output)
                    observation = f"Observed output of cmd `{name}` executed (converted from {type(tool_output)} using str()):\n{current_output_str}"
                return observation # Explicit return for dict case

            elif isinstance(tool_output, str):
                self._current_base64_image = None
                current_output_str = tool_output
                if current_output_str:
                    observation = f"Observed output of cmd `{name}` executed:\n{current_output_str}"
                else:
                    observation = f"Cmd `{name}` completed with no observable string output."
                return observation # Explicit return for str case

            else: # Fallback for any other unhandled types
                logger.warning(f"Tool '{name}' returned an unhandled type: {type(tool_output)}. Converting to string using str().")
                self._current_base64_image = None
                current_output_str = str(tool_output)
                observation = f"Observed output of cmd `{name}` executed (converted from {type(tool_output)} using str()):\n{current_output_str}"
                return observation

        except json.JSONDecodeError:
            logger.error(f"[TOOL_FAIL] Tool '{name}' failed: Invalid JSON arguments.")
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            logger.error(
                f"📝 Oops! The arguments for '{name}' don't make sense - invalid JSON, arguments:{command.function.arguments}"
            )
            return f"Error: {error_msg}"
        except Exception as e:
            logger.error(f"[TOOL_FAIL] Tool '{name}' failed with exception: {str(e)}")
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {str(e)}"
            logger.exception(error_msg)
            return f"Error: {error_msg}"
        finally:
            if hasattr(self, '_current_script_tool_call_id') and self._current_script_tool_call_id == command.id:
                if hasattr(self, '_cleanup_sandbox_file') and callable(getattr(self, '_cleanup_sandbox_file')):
                    await self._cleanup_sandbox_file(self._current_sandbox_pid_file)
                else:
                    logger.warning(f"Agent {self.name} does not have a _cleanup_sandbox_file method. PID file {self._current_sandbox_pid_file} may not be cleaned if it exists.")

                logger.info(f"Clearing PID tracking for tool call ID '{command.id}'.")
                self._current_sandbox_pid = None
                self._current_sandbox_pid_file = None
                self._current_script_tool_call_id = None

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        if not self._is_special_tool(name):
            return
        if self._should_finish_execution(name=name, result=result, **kwargs):
            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        return True

    def _is_special_tool(self, name: str) -> bool:
        return name.lower() in [n.lower() for n in self.special_tool_names]

    async def cleanup(self):
        logger.info(f"🧹 Cleaning up resources for agent '{self.name}'...")
        for tool_name, tool_instance in self.available_tools.tool_map.items():
            if hasattr(tool_instance, "cleanup") and asyncio.iscoroutinefunction(
                tool_instance.cleanup
            ):
                try:
                    logger.debug(f"🧼 Cleaning up tool: {tool_name}")
                    await tool_instance.cleanup()
                except Exception as e:
                    logger.error(f"🚨 Error cleaning up tool '{tool_name}': {str(e)}")
        logger.info(f"✨ Cleanup complete for agent '{self.name}'.")

    async def run(self, request: Optional[str] = None) -> str:
        CRITIC_REVIEW_INTERVAL = 5
        try:
            if self.state == AgentState.IDLE or self.current_step == 0:
                logger.info(f"[{self.name}] Executando validação de pré-execução do ambiente...")
                validator = EnvironmentValidator(agent_name=self.name)
                env_ok, error_messages = await validator.run_all_checks()
                if not env_ok:
                    consolidated_error_msg = (
                        f"Validação de pré-execução do ambiente falhou para o agente '{self.name}'. "
                        "Por favor, verifique os erros e tente novamente.\n" + "\n".join(error_messages)
                    )
                    logger.error(consolidated_error_msg)
                    self.memory.add_message(Message.system_message(consolidated_error_msg))
                    self.state = AgentState.ERROR
                    raise AgentEnvironmentError(consolidated_error_msg)

            if self.state == AgentState.IDLE:
                if request:
                    self.update_memory("user", request)
                    if self.initial_user_prompt_for_critic is None:
                        self.initial_user_prompt_for_critic = request
                self.state = AgentState.RUNNING
            elif self.state == AgentState.AWAITING_USER_FEEDBACK:
                if request:
                    self.update_memory("user", request)
                elif not self.initial_user_prompt_for_critic:
                    first_user_msg = next((m for m in self.memory.messages if m.role == Role.USER), None)
                    if first_user_msg:
                        self.initial_user_prompt_for_critic = first_user_msg.content
                self.state = AgentState.RUNNING
            elif self.state == AgentState.RUNNING:
                if request:
                    self.update_memory("user", request)
                elif not self.initial_user_prompt_for_critic:
                    first_user_msg = next((m for m in self.memory.messages if m.role == Role.USER), None)
                    if first_user_msg:
                        self.initial_user_prompt_for_critic = first_user_msg.content
            else:
                logger.error(f"Run method called on agent in an unstartable/unresumable state: {self.state.value}. Raising RuntimeError.")
                raise RuntimeError(f"Cannot run/resume agent from state: {self.state.value}")

            results: List[str] = []
            if self.current_step == 0:
                 self.steps_since_last_critic_review = 0

            while self.state == AgentState.RUNNING:
                async with self.state_context(AgentState.RUNNING):
                    while self.state not in [AgentState.FINISHED, AgentState.ERROR, AgentState.USER_HALTED, AgentState.USER_PAUSED]:
                        self.current_step += 1
                        self.steps_since_last_critic_review += 1

                        if hasattr(self, 'user_pause_requested_event') and self.user_pause_requested_event.is_set():
                            self.user_pause_requested_event.clear()
                            self.state = AgentState.USER_PAUSED
                            break

                        if await self.should_request_feedback():
                            self.state = AgentState.AWAITING_USER_FEEDBACK
                            break

                        if self.state in [AgentState.FINISHED, AgentState.ERROR, AgentState.USER_HALTED, AgentState.AWAITING_USER_FEEDBACK]:
                            break

                        if self.critic_agent and self.steps_since_last_critic_review >= CRITIC_REVIEW_INTERVAL:
                            logger.info(f"[{self.name}] Agente Crítico ativado na etapa {self.current_step} (total) / {self.steps_since_last_critic_review} (desde última revisão).")
                            current_plan_markdown = "Plano não disponível para o crítico."
                            try:
                                checklist_manager = getattr(self, 'checklist_manager', None)
                                if checklist_manager and hasattr(checklist_manager, 'get_tasks_as_markdown'):
                                    current_plan_markdown = await checklist_manager.get_tasks_as_markdown()
                                elif hasattr(self, '_is_checklist_complete'):
                                    local_op = LocalFileOperator()
                                    checklist_path = str(config.workspace_root / "checklist_principal_tarefa.md")
                                    if await local_op.exists(checklist_path):
                                        current_plan_markdown = await local_op.read_file(checklist_path)
                                    else:
                                        current_plan_markdown = "Checklist principal ('checklist_principal_tarefa.md') não encontrado."
                            except Exception as e_plan_read:
                                logger.warning(f"[{self.name}] Não foi possível obter o plano detalhado para o Agente Crítico: {e_plan_read}")

                            recent_tool_action_results = []
                            lookback_messages_count = self.steps_since_last_critic_review * 2 + 5
                            for msg in reversed(self.memory.messages[-lookback_messages_count:]):
                                if msg.role == Role.TOOL and hasattr(msg, 'name') and hasattr(msg, 'content') and hasattr(msg, 'tool_call_id'):
                                    recent_tool_action_results.append({
                                        "name": msg.name,
                                        "content": msg.content,
                                        "tool_call_id": msg.tool_call_id
                                    })
                                if len(recent_tool_action_results) >= CRITIC_REVIEW_INTERVAL + 2:
                                    break
                            recent_tool_action_results.reverse()

                            critic_feedback_text, critic_redirect_suggestion = self.critic_agent.review_plan_and_progress(
                                current_plan_markdown=current_plan_markdown,
                                initial_user_prompt=self.initial_user_prompt_for_critic,
                                messages=[msg.model_dump() for msg in self.memory.messages[-10:]],
                                tool_results=recent_tool_action_results,
                                current_step=self.current_step,
                                steps_since_last_review=self.steps_since_last_critic_review
                            )
                            self.memory.add_message(Message.system_message(f"Feedback do Agente Crítico: {critic_feedback_text}"))
                            logger.info(f"[{self.name}] Feedback do Agente Crítico: {critic_feedback_text.splitlines()[0]}...")

                            if critic_redirect_suggestion and isinstance(critic_redirect_suggestion, dict):
                                critic_clarification = critic_redirect_suggestion.get("clarification", "Nenhuma clarificação adicional do crítico.")
                                self.memory.add_message(Message.system_message(f"ALERTA DO CRÍTICO: {critic_clarification}"))
                                logger.info(f"[{self.name}] ALERTA DO CRÍTICO (Clarificação): {critic_clarification}")
                                action_type = critic_redirect_suggestion.get("action_type")
                                details = critic_redirect_suggestion.get("details", {})
                                if action_type == "MODIFY_PLAN" and "task_description" in details:
                                    add_task_tool_name = "add_checklist_task"
                                    if self.available_tools.get_tool(add_task_tool_name):
                                        try:
                                            add_task_args = {"description": details["task_description"], "priority": details.get("priority", "normal"), "status": "Pendente"}
                                            add_task_call = ToolCall(id=f"critic_mod_plan_{self.current_step}", function=Function(name=add_task_tool_name, arguments=json.dumps(add_task_args)))
                                            logger.info(f"[{self.name}] Crítico sugeriu MODIFY_PLAN. Tentando adicionar tarefa via {add_task_tool_name} com args: {add_task_args}")
                                            add_task_result_obs = await self.execute_tool(add_task_call)
                                            self.memory.add_message(Message.tool_message(content=add_task_result_obs, tool_call_id=add_task_call.id, name=add_task_tool_name))
                                            self.memory.add_message(Message.system_message(f"Feedback do Agente Crítico: Tarefa '{details['task_description']}' foi (tentativamente) adicionada ao plano conforme sugestão do crítico."))
                                        except Exception as e_critic_add_task:
                                            logger.error(f"[{self.name}] Erro ao tentar adicionar tarefa sugerida pelo crítico: {e_critic_add_task}")
                                            self.memory.add_message(Message.system_message(f"ALERTA DO CRÍTICO: Falha ao tentar adicionar tarefa '{details['task_description']}' ao plano via ferramenta, conforme sugestão do crítico."))
                                    else:
                                        self.memory.add_message(Message.system_message(f"ALERTA DO CRÍTICO: Sugestão para modificar o plano: Adicionar tarefa '{details['task_description']}'. A ferramenta '{add_task_tool_name}' não está diretamente disponível. O agente principal deve considerar esta sugestão."))
                                elif action_type == "REQUEST_HUMAN_INPUT" and "question" in details:
                                    ask_human_tool_name = "ask_human"
                                    self.memory.add_message(Message.system_message(f"ALERTA DO CRÍTICO: É crucial obter input humano. Por favor, considere usar a ferramenta '{ask_human_tool_name}' com a seguinte pergunta: {details['question']}"))
                                elif action_type == "SUGGEST_ALTERNATIVE_TOOL" and "alternative_tool_name" in details:
                                    self.memory.add_message(Message.system_message(f"ALERTA DO CRÍTICO: Considere usar a ferramenta '{details['alternative_tool_name']}' com argumentos aproximados: {details.get('alternative_tool_args', {})} em vez de '{details.get('failed_tool', 'a ferramenta anterior')}'. O agente principal deve avaliar e decidir sobre esta sugestão."))
                            self.steps_since_last_critic_review = 0

                        step_result = await self.step()
                        results.append(f"Step {self.current_step}: {step_result}")

                        if self.tool_calls and self.memory.messages:
                            last_executed_tool_call = self.tool_calls[0]
                            critical_actions_map = {
                                "reset_current_task_checklist": {
                                    "verification_tool": "view_checklist",
                                    "confirmation_message_template": "[SISTEMA EXECUTOR]: Ação crítica '{action_name}' foi executada. Sua próxima ação DEVE ser verificar o resultado. Use a ferramenta '{verification_tool}' para confirmar que o checklist está vazio antes de prosseguir."
                                }
                            }
                            last_tool_message = next((msg for msg in reversed(self.memory.messages) if msg.role == Role.TOOL and msg.tool_call_id == last_executed_tool_call.id), None)
                            if last_tool_message and last_tool_message.name in critical_actions_map:
                                action_details = critical_actions_map[last_tool_message.name]
                                if "Error:" not in last_tool_message.content:
                                    confirmation_prompt = action_details["confirmation_message_template"].format(action_name=last_tool_message.name, verification_tool=action_details["verification_tool"])
                                    self.memory.add_message(Message.system_message(confirmation_prompt))
                                    logger.info(f"[{self.name}] Ação Crítica '{last_tool_message.name}' executada. Injetando prompt de confirmação: {confirmation_prompt}")
                                else:
                                    logger.warning(f"[{self.name}] Ação Crítica '{last_tool_message.name}' parece ter falhado. Não injetando prompt de confirmação. Resultado: {last_tool_message.content}")

                        if self.is_stuck():
                            self.handle_stuck_state()

                if self.state == AgentState.AWAITING_USER_FEEDBACK: break
                elif self.state == AgentState.USER_PAUSED: break
                if self.state not in [AgentState.RUNNING]: break

            if self.state == AgentState.USER_HALTED: pass
            elif self.state == AgentState.AWAITING_USER_FEEDBACK: pass
            elif self.state == AgentState.USER_PAUSED: pass
            elif self.current_step >= self.max_steps and self.max_steps > 0: self.state = AgentState.FINISHED
            elif not self.tool_calls and self.state == AgentState.RUNNING:
                last_message = self.memory.messages[-1] if self.memory.messages else None
                if last_message and last_message.role == Role.ASSISTANT and not last_message.tool_calls and last_message.content:
                    logger.info("Agente terminou de pensar e não produziu novas chamadas de ferramenta. Considerando como FINISHED.")
                    self.state = AgentState.FINISHED
                elif self.state == AgentState.RUNNING:
                    logger.info("Agente no estado RUNNING sem novas tool_calls. Considerando como FINISHED.")
                    self.state = AgentState.FINISHED
            elif self.state == AgentState.RUNNING: self.state = AgentState.FINISHED
            elif self.state == AgentState.ERROR: pass
            elif self.state == AgentState.FINISHED: pass
            else: logger.error(f"Execution ended with an unexpected or unhandled state: {self.state.value} at step {self.current_step}. Review agent logic.")

            final_summary = f"Execution concluded. Final state: {self.state.value}, Current step: {self.current_step}."
            results.append(final_summary)
            return "\n".join(results) if results else "No steps executed or execution ended."

        except AgentEnvironmentError as env_err:
            logger.error(f"[{self.name}] Saindo devido a AgentEnvironmentError: {env_err}")
            raise
        finally:
            await self.cleanup()
            if hasattr(SANDBOX_CLIENT, 'cleanup') and callable(SANDBOX_CLIENT.cleanup):
                 await SANDBOX_CLIENT.cleanup()
            logger.info(f"ToolCallAgent run method finished for agent '{self.name}'. Final state: {self.state.value}")

# Note: The traceback points to line 564 and mentions "```".
# This often means a markdown code block delimiter was left in the Python code.
# Assuming the "```" is the actual content on or starting at line 564 causing the error.
# If it's part of a larger comment or string, the fix might involve more lines.
# For now, this attempts to remove a standalone "```" or comment it out if it's on its own line.
# If the "```" is part of a multi-line string that's causing the issue, this simple replacement might not be enough.
# A more robust fix would be to see the surrounding lines.

# Given the repeated nature of this error and the `git pull` behavior,
# it's highly likely the issue is in the remote branch being pulled.
# The local fix applied by the agent might be correct, but it's being overwritten.
