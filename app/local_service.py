"""
Local Service module for replacing Daytona with local execution environment.
Provides process management, file operations, and CLI support for Windows/Linux/macOS.
"""

import asyncio
import os
import platform
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Union

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from app.config import config
from app.logger import logger
from app.security.guardian_agent import (
    get_guardian_agent,
    ValidationRequest,
    CommandSource,
)


class LocalProcess:
    """Represents a running process in the local service."""
    
    def __init__(self, process_id: str, command: str, cwd: str, process: subprocess.Popen):
        self.process_id = process_id
        self.command = command
        self.cwd = cwd
        self.process = process
        self.start_time = asyncio.get_event_loop().time()
        
    @property
    def is_running(self) -> bool:
        """Check if the process is still running."""
        return self.process.poll() is None
        
    @property
    def pid(self) -> int:
        """Get the process PID."""
        return self.process.pid
        
    async def wait(self, timeout: Optional[int] = None) -> int:
        """Wait for the process to complete and return the exit code."""
        try:
            return await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self.process.wait
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            self.terminate()
            raise
            
    def terminate(self):
        """Terminate the process."""
        try:
            if self.is_running:
                self.process.terminate()
                # Force kill if it doesn't terminate after 5 seconds
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
        except ProcessLookupError:
            # Process already terminated
            pass


