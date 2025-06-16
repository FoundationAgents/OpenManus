import re
from typing import List, Dict, Any, Optional

from pydantic import Field, model_validator

from app.agent.base import BaseAgent, AgentState
from app.llm.llm_client import LLMClient
from app.memory.base import Message, MessageRole
from app.tool.sandbox_python_executor import SandboxPythonExecutor
from app.config import AgentSettings


class SelfCodingAgent(BaseAgent):
    """
    A specialized agent that autonomously generates, executes, and iteratively
    corrects Python code to accomplish a given task.

    The agent operates by:
    1. Receiving a task description.
    2. Generating Python code using an LLM.
    3. Executing the code in a secure sandbox environment via `SandboxPythonExecutor`.
    4. Analyzing the execution results (stdout, stderr, exit code).
    5. If execution fails or produces errors, the agent attempts to correct the
       code by re-prompting the LLM with the original task, the faulty code,
       and its output.
    6. This correction process iterates up to `max_correction_attempts`.

    Key Attributes:
        name (str): "SelfCodingAgent".
        description (str): A brief description of the agent's capabilities.
        system_prompt (str): The base prompt used to instruct the LLM for code generation and correction.
        sandbox_executor_tool (SandboxPythonExecutor): The tool used for executing Python code.
        max_correction_attempts (int): Maximum number of times the agent will try to correct failing code.
        current_task_description (Optional[str]): The description of the current task being processed.
        current_code_to_execute (Optional[str]): The Python code currently being evaluated or corrected.
        current_correction_attempts (int): The number of correction attempts made for the current code.
    """

    name: str = "SelfCodingAgent"
    description: str = (
        "An agent that can generate, execute, and iteratively correct Python code "
        "in a sandbox environment."
    )
    system_prompt: str = (
        "You are an AI assistant that writes Python code to solve problems. "
        "Given a task, write a Python script that accomplishes it. "
        "The script will be executed in a sandbox environment. "
        "Ensure your code uses print statements for any output you want to be visible. "
        "Only the output from print statements will be captured as stdout. "
        "Your response should contain *only* the Python code, preferably in a "
        "single markdown block (e.g., ```python ... ```). "
        "Do not include any explanatory text outside the code block. "
        "If you are asked to correct code, provide the full corrected script."
    )

    sandbox_executor_tool: SandboxPythonExecutor = Field(default_factory=SandboxPythonExecutor)
    max_correction_attempts: int = 3
    default_execution_timeout: int = 30  # Added default execution timeout
    current_correction_attempts: int = 0
    
    # State for the current task being processed
    current_task_description: Optional[str] = None
    current_code_to_execute: Optional[str] = None

    @model_validator(mode="after")
    def validate_agent_state(self) -> "SelfCodingAgent":
        if not isinstance(self.sandbox_executor_tool, SandboxPythonExecutor):
            self.sandbox_executor_tool = SandboxPythonExecutor()
        # Initialize mutable state attributes for clarity, though run() will also manage them per task
        self.current_task_description = None
        self.current_code_to_execute = None
        self.current_correction_attempts = 0
        return self

    def _extract_python_code(self, llm_response: str) -> str:
        """
        Extracts Python code from the LLM's response string.

        It looks for Markdown code blocks, specifically:
        - ```python ... ``` (preferred)
        - ``` ... ``` (generic)

        If no Markdown block is found, it assumes the entire response string
        is the code, after stripping leading/trailing whitespace.

        Args:
            llm_response: The string response from the LLM.

        Returns:
            The extracted Python code as a string, or the original response
            stripped if no code block is found.
        """
        match_python = re.search(r"```python\s*(.*?)\s*```", llm_response, re.DOTALL | re.IGNORECASE)
        if match_python:
            return match_python.group(1).strip()

        match_generic = re.search(r"```\s*(.*?)\s*```", llm_response, re.DOTALL)
        if match_generic:
            return match_generic.group(1).strip()
        
        return llm_response.strip()

    async def step(self) -> str:
        """
        Performs a single step in the agent's problem-solving process.

        This method handles one iteration of the generate-execute-evaluate-correct loop.
        If no code is currently being processed (`self.current_code_to_execute` is None),
        it attempts to generate initial code based on `self.current_task_description`.
        Otherwise, it executes the `self.current_code_to_execute`.

        Based on the execution outcome:
        - If successful, it sets the agent state to `FINISHED`.
        - If failed, it attempts to generate a correction from the LLM, unless
          `max_correction_attempts` has been reached.

        The method logs its actions and observations to the agent's memory and
        returns a string summarizing the outcome of the step.

        Returns:
            A string message summarizing the result of the step, e.g.,
            "Code executed successfully.", "Execution failed. Attempting correction...",
            or an error message if a critical failure occurs.
        """
        if self.state == AgentState.FINISHED or self.state == AgentState.ERROR:
            return "Task already finished or in an error state. Start a new task via run()."

        if not self.current_task_description:
            self.memory.add_message(Message(role=MessageRole.SYSTEM, content="Error: No task description available."))
            self.state = AgentState.ERROR
            return "Error: No task description. Cannot proceed."

        # Initial Code Generation (if no code is currently being worked on)
        if self.current_code_to_execute is None:
            self.current_correction_attempts = 0 # Reset for the first attempt of this task
            self.memory.add_message(Message(role=MessageRole.SYSTEM, content=f"Starting task: {self.current_task_description}"))
            self.memory.add_message(Message(role=MessageRole.SYSTEM, content="Attempting to generate initial code for the task.")) # Log point 1
            
            llm_messages: List[Message] = [
                Message(role=MessageRole.SYSTEM, content=self.system_prompt),
                Message(role=MessageRole.USER, content=f"The task is: {self.current_task_description}")
            ]
            
            try:
                llm_response_message = await self.llm.chat_completion_async(messages=llm_messages)
                self.memory.add_message(llm_response_message)
            except Exception as e:
                self.memory.add_message(Message(role=MessageRole.SYSTEM, content=f"Error during initial LLM call: {str(e)}"))
                self.state = AgentState.ERROR
                return f"Error during initial code generation: {str(e)}"

            generated_code_text = llm_response_message.content
            extracted_code = self._extract_python_code(generated_code_text)
            self.memory.add_message(Message(role=MessageRole.SYSTEM, content="Initial code generated successfully.")) # Log point 2

            if not extracted_code:
                error_msg = "Code generation failed: LLM did not return any code."
                self.memory.add_message(Message(role=MessageRole.SYSTEM, content=error_msg))
                self.state = AgentState.ERROR # Cannot proceed without code
                return error_msg
            
            self.current_code_to_execute = extracted_code
            self.memory.add_message(Message(role=MessageRole.SYSTEM, content=f"Attempt {self.current_correction_attempts + 1}. Code to execute:\n```python\n{self.current_code_to_execute}\n```"))

        # Code Execution
        if not self.current_code_to_execute: # Should not happen if initial generation logic is correct
            self.state = AgentState.ERROR
            return "Error: No code available for execution."

        self.memory.add_message(Message(role=MessageRole.SYSTEM, content=f"Preparing to execute code for attempt {self.current_correction_attempts + 1}...")) # Log point 3
        try:
            execution_result = await self.sandbox_executor_tool.execute(
                code=self.current_code_to_execute, timeout=self.default_execution_timeout
            )
            self.memory.add_message(Message(role=MessageRole.SYSTEM, content="Code execution finished. Analyzing results...")) # Log point 4
        except Exception as e:
            # This catches unexpected errors from the sandbox tool itself
            self.memory.add_message(Message(role=MessageRole.SYSTEM, content=f"Error during code execution tool call: {str(e)}"))
            self.state = AgentState.ERROR
            return f"Error calling sandbox executor: {str(e)}"

        # Store execution result
        exec_stdout = execution_result.get("stdout", "")
        exec_stderr = execution_result.get("stderr", "")
        exec_exit_code = execution_result.get("exit_code", -1)

        result_message_content = (
            f"Execution Attempt {self.current_correction_attempts + 1} Result:\n"
            f"Exit Code: {exec_exit_code}\n"
            f"Stdout:\n{exec_stdout}\n"
            f"Stderr:\n{exec_stderr}"
        )
        self.memory.add_message(Message(role=MessageRole.SYSTEM, content=result_message_content))

        # Evaluation and Correction Loop
        # Success condition: exit code 0 and no stderr (or stderr is acceptable)
        # For now, strict: exit code 0 and empty stderr.
        if exec_exit_code == 0 and not exec_stderr:
            success_msg = f"Code executed successfully.\nOutput:\n{exec_stdout}"
            self.memory.add_message(Message(role=MessageRole.SYSTEM, content=success_msg))
            self.state = AgentState.FINISHED
            self.current_code_to_execute = None # Clear code for next task
            # self.current_task_description = None # Clear task for next run
            return success_msg
        else: # Execution failed or had errors/warnings in stderr
            self.current_correction_attempts += 1
            if self.current_correction_attempts >= self.max_correction_attempts:
                failure_msg = (
                    f"Code execution failed after {self.max_correction_attempts} attempts.\n"
                    f"Last Exit Code: {exec_exit_code}\n"
                    f"Last Stderr:\n{exec_stderr}\n"
                    f"Last Stdout:\n{exec_stdout}"
                )
                self.memory.add_message(Message(role=MessageRole.SYSTEM, content=failure_msg))
                self.state = AgentState.ERROR # Or FINISHED if error state is terminal for the task
                self.current_code_to_execute = None # Clear code
                # self.current_task_description = None
                return failure_msg
            else:
                # Attempt correction
                self.memory.add_message(Message(role=MessageRole.SYSTEM, content="Execution failed. Preparing to attempt code correction.")) # Log point 5
                self.memory.add_message(Message(role=MessageRole.SYSTEM, content="Attempting code correction."))
                correction_prompt_parts = [
                    self.system_prompt, # Re-iterate overall goal
                    f"The original task was: {self.current_task_description}",
                    f"The following Python code was executed:\n```python\n{self.current_code_to_execute}\n```",
                    f"It produced the following output (stdout):\n```\n{exec_stdout}\n```",
                    f"And the following errors (stderr):\n```\n{exec_stderr}\n```",
                    f"The exit code was: {exec_exit_code}",
                    "Please analyze the error and provide a corrected version of the Python script. "
                    "Ensure the full corrected script is provided in a single markdown block. "
                    "Do not include any explanatory text outside the code block."
                ]
                # Use a history of messages for correction to give context
                # For now, we can just use the last few relevant messages or build a specific prompt.
                # The memory already contains the task, previous code, and its output.
                # We can create a focused list of messages for the LLM.

                # Simplified: Construct a user message with all context for correction
                correction_user_message = Message(role=MessageRole.USER, content="\n".join(correction_prompt_parts[1:]))
                
                llm_correction_messages: List[Message] = [
                     Message(role=MessageRole.SYSTEM, content=self.system_prompt), # System prompt
                     # Include some history if useful - e.g. original user task, last assistant code, last tool output
                     # For this version, the correction_user_message is comprehensive.
                     correction_user_message
                ]

                try:
                    llm_corrected_response = await self.llm.chat_completion_async(messages=llm_correction_messages)
                    self.memory.add_message(llm_corrected_response)
                    self.memory.add_message(Message(role=MessageRole.SYSTEM, content="Corrected code received from LLM.")) # Log point 6
                except Exception as e:
                    self.memory.add_message(Message(role=MessageRole.SYSTEM, content=f"Error during LLM call for correction: {str(e)}"))
                    # Decide if this failure means we stop or if the old code is re-attempted (potentially risky)
                    # For now, let's assume an LLM error here might lead to retrying with old code or erroring out.
                    # Let's be safe: if LLM for correction fails, we error out this attempt.
                    self.state = AgentState.ERROR
                    return f"Error during LLM call for code correction: {str(e)}"

                new_code_text = llm_corrected_response.content
                extracted_new_code = self._extract_python_code(new_code_text)

                if not extracted_new_code:
                    # LLM failed to provide corrected code
                    self.memory.add_message(Message(role=MessageRole.SYSTEM, content="LLM did not provide any corrected code.")) # Log point 7
                    error_msg = "Correction attempt failed: LLM did not return any code for correction."
                    self.memory.add_message(Message(role=MessageRole.SYSTEM, content=error_msg))
                    # We don't change self.current_code_to_execute, so next step will re-run the *previous* failed code.
                    # This might not be ideal. Alternatively, we could count this as a failed attempt and stop if maxed out.
                    # For now, this counts as an attempt. If it happens repeatedly, max_correction_attempts will be hit.
                    # Let's return the error_msg; the loop in run() will call step() again.
                    return error_msg 

                self.current_code_to_execute = extracted_new_code
                self.memory.add_message(Message(role=MessageRole.SYSTEM, content=f"Attempt {self.current_correction_attempts + 1}. Corrected code to execute:\n```python\n{self.current_code_to_execute}\n```"))
                
                # State remains RUNNING, next call to step will execute the corrected code
                return (
                    f"Execution failed. Attempting correction "
                    f"({self.current_correction_attempts}/{self.max_correction_attempts})..."
                )

    async def run(
        self, request: str, config: Optional[AgentSettings] = None
    ) -> Dict[str, Any]:
        """
        Main entry point to run the SelfCodingAgent to accomplish a given task.

        This method orchestrates the agent's lifecycle for a single task request:
        1. Initializes or updates the LLM client based on provided `config`.
        2. Sets up the agent's internal state for the new task (`current_task_description`,
           clears `current_code_to_execute`, resets `current_correction_attempts`).
        3. Adds the user's `request` to the agent's memory.
        4. Enters a loop, repeatedly calling the `step()` method as long as the
           agent's state is `RUNNING`. Each call to `step()` represents one iteration
           of code generation/execution/correction.
        5. The loop continues until the `step()` method changes the agent's state
           to `FINISHED` (on success) or `ERROR` (if max attempts are reached or an
           unrecoverable error occurs).
        6. A loop guard is in place to prevent potential infinite loops during development.

        Args:
            request: A string describing the task for the agent to accomplish.
            config: Optional `AgentSettings` to configure the agent, particularly
                    LLM settings.

        Returns:
            A dictionary containing the final outcome of the agent's execution:
            - "response" (str): The final message from the agent, indicating success
                                or the nature of the failure.
            - "status" (AgentState): The final state of the agent.
            - "memory" (str): A string representation of all messages (interactions,
                              thoughts, tool outputs) logged by the agent during its run.
        """
        self.memory.add_message(Message(role=MessageRole.USER, content=request))
        
        if config and config.llm_settings:
            self.llm = LLMClient(settings=config.llm_settings)
        elif not self.llm: # Ensure LLM is initialized
            # Assuming BaseAgent or a global default LLM client is available
            # If not, this would need proper initialization.
            # For now, we assume self.llm is valid.
            pass

        # Initialize state for a new task
        self.current_task_description = request
        self.current_code_to_execute = None # Start with no code
        self.current_correction_attempts = 0
        self.state = AgentState.RUNNING
        
        response_content = "Agent started..." # Initial response

        # The BaseAgent's run loop might handle max_steps.
        # This internal loop ensures step() is called until state is FINISHED or ERROR.
        loop_guard = 0 # To prevent infinite loops in dev if state isn't set correctly
        max_loops = self.max_correction_attempts + 5 # Allow for initial + corrections + some buffer

        while self.state == AgentState.RUNNING and loop_guard < max_loops:
            step_result = await self.step()
            response_content = step_result # Update response with the latest from step
            loop_guard +=1
            if loop_guard >= max_loops and self.state == AgentState.RUNNING:
                self.memory.add_message(Message(role=MessageRole.SYSTEM, content="Error: Agent seems stuck in a loop."))
                self.state = AgentState.ERROR
                response_content = "Error: Agent exceeded maximum internal loops."

        # Final response structure
        return {
            "response": response_content, # The final message from the last step
            "status": self.state.value,
            "memory": self.memory.get_messages_str(), # Or a more structured representation
        }

```
