import asyncio
import json
from typing import Any, List, Optional, Union

from pydantic import Field

from app.config import config
from app.agent.react import ReActAgent
from app.config import config # Added
from app.exceptions import TokenLimitExceeded
from app.logger import logger
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice, Function

from app.tool import CreateChatCompletion, Terminate, ToolCollection
from app.tool.base import ToolResult # Added
from app.tool.file_operators import LocalFileOperator # Added
from app.tool.code_formatter import FormatPythonCode # Added
from app.tool.code_editor_tools import ReplaceCodeBlock, ApplyDiffPatch, ASTRefactorTool # Modified


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
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)
    _current_base64_image: Optional[str] = None

    max_steps: int = 30
    max_observe: Optional[Union[int, bool]] = None

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        if self.current_step == 1: # current_step is 1 for the first proper thinking step
            checklist_filename = "checklist_principal_tarefa.md"
            # config.workspace_root is a Path object, ensure checklist_path is a string if tools expect strings
            checklist_path_str = str(config.workspace_root / checklist_filename)
            
            local_op = LocalFileOperator()
            checklist_exists = False # Default to not existing
            try:
                # Use a blocking call to os.path.exists for simplicity here, or make LocalFileOperator().exists() non-async
                # For now, let's assume we can await it. If not, this needs adjustment.
                # Based on file_operators.py, exists is async.
                checklist_exists = await local_op.exists(checklist_path_str)
            except Exception as e:
                logger.error(f"Error checking for checklist existence: {e}. Proceeding with LLM thought.")
                # If error checking existence, better to let LLM try to create it or decide,
                # rather than falsely assuming it exists or blocking the flow.
                # For this specific logic, we want to *force* creation if unsure or error.
                # So, if an error occurs, we'll treat it as "doesn't exist" to trigger creation.
                checklist_exists = False 

            if not checklist_exists:
                logger.info(f"Checklist file '{checklist_path_str}' not found or error during check at step 1. Enforcing creation.")
                
                initial_checklist_content = "- [Pendente] Decompor a solicitação do usuário e popular o checklist com as subtarefas."
                
                # Manually construct the JSON string for arguments
                # Manually construct the JSON string for arguments
                # Ensure checklist_path_str and initial_checklist_content are properly escaped for JSON
                escaped_checklist_path_str = json.dumps(checklist_path_str)
                escaped_initial_checklist_content = json.dumps(initial_checklist_content)

                arguments_json_string = f'{{"command": "create", "path": {escaped_checklist_path_str}, "file_text": {escaped_initial_checklist_content}}}'
                
                forced_tool_call = ToolCall(
                    id="forced_checklist_creation_001", # Static ID for this specific forced call
                    function=Function( 
                        name="str_replace_editor",
                        arguments=arguments_json_string # Use the manually constructed string
                    )
                    # type="function" # type is implicitly function for ToolCall
                )
                
                self.tool_calls = [forced_tool_call]
                
                assistant_thought_content = "A primeira ação é criar o checklist da tarefa para organizar o trabalho."
                self.memory.add_message(
                    Message.from_tool_calls(content=assistant_thought_content, tool_calls=self.tool_calls)
                )
                
                return True # Indicates that an action (the forced tool call) is ready

        if self.next_step_prompt:
            user_msg = Message.user_message(self.next_step_prompt)
            self.messages += [user_msg]

        try:
            # Get response with tool options
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
            # Check if this is a RetryError containing TokenLimitExceeded
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False
            raise

        # Imports no topo do arquivo já devem existir:
        # from app.schema import ToolCall, Function

        # ... dentro do método think() ...

        raw_openai_tool_calls = response.tool_calls if response and response.tool_calls else []
        converted_tool_calls = []
        if raw_openai_tool_calls:
            for openai_tc in raw_openai_tool_calls:
                if openai_tc.function: # Verificar se function não é None
                    app_function = Function( # Usando o Function de app.schema
                        name=openai_tc.function.name,
                        arguments=openai_tc.function.arguments
                    )
                    app_tc = ToolCall( # Usando o ToolCall de app.schema
                        id=openai_tc.id,
                        type=openai_tc.type if openai_tc.type else "function", # Default type to "function"
                        function=app_function
                    )
                    converted_tool_calls.append(app_tc)
                else:
                    # Logar um aviso se uma tool call do OpenAI não tiver a parte da função
                    logger.warning(f"OpenAI tool_call (ID: {openai_tc.id}) missing function component, skipping conversion.")

        self.tool_calls = converted_tool_calls
        # A variável local 'tool_calls' também pode ser atualizada se for usada posteriormente no método,
        # mas self.tool_calls é o principal. Para consistência:
        tool_calls = self.tool_calls

        content = response.content if response and response.content else ""

        # Log response info (manter esta parte)
        logger.info(f"✨ {self.name}'s thoughts: {content}")
        # Note: self.name aqui é o nome do ToolCallAgent ("toolcall"), não do Manus.
        # Isso pode ser confuso no log, mas é o comportamento existente.
        logger.info(
            f"🛠️ {self.name} selected {len(self.tool_calls) if self.tool_calls else 0} tools to use"
        )
        if self.tool_calls: # Usar self.tool_calls que agora é do tipo correto
            logger.info(
                f"🧰 Tools being prepared: {[call.function.name for call in self.tool_calls]}"
            )
            # Adicionar uma verificação para self.tool_calls não estar vazio antes de acessar [0]
            if self.tool_calls:
                 logger.info(f"🔧 Tool arguments: {self.tool_calls[0].function.arguments}")

        try:
            if response is None:
                raise RuntimeError("No response received from the LLM")

            # Handle different tool_choices modes
            if self.tool_choices == ToolChoice.NONE:
                if tool_calls:
                    logger.warning(
                        f"🤔 Hmm, {self.name} tried to use tools when they weren't available!"
                    )
                if content:
                    self.memory.add_message(Message.assistant_message(content))
                    return True
                return False

            # Create and add assistant message
            assistant_msg = (
                Message.from_tool_calls(content=content, tool_calls=self.tool_calls)
                if self.tool_calls
                else Message.assistant_message(content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True  # Will be handled in act()

            # For 'auto' mode, continue with content if no commands but content exists
            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(content)

            return bool(self.tool_calls)
        except Exception as e:
            logger.error(f"🚨 Oops! The {self.name}'s thinking process hit a snag: {e}")
            self.memory.add_message(
                Message.assistant_message(
                    f"Error encountered while processing: {str(e)}"
                )
            )
            return False

    async def act(self) -> str:
        """Execute tool calls and handle their results"""
        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)

            # Return last message content if no tool calls
            return self.messages[-1].content or "No content or commands to execute"

        results = []
        for command in self.tool_calls:
            # Reset base64_image for each tool call
            self._current_base64_image = None

            result = await self.execute_tool(command)

            if self.max_observe:
                result = result[: self.max_observe]

            logger.info(
                f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}"
            )

            # Add tool response to memory
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
        """Execute a single tool call with robust error handling"""
        # Import SandboxPythonExecutor here to check its name
        # This is a bit of a workaround for circular dependency or module loading issues
        # if SandboxPythonExecutor were imported at the top level of manus.py for type hinting
        # and toolcall.py also needs it for name comparison.
        # A better solution might be to use a string literal for the name or a shared constant.
        from app.tool.sandbox_python_executor import SandboxPythonExecutor

        # Import Function and ToolCall if not already available at the top of the file for isinstance checks
        # from app.schema import Function, ToolCall # Ensure this is appropriately placed if needed

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
        # Ensure app.schema.Function is imported if you are using it for isinstance check.
        # Assuming Function is already imported from app.schema at the top of the file.
        if not isinstance(current_function, Function):
            logger.error(f"execute_tool: command.function is not a Function instance for command ID {command.id}, got {type(current_function)}.")
            return f"Error: Invalid command function type ({type(current_function)})."

        name_to_be_used = None # Initialize to ensure it's clear if not set
        try:
            name_to_be_used = current_function.name
            if not name_to_be_used:
                logger.error(f"execute_tool: command.function.name is None or empty for command ID {command.id}.")
                return "Error: Command function name is missing or empty."
        except AttributeError as e_name_access:
            logger.error(f"execute_tool: AttributeError while accessing command.function.name for command ID {command.id}. Function object was: {str(current_function)}. Error: {e_name_access}", exc_info=True)
            return "Error: Failed to access function name due to AttributeError."
        except Exception as e_general_name_access: # Catch any other unexpected error during name access
            logger.error(f"execute_tool: Unexpected error while accessing command.function.name for command ID {command.id}. Function object was: {str(current_function)}. Error: {e_general_name_access}", exc_info=True)
            return "Error: Unexpected error accessing function name."

        # Use 'name_to_be_used' from this point onwards instead of just 'name' for clarity
        name = name_to_be_used
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        try:
            # Parse arguments
            args = json.loads(command.function.arguments or "{}")

            # Handle path argument aliasing for str_replace_editor
            if name == "str_replace_editor":
                if 'path' not in args and 'path_absoluto' in args:
                    args['path'] = args.pop('path_absoluto')
                    logger.info(f"Aliased 'path_absoluto' to 'path' for str_replace_editor call.")
                elif 'path' not in args and 'caminho_completo_do_arquivo' in args:
                    args['path'] = args.pop('caminho_completo_do_arquivo')
                    logger.info(f"Aliased 'caminho_completo_do_arquivo' to 'path' for str_replace_editor call.")
                elif 'path' not in args and 'script_internal_file_path' in args: # New condition
                    args['path'] = args.pop('script_internal_file_path')
                    logger.info(f"Aliased 'script_internal_file_path' to 'path' for str_replace_editor call.")

            # Execute the tool
            logger.info(f"[TOOL_START] Activating tool '{name}' with args: {args}")
            tool_output = await self.available_tools.execute(name=name, tool_input=args)
            logger.info(f"[TOOL_END] Tool '{name}' executed successfully.")

            # Store PID file path if this was the sandbox executor
            if name == SandboxPythonExecutor().name:
                # Check if tool_output is a dict, which is the expected return type for SandboxPythonExecutor
                # when it successfully returns a pid_file_path.
                if isinstance(tool_output, dict) and "pid_file_path" in tool_output:
                    self._current_sandbox_pid_file = tool_output["pid_file_path"]
                    self._current_script_tool_call_id = command.id
                    self._current_sandbox_pid = None # Reset PID, will be read if needed
                    logger.info(f"Stored PID file path '{self._current_sandbox_pid_file}' for tool call ID '{command.id}'.")
                # If tool_output is ToolResult, it means SandboxPythonExecutor might have wrapped its dict output
                # or an error occurred. If it's an error, it will be handled by the ToolResult processing below.
                # If it's a ToolResult containing the dict, we might need to extract it.
                # However, the current SandboxPythonExecutor().execute() method returns a dict directly, not a ToolResult.
                # So, this condition might be more for future-proofing or if other tools behave differently.
                elif isinstance(tool_output, ToolResult) and isinstance(tool_output.output, dict) and "pid_file_path" in tool_output.output:
                    self._current_sandbox_pid_file = tool_output.output["pid_file_path"]
                    self._current_script_tool_call_id = command.id
                    self._current_sandbox_pid = None
                    logger.info(f"Stored PID file path '{self._current_sandbox_pid_file}' (from ToolResult.output) for tool call ID '{command.id}'.")
                else:
                    logger.warning(f"Tool {name} did not return 'pid_file_path' as expected. Output type: {type(tool_output)}")

            # Handle special tools
            await self._handle_special_tool(name=name, result=tool_output)

            current_output_str = ""
            if isinstance(tool_output, ToolResult):
                if tool_output.base64_image:
                    self._current_base64_image = tool_output.base64_image

                if tool_output.error:
                    current_output_str = f"Error: {tool_output.error}"
                elif tool_output.output is not None:
                    current_output_str = str(tool_output.output)
                else:
                    current_output_str = "" # Saída vazia se não houver erro nem output

                observation = (
                    f"Observed output of cmd `{name}` executed:\n{current_output_str}"
                    if current_output_str
                    else f"Cmd `{name}` completed with no observable output or error."
                )
            elif isinstance(tool_output, str):
                self._current_base64_image = None # Garantir que não haja imagem base64 de uma execução anterior
                current_output_str = tool_output
                observation = (
                    f"Observed output of cmd `{name}` executed:\n{current_output_str}"
                    if current_output_str # Verifica se a string não é vazia
                    else f"Cmd `{name}` completed with no observable string output."
                )
            else:
                # Caso para tipos inesperados, pode ser logado ou tratado como erro
                logger.warning(f"Tool '{name}' returned an unexpected type: {type(tool_output)}. Converting to string.")
                self._current_base64_image = None
                current_output_str = str(tool_output) # Tenta converter para string como fallback
                observation = f"Observed output of cmd `{name}` executed (converted from {type(tool_output)}):\n{current_output_str}"

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
            # Cleanup PID file and attributes if this was the tracked script
            if hasattr(self, '_current_script_tool_call_id') and self._current_script_tool_call_id == command.id:
                if hasattr(self, '_cleanup_sandbox_file') and callable(getattr(self, '_cleanup_sandbox_file')):
                    await self._cleanup_sandbox_file(self._current_sandbox_pid_file)
                else:
                    # This case should ideally not happen if Manus is the one running.
                    # This indicates an agent that inherits ToolCallAgent but isn't Manus
                    # and hasn't implemented its own _cleanup_sandbox_file or similar.
                    logger.warning(f"Agent {self.name} does not have a _cleanup_sandbox_file method. PID file {self._current_sandbox_pid_file} may not be cleaned if it exists.")


                logger.info(f"Clearing PID tracking for tool call ID '{command.id}'.")
                self._current_sandbox_pid = None
                self._current_sandbox_pid_file = None
                self._current_script_tool_call_id = None

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Set agent state to finished
            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return True

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]

    async def cleanup(self):
        """Clean up resources used by the agent's tools."""
        logger.info(f"🧹 Cleaning up resources for agent '{self.name}'...")
        for tool_name, tool_instance in self.available_tools.tool_map.items():
            if hasattr(tool_instance, "cleanup") and asyncio.iscoroutinefunction(
                tool_instance.cleanup
            ):
                try:
                    logger.debug(f"🧼 Cleaning up tool: {tool_name}")
                    await tool_instance.cleanup()
                except Exception as e:
                    logger.error(
                        f"🚨 Error cleaning up tool '{tool_name}': {str(e)}"
                    )
                    # import traceback # Comment out for now, can be added if necessary
                    # logger.error(f"Traceback for {tool_name} cleanup error: {traceback.format_exc()}")
        logger.info(f"✨ Cleanup complete for agent '{self.name}'.")

    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with cleanup when done."""
        try:
            return await super().run(request)
        finally:
            await self.cleanup()
