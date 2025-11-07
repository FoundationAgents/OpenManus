"""
CLI Tools module providing cross-platform command execution support.
Supports Windows (cmd, powershell) and Unix (bash, terminal) environments.
"""

import os
import platform
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

from app.config import config
from app.logger import logger


class CLITool:
    """Cross-platform CLI tool for executing system commands."""
    
    def __init__(self):
        self.system = platform.system().lower()
        self._setup_environment()
        
    def _setup_environment(self):
        """Setup environment-specific configurations."""
        if self.system == "windows":
            self.shells = {
                "cmd": {
                    "executable": "cmd.exe",
                    "args": ["/C"],
                    "syntax": "windows"
                },
                "powershell": {
                    "executable": "powershell.exe",
                    "args": ["-Command"],
                    "syntax": "powershell"
                },
                "cm": {
                    "executable": "cmd.exe",
                    "args": ["/C"],
                    "syntax": "windows"
                }
            }
        else:
            self.shells = {
                "bash": {
                    "executable": "/bin/bash",
                    "args": ["-c"],
                    "syntax": "unix"
                },
                "terminal": {
                    "executable": os.environ.get("SHELL", "/bin/bash"),
                    "args": ["-c"],
                    "syntax": "unix"
                },
                "sh": {
                    "executable": "/bin/sh",
                    "args": ["-c"],
                    "syntax": "unix"
                }
            }
            
    def get_available_shells(self) -> List[str]:
        """Get list of available shells for the current platform."""
        available = []
        for shell_name, shell_config in self.shells.items():
            try:
                # Check if executable exists
                if self.system == "windows":
                    # On Windows, most executables are in PATH
                    available.append(shell_name)
                else:
                    # On Unix, check if executable exists and is executable
                    if os.path.isfile(shell_config["executable"]) and os.access(shell_config["executable"], os.X_OK):
                        available.append(shell_name)
            except Exception:
                pass
        return available
        
    def validate_command(self, command: str, shell_type: str) -> bool:
        """Validate if a command is allowed to be executed."""
        # Extract base command
        if self.system == "windows":
            # Windows command parsing
            parts = command.split()
            base_cmd = parts[0].lower() if parts else ""
        else:
            # Unix command parsing
            parts = shlex.split(command)
            base_cmd = parts[0] if parts else ""
            
        # Check against allowed commands
        allowed_commands = set(config.local_service.allowed_commands)
        
        # Add platform-specific commands
        if self.system == "windows":
            allowed_commands.update(["dir", "cls", "echo", "type", "copy", "del", "move"])
        else:
            allowed_commands.update(["ls", "clear", "echo", "cat", "cp", "rm", "mv", "pwd"])
            
        return base_cmd in allowed_commands
        
    def prepare_command(self, command: str, shell_type: str) -> List[str]:
        """Prepare command for execution with the specified shell."""
        if shell_type not in self.shells:
            raise ValueError(f"Unsupported shell type: {shell_type}")
            
        shell_config = self.shells[shell_type]
        
        if self.system == "windows":
            # Windows command preparation
            if shell_type == "powershell":
                return [shell_config["executable"]] + shell_config["args"] + [command]
            else:
                # cmd and cm use the same format
                return [shell_config["executable"]] + shell_config["args"] + [command]
        else:
            # Unix command preparation
            return [shell_config["executable"]] + shell_config["args"] + [command]
            
    def format_command_for_display(self, command: str, shell_type: str) -> str:
        """Format command for display in the UI."""
        if shell_type == "powershell":
            return f"PS> {command}"
        elif shell_type in ["cmd", "cm"]:
            return f"C:\\> {command}"
        elif shell_type in ["bash", "terminal", "sh"]:
            return f"$ {command}"
        else:
            return f"{shell_type}> {command}"
            
    async def execute_command(
        self,
        command: str,
        shell_type: str = "default",
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        capture_output: bool = True,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Union[int, str, bool]]:
        """Execute a command using the specified shell."""
        
        # Use default shell for the platform if not specified
        if shell_type == "default":
            shell_type = "cmd" if self.system == "windows" else "bash"
            
        # Validate shell type
        if shell_type not in self.shells:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Unsupported shell type: {shell_type}",
                "shell_type": shell_type
            }
            
        # Validate command
        if not self.validate_command(command, shell_type):
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command not allowed: {command}",
                "shell_type": shell_type
            }
            
        # Prepare command
        cmd_list = self.prepare_command(command, shell_type)
        
        # Set working directory
        working_dir = cwd or str(config.local_service.workspace_directory)
        
        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
            
        # Windows-specific environment setup
        if self.system == "windows":
            env["PYTHONIOENCODING"] = "utf-8"
            env["TERM"] = "xterm-256color"
            
        try:
            # Execute command
            logger.info(f"Executing {shell_type} command: {command}")
            
            process = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd_list,
                    cwd=working_dir,
                    env=env,
                    capture_output=capture_output,
                    text=True,
                    timeout=timeout or config.local_service.process_timeout,
                    shell=False
                )
            )
            
            return {
                "success": process.returncode == 0,
                "exit_code": process.returncode,
                "stdout": process.stdout if capture_output else "",
                "stderr": process.stderr if capture_output else "",
                "shell_type": shell_type,
                "command_display": self.format_command_for_display(command, shell_type)
            }
            
        except subprocess.TimeoutExpired as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout or config.local_service.process_timeout} seconds",
                "shell_type": shell_type
            }
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "shell_type": shell_type
            }
            
    def get_system_info(self) -> Dict[str, str]:
        """Get system information for the current platform."""
        info = {
            "system": self.system,
            "platform": platform.platform(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "available_shells": self.get_available_shells()
        }
        
        if self.system == "windows":
            try:
                import wmi
                c = wmi.WMI()
                for os_info in c.Win32_OperatingSystem():
                    info.update({
                        "os_name": os_info.Caption,
                        "os_version": os_info.Version,
                        "os_build": os_info.BuildNumber
                    })
                    break
            except ImportError:
                info["os_name"] = "Windows"
                info["os_version"] = platform.version()
        else:
            info.update({
                "os_name": platform.system(),
                "os_version": platform.version(),
                "shell": os.environ.get("SHELL", "unknown")
            })
            
        return info


# Import asyncio for async operations
import asyncio

# Global instance
cli_tool = CLITool()