class LocalService:
    """Local service for managing processes and file operations."""
    
    def __init__(self):
        self.processes: Dict[str, LocalProcess] = {}
        self.workspace_dir = Path(config.local_service.workspace_directory).resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Detect platform and set appropriate shell
        self.system = platform.system().lower()
        if self.system == "windows":
            self.shell = True
            self.default_shell = "cmd"
        else:
            self.shell = True
            self.default_shell = "bash"
            
        logger.info(f"Initialized LocalService for {self.system} with workspace: {self.workspace_dir}")
        
    def _get_allowed_command(self, command: str) -> Optional[str]:
        """Check if a command is allowed and return the validated command."""
        # Extract the base command (first word)
        base_cmd = command.split()[0].lower() if command else ""
        
        # Check if the base command is in the allowed list
        if base_cmd in config.local_service.allowed_commands:
            return command
            
        # Special cases for Windows
        if self.system == "windows":
            if base_cmd in ["cm", "cmd"]:
                return command.replace(base_cmd, "cmd", 1)
            elif base_cmd == "powershell":
                return f"powershell -Command \"{command[len('powershell'):].strip()}\""
                
        logger.warning(f"Command '{base_cmd}' is not in allowed commands list")
        return None
        
    async def execute_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        capture_output: bool = True,
        user_id: Optional[int] = None,
        agent_id: Optional[str] = None
    ) -> Dict[str, Union[int, str, bool]]:
        """Execute a command and return the result."""
        
        # Validate command through Guardian
        if config.guardian_validation.enable_command_validation:
            guardian = await get_guardian_agent()
            
            working_dir = Path(cwd) if cwd else self.workspace_dir
            
            validation_request = ValidationRequest(
                command=command,
                source=CommandSource.LOCAL_SERVICE,
                agent_id=agent_id,
                user_id=user_id,
                working_dir=str(working_dir)
            )
            
            decision = await guardian.validate(validation_request)
            
            if not decision.approved:
                logger.warning(f"Command rejected by Guardian: {command}")
                return {
                    "success": False,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command rejected by Guardian: {decision.reason}"
                }
            
            logger.debug(f"Command approved by Guardian: {command}")
        
        # Validate command locally
        validated_command = self._get_allowed_command(command)
        if not validated_command:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command '{command}' is not allowed"
            }
            
        # Set working directory
        working_dir = Path(cwd) if cwd else self.workspace_dir
        working_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate process ID
        process_id = str(uuid.uuid4())
        
        try:
            # Prepare subprocess arguments
            kwargs = {
                "shell": self.shell,
                "cwd": str(working_dir),
                "text": True,
                "stdout": subprocess.PIPE if capture_output else None,
                "stderr": subprocess.PIPE if capture_output else None,
            }
            
            # Windows-specific environment setup
            if self.system == "windows":
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                kwargs["env"] = env
                
            logger.info(f"Executing command: {validated_command} in {working_dir}")
            
            # Start the process
            process = await asyncio.get_event_loop().run_in_executor(
                None, lambda: subprocess.Popen(validated_command, **kwargs)
            )
            
            # Create LocalProcess object
            local_process = LocalProcess(process_id, validated_command, str(working_dir), process)
            self.processes[process_id] = local_process
            
            # Wait for completion with timeout
            exit_code = await local_process.wait(timeout or config.local_service.process_timeout)
            
            # Get output
            stdout = ""
            stderr = ""
            if capture_output:
                stdout = process.stdout.read() if process.stdout else ""
                stderr = process.stderr.read() if process.stderr else ""
                
            # Clean up
            del self.processes[process_id]
            
            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "process_id": process_id
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Command timed out: {validated_command}")
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout or config.local_service.process_timeout} seconds"
            }
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e)
            }
            
    async def execute_interactive_command(
        self,
        command: str,
        cwd: Optional[str] = None
    ) -> str:
        """Execute an interactive command and return the process ID."""
        
        validated_command = self._get_allowed_command(command)
        if not validated_command:
            raise ValueError(f"Command '{command}' is not allowed")
            
        working_dir = Path(cwd) if cwd else self.workspace_dir
        process_id = str(uuid.uuid4())
        
        kwargs = {
            "shell": self.shell,
            "cwd": str(working_dir),
            "text": True,
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
        }
        
        if self.system == "windows":
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            kwargs["env"] = env
            
        process = await asyncio.get_event_loop().run_in_executor(
            None, lambda: subprocess.Popen(validated_command, **kwargs)
        )
        
        local_process = LocalProcess(process_id, validated_command, str(working_dir), process)
        self.processes[process_id] = local_process
        
        return process_id
        
    async def send_input_to_process(self, process_id: str, input_text: str) -> bool:
        """Send input to an interactive process."""
        if process_id not in self.processes:
            return False
            
        process = self.processes[process_id].process
        try:
            process.stdin.write(input_text + "\n")
            process.stdin.flush()
            return True
        except Exception as e:
            logger.error(f"Error sending input to process {process_id}: {e}")
            return False
            
    async def get_process_output(self, process_id: str) -> Optional[str]:
        """Get output from an interactive process."""
        if process_id not in self.processes:
            return None
            
        process = self.processes[process_id].process
        try:
            # Non-blocking read
            import select
            import sys
            
            if self.system == "windows":
                # Windows doesn't support select on pipes
                # For simplicity, return None on Windows
                return None
            else:
                # Unix-like systems
                ready, _, _ = select.select([process.stdout], [], [], 0.1)
                if ready:
                    return process.stdout.read(1024)
                return None
        except Exception as e:
            logger.error(f"Error reading output from process {process_id}: {e}")
            return None
            
    async def terminate_process(self, process_id: str) -> bool:
        """Terminate a running process."""
        if process_id not in self.processes:
            return False
            
        try:
            self.processes[process_id].terminate()
            del self.processes[process_id]
            return True
        except Exception as e:
            logger.error(f"Error terminating process {process_id}: {e}")
            return False
            
    def list_processes(self) -> List[Dict[str, Union[str, int, bool]]]:
        """List all running processes."""
        return [
            {
                "process_id": proc.process_id,
                "command": proc.command,
                "cwd": proc.cwd,
                "pid": proc.pid,
                "is_running": proc.is_running,
                "start_time": proc.start_time
            }
            for proc in self.processes.values()
        ]
        
    async def write_file(self, file_path: str, content: str) -> bool:
        """Write content to a file in the workspace."""
        try:
            full_path = self.workspace_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Create version if versioning is enabled
            try:
                from app.storage.service import get_versioning_service
                versioning_service = get_versioning_service()
                versioning_service.on_file_save(
                    file_path,
                    content,
                    agent="local_service",
                    reason="File written via LocalService"
                )
            except ImportError:
                # Versioning service not available
                pass
            except Exception as e:
                logger.warning(f"Failed to create version for {file_path}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return False
            
    async def read_file(self, file_path: str) -> Optional[str]:
        """Read content from a file in the workspace."""
        try:
            full_path = self.workspace_dir / file_path
            if not full_path.exists():
                return None
                
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
            
    def list_files(self, directory: str = ".") -> List[str]:
        """List files in a directory."""
        try:
            full_path = self.workspace_dir / directory
            if not full_path.exists():
                return []
                
            files = []
            for item in full_path.rglob("*"):
                relative_path = item.relative_to(self.workspace_dir)
                if item.is_file():
                    files.append(str(relative_path))
                elif item.is_dir():
                    files.append(str(relative_path) + "/")
            return sorted(files)
        except Exception as e:
            logger.error(f"Error listing files in {directory}: {e}")
            return []
            
    async def cleanup(self):
        """Clean up all running processes."""
        for process_id in list(self.processes.keys()):
            await self.terminate_process(process_id)
        logger.info("LocalService cleanup completed")


# Global instance
local_service = LocalService()