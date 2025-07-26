import os
import traceback
from typing import Dict, Union
import asyncio

# Imports for ASTRefactorTool
import ast
try:
    import astunparse
except ImportError:
    astunparse = None # Handled in the tool's execute method

from app.tool.base import BaseTool
from app.logger import logger
from app.config import config # For workspace path

class ReplaceCodeBlock(BaseTool):
    name: str = "replace_code_block"
    description: str = (
        "Replaces a block of code in a specified file between a given start_line and end_line (inclusive). "
        "Line numbers are 1-indexed. Relative paths are resolved from the agent's workspace root."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The relative (from workspace root) or absolute path to the file to be modified.",
            },
            "start_line": {
                "type": "integer",
                "description": "The 1-indexed line number where the replacement block starts.",
            },
            "end_line": {
                "type": "integer",
                "description": "The 1-indexed line number where the replacement block ends (inclusive).",
            },
            "new_content": {
                "type": "string",
                "description": "The new code content to insert. Can be multi-line. Empty string to delete lines.",
            },
        },
        "required": ["path", "start_line", "end_line", "new_content"],
    }

    async def execute(self, path: str, start_line: int, end_line: int, new_content: str) -> Dict[str, str]:
        if not os.path.isabs(path):
            file_path = os.path.join(config.workspace_root, path)
        else:
            file_path = path

        file_path = os.path.normpath(file_path)

        if not os.path.isabs(path):
            if not file_path.startswith(os.path.normpath(config.workspace_root)):
                logger.error(f"Path traversal attempt detected. Original path: '{path}', Resolved path: '{file_path}' is outside workspace '{config.workspace_root}'.")
                return {"error": "Path traversal attempt detected. Operation is not allowed."}

        if not os.path.isfile(file_path):
            logger.error(f"File not found at path: {file_path}")
            return {"error": f"File not found: {path} (resolved to: {file_path})"}

        if start_line <= 0:
            logger.error(f"Invalid start_line: {start_line}. Must be > 0.")
            return {"error": "start_line must be 1-indexed and greater than 0."}
        if end_line < start_line:
            logger.error(f"Invalid end_line: {end_line}. Must be >= start_line ({start_line}).")
            return {"error": "end_line must be greater than or equal to start_line."}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if start_line > len(lines) + 1 :
                 logger.error(f"start_line ({start_line}) is too far beyond the end of the file ({len(lines)} lines).")
                 return {"error": f"start_line ({start_line}) is too far beyond the end of the file ({len(lines)} lines). To append, start_line can be at most {len(lines) + 1}."}

            start_line_0idx = start_line - 1
            end_line_0idx = end_line
            pre_block = lines[:start_line_0idx]

            if end_line_0idx >= len(lines):
                post_block = []
            else:
                post_block = lines[end_line_0idx:]

            if new_content:
                new_content_lines = new_content.splitlines(True)
            else:
                new_content_lines = []
                if start_line_0idx == len(lines) and not lines:
                    pass
                elif start_line_0idx > len(lines):
                     logger.error(f"start_line ({start_line}) is beyond the end of the file ({len(lines)} lines) and new_content is empty. Nothing to replace.")
                     return {"error": f"start_line ({start_line}) is beyond the end of the file ({len(lines)} lines) and new_content is empty. Nothing to replace."}

            final_lines = pre_block + new_content_lines + post_block

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(final_lines)

            action = "appended to" if start_line_0idx == len(lines) and new_content else "replaced lines"
            if not new_content and start_line <= end_line :
                action = "deleted lines" if end_line <= len(lines) else "deleted lines until end of file"

            end_line_display = min(end_line, len(lines)) if start_line <= len(lines) else len(lines)

            logger.info(f"Successfully {action} {start_line}-{end_line_display if new_content else end_line} in file {file_path}")
            return {"status": f"Successfully {action} {start_line}-{end_line_display if new_content else end_line} in file {path}."}

        except Exception as e:
            logger.error(f"Error replacing code block in {file_path}: {e}\n{traceback.format_exc()}")
            return {"error": f"An unexpected error occurred: {str(e)}"}


