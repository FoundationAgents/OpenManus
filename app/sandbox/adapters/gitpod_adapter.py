"""GitPod self-hosted sandbox adapter."""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseSandboxAdapter, ExecutionResult, SandboxInfo, SandboxStatus

try:
    import httpx
except ImportError:
    httpx = None


class GitPodSandboxAdapter(BaseSandboxAdapter):
    """GitPod self-hosted sandbox adapter."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        if not httpx:
            raise ImportError(
                "httpx package required for GitPod adapter: pip install httpx"
            )

        self.gitpod_url = self.config.get("gitpod_url", "https://gitpod.local")
        self.api_token = self.config.get("gitpod_token")
        self.default_image = self.config.get("image", "gitpod/workspace-full-vnc")

        if not self.api_token:
            raise ValueError("GitPod API token required in config")

    async def create_sandbox(self, **kwargs) -> str:
        """Create GitPod workspace."""
        workspace_id = str(uuid.uuid4())
        vnc_password = kwargs.get("password", "123456")

        workspace_config = {
            "contextUrl": kwargs.get("context_url", "github.com/empty-repo"),
            "configuration": {
                "image": kwargs.get("image", self.default_image),
                "tasks": [{"init": self._get_init_script(vnc_password)}],
                "ports": [
                    {"port": 6080, "onOpen": "ignore"},  # VNC
                    {"port": 8080, "onOpen": "ignore"},  # Web
                    {"port": 9222, "onOpen": "ignore"},  # Chrome Debug
                ],
                "vscode": {"extensions": ["ms-python.python", "ms-vscode.vscode-json"]},
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.gitpod_url}/api/v1/workspaces",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    json=workspace_config,
                )

                if response.status_code not in [200, 201]:
                    raise RuntimeError(
                        f"Failed to create GitPod workspace: {response.text}"
                    )

                workspace = response.json()
                actual_workspace_id = workspace.get("id", workspace_id)

                # Wait for workspace to be ready
                await self._wait_for_ready(actual_workspace_id)

                # Get workspace URLs
                urls = await self._get_workspace_urls(actual_workspace_id)

                # Create sandbox info
                info = SandboxInfo(
                    id=actual_workspace_id,
                    status=SandboxStatus.RUNNING,
                    image=kwargs.get("image", self.default_image),
                    created_at=datetime.now().isoformat(),
                    urls=urls,
                    metadata={
                        "backend": "gitpod",
                        "vnc_password": vnc_password,
                        "workspace_config": workspace_config,
                    },
                )

                self._update_sandbox_info(actual_workspace_id, info)
                return actual_workspace_id

        except Exception as e:
            raise RuntimeError(f"Failed to create GitPod workspace: {e}")

    def _get_init_script(self, vnc_password: str) -> str:
        """Generate initialization script for GitPod workspace."""
        return f"""
            # Update system
            sudo apt-get update -qq

            # Install Chrome
            wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
            echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
            sudo apt-get update -qq
            sudo apt-get install -y google-chrome-stable

            # Install VNC server
            sudo apt-get install -y tigervnc-standalone-server tigervnc-common

            # Setup VNC password
            mkdir -p ~/.vnc
            echo "{vnc_password}" | vncpasswd -f > ~/.vnc/passwd
            chmod 600 ~/.vnc/passwd

            # Create VNC startup script
            cat > ~/.vnc/xstartup << 'XEOF'
#!/bin/bash
export XKL_XMODMAP_DISABLE=1
export XDG_CURRENT_DESKTOP="XFCE"
export XDG_SESSION_DESKTOP="xfce"
unset SESSION_MANAGER
startxfce4 &
XEOF
            chmod +x ~/.vnc/xstartup

            # Start VNC server
            vncserver :1 -geometry 1024x768 -depth 24 -localhost no &

            # Setup environment
            export CHROME_DEBUGGING_PORT=9222
            export DISPLAY=:1

            # Install Python packages
            pip install --quiet playwright selenium browser-use httpx

            # Install Playwright browsers
            python -m playwright install chromium

            # Setup supervisord for service management
            sudo apt-get install -y supervisor

            # Create supervisor config for services
            sudo tee /etc/supervisor/conf.d/sandbox-services.conf > /dev/null << 'SEOF'
[program:vnc]
command=vncserver :1 -fg -geometry 1024x768 -depth 24 -localhost no
autorestart=true
user=gitpod

