import ast
import inspect
import json
import multiprocessing
import sys
from io import StringIO
from typing import Any, ClassVar, Dict, List, Optional

from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.python_execute import PythonExecute


class CodeActContext:
    """Context store for CodeAct execution to maintain state between calls."""

    def __init__(self):
        self.variables = {}  # Store variables across executions
        self.history = []  # Execution history
        self.action_results = {}  # Results of previous actions
        self.plan_status = {}  # Status of each step in the plan

    def to_dict(self) -> Dict[str, Any]:
        """Serialize context to dictionary, excluding complex objects."""
        return {
            "variables": {
                k: v for k, v in self.variables.items()
                if isinstance(v, (str, int, float, bool, list, dict))
            },
            "history": self.history[-5:],  # Keep only recent history
            "plan_status": self.plan_status
        }

    def update_from_code_result(self, code: str, result: Dict[str, Any]) -> None:
        """Update context based on executed code and its result."""
        self.history.append({
            "code_snippet": code[:100] + ("..." if len(code) > 100 else ""),
            "success": result.get("success", False),
            "timestamp": "__TIMESTAMP__"  # Will be replaced in runtime
        })

        # Extract variable assignments from code
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            if var_name in result.get("locals", {}):
                                self.variables[var_name] = result["locals"][var_name]
        except Exception as e:
            logger.warning(f"Failed to parse code for context update: {e}")


class CodeAct(BaseTool):
    """
    Enhanced Python code execution tool that implements the CodeAct pattern.

    CodeAct allows the agent to execute Python code as actions with improved:
    - Context persistence between calls
    - Error handling and recovery
    - Integration with planning system
    - Memory of previous executions and results
    """

    name: str = "code_act"
    description: str = """
    Execute Python code as actions with state management between executions.

    This tool enhances PythonExecute with:
    - Persistent variables between executions
    - Action tracking and monitoring
    - Integration with the planning system
    - Better error recovery options

    Example usage:
    ```python
    # Define a function to process data
    def process_data(data):
        return [x * 2 for x in data]

    # Use a variable from previous execution
    if 'data' in context.variables:
        data = context.variables['data']
    else:
        data = [1, 2, 3, 4, 5]

    # Process data and store result
    result = process_data(data)
    print(f"Processed data: {result}")

    # Update plan status
    if len(result) > 0:
        context.plan_status['data_processing'] = 'completed'
    else:
        context.plan_status['data_processing'] = 'failed'
    ```
    """

    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum execution time in seconds.",
                "default": 10
            },
            "with_context": {
                "type": "boolean",
                "description": "Whether to provide execution context to the code.",
                "default": True
            },
            "plan_step": {
                "type": "string",
                "description": "Optional plan step ID to associate with this execution.",
            }
        },
        "required": ["code"],
    }

    context: ClassVar[CodeActContext] = CodeActContext()
    python_execute: ClassVar[PythonExecute] = PythonExecute()

    def _run_code_with_context(
        self,
        code: str,
        result_dict: dict,
        context_dict: Optional[Dict] = None
    ) -> None:
        """Execute code with access to context and capture local variables."""
        original_stdout = sys.stdout
        locals_dict = {}

        try:
            # Prepare safe globals with context
            if isinstance(__builtins__, dict):
                safe_globals = {"__builtins__": __builtins__}
            else:
                safe_globals = {"__builtins__": __builtins__.__dict__.copy()}

            # Add context to globals if requested
            if context_dict:
                safe_globals["context"] = type("Context", (), context_dict)

            # Execute code and capture output
            output_buffer = StringIO()
            sys.stdout = output_buffer

            # Execute with locals dict to capture assigned variables
            exec(code, safe_globals, locals_dict)

            # Store results
            result_dict["observation"] = output_buffer.getvalue()
            result_dict["locals"] = {
                k: v for k, v in locals_dict.items()
                if not k.startswith("_") and isinstance(v, (str, int, float, bool, list, dict))
            }
            result_dict["success"] = True

        except Exception as e:
            result_dict["observation"] = str(e)
            result_dict["error_type"] = type(e).__name__
            result_dict["success"] = False

        finally:
            sys.stdout = original_stdout

    async def execute(
        self,
        code: str,
        timeout: int = 10,
        with_context: bool = True,
        plan_step: Optional[str] = None,
    ) -> ToolResult:
        """
        Execute Python code with context awareness and enhanced error handling.

        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            with_context: Whether to provide the context to the code
            plan_step: Optional plan step ID to associate with this execution

        Returns:
            ToolResult with execution results
        """
        # Prepare context if needed
        context_dict = self.context.to_dict() if with_context else None

        # Run code in a separate process for safety and timeout handling
        with multiprocessing.Manager() as manager:
            result = manager.dict({
                "observation": "",
                "locals": {},
                "success": False
            })

            proc = multiprocessing.Process(
                target=self._run_code_with_context,
                args=(code, result, context_dict)
            )

            proc.start()
            proc.join(timeout)

            # Handle timeout
            if proc.is_alive():
                proc.terminate()
                proc.join(1)
                execution_result = {
                    "observation": f"Execution timeout after {timeout} seconds",
                    "success": False,
                    "error_type": "TimeoutError"
                }
            else:
                execution_result = dict(result)

            # Update context with results
            self.context.update_from_code_result(code, execution_result)

            # Update plan status if step was provided
            if plan_step:
                if execution_result.get("success", False):
                    self.context.plan_status[plan_step] = "completed"
                else:
                    self.context.plan_status[plan_step] = "failed"

            # Format output for display
            output = execution_result.get("observation", "")
            success = execution_result.get("success", False)

            # Add contextual information
            if with_context:
                context_info = "\n\n--- Context Info ---\n"
                if self.context.variables:
                    context_info += "Available variables: " + ", ".join(self.context.variables.keys()) + "\n"
                if self.context.plan_status:
                    context_info += "Plan status: " + json.dumps(self.context.plan_status, indent=2) + "\n"

                # Only add context info if execution was successful
                if success:
                    output += context_info

            return ToolResult(
                output=output,
                metadata={
                    "success": success,
                    "error_type": execution_result.get("error_type"),
                    "with_context": with_context,
                    "plan_step": plan_step
                }
            )

    def reset_context(self) -> None:
        """Reset the execution context."""
        self.context = CodeActContext()