class ApplyDiffPatch(BaseTool):
    name: str = "apply_diff_patch"
    description: str = (
        "Applies a patch (in unified diff format) to a specified file. "
        "Useful for complex or non-contiguous code changes. "
        "Relative paths are resolved from the agent's workspace root."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The relative (from workspace root) or absolute path to the file to be patched.",
            },
            "patch_content": {
                "type": "string",
                "description": "The content of the patch in unified diff format.",
            },
        },
        "required": ["path", "patch_content"],
    }

    async def execute(self, path: str, patch_content: str) -> Dict[str, str]:
        if not os.path.isabs(path):
            file_path = os.path.join(config.workspace_root, path)
        else:
            file_path = path

        file_path = os.path.normpath(file_path)

        if not os.path.isabs(path):
            if not file_path.startswith(os.path.normpath(config.workspace_root)):
                logger.error(f"Path traversal attempt detected for patch application. Original path: '{path}', Resolved path: '{file_path}' is outside workspace '{config.workspace_root}'.")
                return {"error": "Path traversal attempt detected. Operation is not allowed."}

        if not os.path.isfile(file_path):
            logger.error(f"File not found at path for patching: {file_path}")
            return {"error": f"File not found for patching: {path} (resolved to: {file_path})"}

        if not patch_content.strip():
            return {"error": "Patch content cannot be empty."}

        try:
            if not patch_content.endswith('\n'):
                patch_content += '\n'

            command = f"patch '{file_path}'"

            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate(input=patch_content.encode('utf-8'))

            if process.returncode == 0:
                logger.info(f"Patch successfully applied to {file_path}. Output: {stdout.decode('utf-8', 'replace')}")
                return {"status": f"Patch successfully applied to {path}.", "details": stdout.decode('utf-8', 'replace')}
            else:
                error_message = f"Failed to apply patch to {file_path}. Return code: {process.returncode}. Error: {stderr.decode('utf-8', 'replace')}. Stdout: {stdout.decode('utf-8', 'replace')}"
                logger.error(error_message)
                return {"error": error_message}

        except FileNotFoundError:
            logger.error("The 'patch' command-line utility was not found. Please ensure it is installed and in the system PATH.")
            return {"error": "The 'patch' command-line utility not found. It needs to be installed on the system."}
        except Exception as e:
            logger.error(f"An unexpected error occurred while applying patch to {file_path}: {e}\n{traceback.format_exc()}")
            return {"error": f"An unexpected error occurred during patch application: {str(e)}"}


class ASTRefactorTool(BaseTool):
    name: str = "ast_refactor"
    description: str = (
        "Performs AST-based refactoring for Python code. "
        "Initially supports 'replace_function_body'. "
        "Requires 'astunparse' library. Relative paths are resolved from workspace root."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The relative (from workspace root) or absolute path to the Python file.",
            },
            "operation": {
                "type": "string",
                "description": "The refactoring operation to perform. Currently supports: 'replace_function_body'.",
                "enum": ["replace_function_body"],
            },
            "target_node_name": {
                "type": "string",
                "description": "The name of the target AST node (e.g., the function name whose body is to be replaced).",
            },
            "new_code_snippet": {
                "type": "string",
                "description": "The new Python code snippet to be used for the refactoring (e.g., the new function body).",
            }
        },
        "required": ["path", "operation", "target_node_name", "new_code_snippet"],
    }

    async def execute(self, path: str, operation: str, target_node_name: str, new_code_snippet: str) -> Dict[str, str]:
        if not astunparse:
            return {"error": "The 'astunparse' library is required for AST refactoring but is not installed."}

        if not os.path.isabs(path):
            file_path = os.path.join(config.workspace_root, path)
        else:
            file_path = path

        file_path = os.path.normpath(file_path)
        if not os.path.isabs(path):
            if not file_path.startswith(os.path.normpath(config.workspace_root)):
                logger.error(f"Path traversal attempt detected for AST refactoring: {file_path}")
                return {"error": "Path is outside the allowed workspace."}

        if not os.path.isfile(file_path):
            logger.error(f"File not found for AST refactoring: {file_path}")
            return {"error": f"File not found: {path} (resolved to: {file_path})"}

        if operation != "replace_function_body":
            return {"error": f"Unsupported operation: {operation}. Currently only 'replace_function_body' is supported."}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()

            original_tree = ast.parse(source_code, filename=file_path)

            new_body_ast_module = ast.parse(new_code_snippet)
            new_body_nodes = new_body_ast_module.body
            if not new_body_nodes and not new_code_snippet.strip(): # if snippet is empty or only whitespace
                 new_body_nodes = [ast.Pass()]


            class FunctionBodyReplacer(ast.NodeTransformer):
                def __init__(self, target_fn_name: str, new_body_nodes: list):
                    super().__init__()
                    self.target_fn_name = target_fn_name
                    self.new_body_nodes = new_body_nodes
                    self.found_and_replaced = False

                def visit_FunctionDef(self, node: ast.FunctionDef):
                    if node.name == self.target_fn_name:
                        node.body = self.new_body_nodes
                        self.found_and_replaced = True
                        logger.info(f"Replaced body of function '{self.target_fn_name}' in AST.")
                    return node

            transformer = FunctionBodyReplacer(target_node_name, new_body_nodes)
            modified_tree = transformer.visit(original_tree)

            if not transformer.found_and_replaced:
                return {"error": f"Function '{target_node_name}' not found in {path}."}

            new_source_code = astunparse.unparse(modified_tree)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_source_code)

            logger.info(f"Successfully refactored (replaced body of '{target_node_name}') in {file_path}")
            return {"status": f"Successfully replaced body of function '{target_node_name}' in {path}."}

        except SyntaxError as e:
            logger.error(f"Syntax error during AST refactoring for {file_path}: {e}\n{traceback.format_exc()}")
            return {"error": f"Syntax error encountered: {str(e)}\nFull traceback in logs."} # Keep it concise for agent
        except Exception as e:
            logger.error(f"Error during AST refactoring for {file_path}: {e}\n{traceback.format_exc()}")
            return {"error": f"An unexpected error occurred during AST refactoring: {str(e)}"}
