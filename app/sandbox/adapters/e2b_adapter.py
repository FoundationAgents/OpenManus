"""E2B sandbox adapter."""

import asyncio
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseSandboxAdapter, ExecutionResult, SandboxInfo, SandboxStatus

try:
    # Try to import e2b
    from e2b_code_interpreter import CodeInterpreter
except ImportError:
    CodeInterpreter = None


class E2BSandboxAdapter(BaseSandboxAdapter):
    """E2B sandbox adapter."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        if not CodeInterpreter:
            raise ImportError(
                "e2b-code-interpreter package required: pip install e2b-code-interpreter"
            )

        self.api_key = self.config.get("api_key") or os.getenv("E2B_API_KEY")
        self.template = self.config.get("template", "base")

        if not self.api_key:
            raise ValueError(
                "E2B API key required (set E2B_API_KEY env var or provide in config)"
            )

        self._e2b_sandboxes: Dict[str, CodeInterpreter] = {}

    async def create_sandbox(self, **kwargs) -> str:
        """Create E2B sandbox."""
        try:
            template = kwargs.get("template", self.template)

            # Create E2B CodeInterpreter instance
            sandbox = CodeInterpreter(api_key=self.api_key, template=template)

            # Start the sandbox
            await sandbox.astart()

            sandbox_id = sandbox.id
            self._e2b_sandboxes[sandbox_id] = sandbox

            # Install additional packages if specified
            init_commands = kwargs.get("init_commands", [])
            for command in init_commands:
                await sandbox.process.astart_and_wait(command)

            # Install browser automation packages by default
            await sandbox.process.astart_and_wait(
                "pip install playwright selenium httpx beautifulsoup4"
            )

            # Install playwright browsers
            await sandbox.process.astart_and_wait(
                "python -m playwright install chromium"
            )

            # Create sandbox info
            info = SandboxInfo(
                id=sandbox_id,
                status=SandboxStatus.RUNNING,
                image=template,
                created_at=datetime.now().isoformat(),
                urls={},  # E2B doesn't expose direct URLs
                metadata={
                    "backend": "e2b",
                    "template": template,
                    "api_key_suffix": (
                        self.api_key[-4:] if self.api_key else ""
                    ),  # Last 4 chars for reference
                },
            )

            self._update_sandbox_info(sandbox_id, info)
            return sandbox_id

        except Exception as e:
            raise RuntimeError(f"Failed to create E2B sandbox: {e}")

    async def get_sandbox_info(self, sandbox_id: str) -> SandboxInfo:
        """Get E2B sandbox information."""
        if sandbox_id in self._active_sandboxes:
            return self._active_sandboxes[sandbox_id]
        else:
            raise ValueError(f"Sandbox {sandbox_id} not found")

    async def execute_command(
        self, sandbox_id: str, command: str, **kwargs
    ) -> ExecutionResult:
        """Execute command in E2B sandbox."""
        sandbox = self._e2b_sandboxes.get(sandbox_id)
        if not sandbox:
            raise ValueError(f"Sandbox {sandbox_id} not found")

        try:
            start_time = time.time()

            # Execute command using E2B process API
            process = await sandbox.process.astart_and_wait(
                command, timeout=kwargs.get("timeout", 60)
            )

            execution_time = time.time() - start_time

            return ExecutionResult(
                stdout=process.stdout,
                stderr=process.stderr,
                exit_code=process.exit_code,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                stdout="", stderr=str(e), exit_code=1, execution_time=execution_time
            )

    async def write_file(self, sandbox_id: str, path: str, content: str) -> None:
        """Write file to E2B sandbox."""
        sandbox = self._e2b_sandboxes.get(sandbox_id)
        if not sandbox:
            raise ValueError(f"Sandbox {sandbox_id} not found")

        try:
            await sandbox.files.awrite(path, content)
        except Exception as e:
            raise RuntimeError(f"Failed to write file {path}: {e}")

    async def read_file(self, sandbox_id: str, path: str) -> str:
        """Read file from E2B sandbox."""
        sandbox = self._e2b_sandboxes.get(sandbox_id)
        if not sandbox:
            raise ValueError(f"Sandbox {sandbox_id} not found")

        try:
            return await sandbox.files.aread(path)
        except Exception as e:
            if "No such file" in str(e) or "not found" in str(e).lower():
                raise FileNotFoundError(f"File not found: {path}")
            else:
                raise RuntimeError(f"Failed to read file {path}: {e}")

    async def list_files(self, sandbox_id: str, path: str = "/") -> List[str]:
        """List files in E2B sandbox directory."""
        sandbox = self._e2b_sandboxes.get(sandbox_id)
        if not sandbox:
            raise ValueError(f"Sandbox {sandbox_id} not found")

        try:
            files = await sandbox.files.alist(path)
            return [f.name for f in files if f.type == "file" or f.type == "directory"]
        except Exception as e:
            raise RuntimeError(f"Failed to list files in {path}: {e}")

    async def start_sandbox(self, sandbox_id: str) -> None:
        """Start a stopped E2B sandbox."""
        # E2B sandboxes are always running when created
        # This is a no-op, just update status
        info = await self.get_sandbox_info(sandbox_id)
        info.status = SandboxStatus.RUNNING
        self._update_sandbox_info(sandbox_id, info)

    async def stop_sandbox(self, sandbox_id: str) -> None:
        """Stop a running E2B sandbox."""
        # E2B doesn't have stop/start functionality
        # We'll just update the status
        info = await self.get_sandbox_info(sandbox_id)
        info.status = SandboxStatus.STOPPED
        self._update_sandbox_info(sandbox_id, info)

    async def destroy_sandbox(self, sandbox_id: str) -> None:
        """Completely destroy E2B sandbox."""
        try:
            if sandbox_id in self._e2b_sandboxes:
                sandbox = self._e2b_sandboxes[sandbox_id]

                # Close the E2B sandbox
                await sandbox.aclose()
                del self._e2b_sandboxes[sandbox_id]

            # Update status
            if sandbox_id in self._active_sandboxes:
                info = self._active_sandboxes[sandbox_id]
                info.status = SandboxStatus.DESTROYED
                self._remove_sandbox_info(sandbox_id)

        except Exception as e:
            raise RuntimeError(f"Failed to destroy E2B sandbox {sandbox_id}: {e}")

    async def execute_python(self, sandbox_id: str, code: str) -> ExecutionResult:
        """Execute Python code in E2B sandbox (specialized method)."""
        sandbox = self._e2b_sandboxes.get(sandbox_id)
        if not sandbox:
            raise ValueError(f"Sandbox {sandbox_id} not found")

        try:
            start_time = time.time()

            # Use E2B's specialized code execution
            execution = await sandbox.code.arun(code)

            execution_time = time.time() - start_time

            # Combine all outputs
            stdout_parts = []
            stderr_parts = []

            for result in execution.results:
                if result.type == "text":
                    stdout_parts.append(result.text)
                elif result.type == "error":
                    stderr_parts.append(result.traceback)

            return ExecutionResult(
                stdout="\n".join(stdout_parts),
                stderr="\n".join(stderr_parts),
                exit_code=1 if stderr_parts else 0,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                stdout="", stderr=str(e), exit_code=1, execution_time=execution_time
            )