[program:chrome-debug]
command=google-chrome --remote-debugging-port=9222 --no-sandbox --disable-dev-shm-usage --headless --disable-gpu
autorestart=true
user=gitpod
SEOF

            sudo supervisorctl reread
            sudo supervisorctl update

            echo "GitPod sandbox initialized successfully!"
        """

    async def _wait_for_ready(self, workspace_id: str, timeout: int = 300):
        """Wait for workspace to be ready."""
        start_time = asyncio.get_event_loop().time()

        async with httpx.AsyncClient(timeout=10.0) as client:
            while True:
                try:
                    response = await client.get(
                        f"{self.gitpod_url}/api/v1/workspaces/{workspace_id}",
                        headers={"Authorization": f"Bearer {self.api_token}"},
                    )

                    if response.status_code == 200:
                        workspace = response.json()
                        phase = workspace.get("status", {}).get("phase")
                        if phase == "running":
                            return
                        elif phase == "stopped" or phase == "error":
                            raise RuntimeError(f"Workspace failed to start: {phase}")

                except httpx.RequestError:
                    pass  # Retry on network errors

                if asyncio.get_event_loop().time() - start_time > timeout:
                    raise TimeoutError(
                        f"Workspace {workspace_id} not ready after {timeout}s"
                    )

                await asyncio.sleep(5)

    async def _get_workspace_urls(self, workspace_id: str) -> Dict[str, str]:
        """Get workspace URLs for VNC and web access."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.gitpod_url}/api/v1/workspaces/{workspace_id}",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                )

                if response.status_code == 200:
                    workspace = response.json()
                    exposed_ports = workspace.get("status", {}).get("exposedPorts", {})

                    urls = {}
                    if "6080" in exposed_ports:
                        urls["vnc"] = exposed_ports["6080"].get("url", "")
                    if "8080" in exposed_ports:
                        urls["web"] = exposed_ports["8080"].get("url", "")
                    if "3000" in exposed_ports:
                        urls["ide"] = exposed_ports["3000"].get("url", "")

                    return urls
        except Exception:
            pass

        return {}

    async def get_sandbox_info(self, sandbox_id: str) -> SandboxInfo:
        """Get GitPod workspace information."""
        if sandbox_id in self._active_sandboxes:
            # Update URLs in case they changed
            info = self._active_sandboxes[sandbox_id]
            info.urls = await self._get_workspace_urls(sandbox_id)
            return info
        else:
            raise ValueError(f"Sandbox {sandbox_id} not found")

    async def execute_command(
        self, sandbox_id: str, command: str, **kwargs
    ) -> ExecutionResult:
        """Execute command in GitPod workspace."""
        try:
            start_time = time.time()

            # Use GitPod terminal API (simplified implementation)
            async with httpx.AsyncClient(timeout=kwargs.get("timeout", 60)) as client:
                response = await client.post(
                    f"{self.gitpod_url}/api/v1/workspaces/{sandbox_id}/exec",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    json={"command": command},
                )

                execution_time = time.time() - start_time

                if response.status_code == 200:
                    result = response.json()
                    return ExecutionResult(
                        stdout=result.get("stdout", ""),
                        stderr=result.get("stderr", ""),
                        exit_code=result.get("exit_code", 0),
                        execution_time=execution_time,
                    )
                else:
                    return ExecutionResult(
                        stdout="",
                        stderr=f"API Error: {response.text}",
                        exit_code=1,
                        execution_time=execution_time,
                    )

        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time=time.time() - start_time,
            )

    async def write_file(self, sandbox_id: str, path: str, content: str) -> None:
        """Write file to GitPod workspace."""
        # Use GitPod file API
        info = await self.get_sandbox_info(sandbox_id)
        ide_url = info.urls.get("ide")

        if not ide_url:
            raise RuntimeError("IDE URL not available for file operations")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{ide_url}/api/fs{path}",
                content=content,
                headers={"Authorization": f"Bearer {self.api_token}"},
            )

            if response.status_code not in [200, 201]:
                raise RuntimeError(f"Failed to write file {path}: {response.text}")

    async def read_file(self, sandbox_id: str, path: str) -> str:
        """Read file from GitPod workspace."""
        info = await self.get_sandbox_info(sandbox_id)
        ide_url = info.urls.get("ide")

        if not ide_url:
            raise RuntimeError("IDE URL not available for file operations")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{ide_url}/api/fs{path}",
                headers={"Authorization": f"Bearer {self.api_token}"},
            )

            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                raise FileNotFoundError(f"File not found: {path}")
            else:
                raise RuntimeError(f"Failed to read file {path}: {response.text}")

    async def list_files(self, sandbox_id: str, path: str = "/workspace") -> List[str]:
        """List files in GitPod workspace directory."""
        result = await self.execute_command(sandbox_id, f"ls -la {path}", timeout=30)

        if result.exit_code != 0:
            raise FileNotFoundError(f"Directory {path} not found: {result.stderr}")

        # Parse ls output
        lines = result.stdout.strip().split("\n")
        files = []
        for line in lines[1:]:  # Skip first line (total)
            if line.strip():
                parts = line.split()
                if len(parts) >= 9:
                    filename = " ".join(parts[8:])
                    if filename not in [".", ".."]:
                        files.append(filename)

        return files

    async def start_sandbox(self, sandbox_id: str) -> None:
        """Start a stopped GitPod workspace."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.gitpod_url}/api/v1/workspaces/{sandbox_id}/start",
                headers={"Authorization": f"Bearer {self.api_token}"},
            )

            if response.status_code not in [200, 202]:
                raise RuntimeError(f"Failed to start workspace: {response.text}")

            # Wait for it to be ready
            await self._wait_for_ready(sandbox_id)

            # Update status
            info = await self.get_sandbox_info(sandbox_id)
            info.status = SandboxStatus.RUNNING
            self._update_sandbox_info(sandbox_id, info)

    async def stop_sandbox(self, sandbox_id: str) -> None:
        """Stop a running GitPod workspace."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.gitpod_url}/api/v1/workspaces/{sandbox_id}/stop",
                headers={"Authorization": f"Bearer {self.api_token}"},
            )

            if response.status_code not in [200, 202]:
                raise RuntimeError(f"Failed to stop workspace: {response.text}")

            # Update status
            info = await self.get_sandbox_info(sandbox_id)
            info.status = SandboxStatus.STOPPED
            self._update_sandbox_info(sandbox_id, info)

    async def destroy_sandbox(self, sandbox_id: str) -> None:
        """Completely destroy GitPod workspace."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.gitpod_url}/api/v1/workspaces/{sandbox_id}",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                )

                if response.status_code not in [200, 204, 404]:  # 404 = already deleted
                    raise RuntimeError(f"Failed to delete workspace: {response.text}")

            # Update status
            if sandbox_id in self._active_sandboxes:
                info = self._active_sandboxes[sandbox_id]
                info.status = SandboxStatus.DESTROYED
                self._remove_sandbox_info(sandbox_id)

        except Exception as e:
            raise RuntimeError(f"Failed to destroy GitPod workspace {sandbox_id}: {e}")
