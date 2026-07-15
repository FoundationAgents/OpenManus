"""Persistent per-conversation Docker sandbox runtime."""

from __future__ import annotations

import asyncio
import io
import os
import re
import shlex
import tarfile
from pathlib import Path
from typing import Any, Optional

import docker
from docker.errors import APIError, NotFound

from app.config import SandboxSettings


class ConversationSandbox:
    """A Docker-backed computer for one conversation.

    The container persists across follow-up tasks and mounts exactly one
    conversation workspace at /workspace so artifacts remain visible to the UI.
    """

    def __init__(
        self,
        conversation_id: str,
        host_workspace: Path,
        config: SandboxSettings,
    ) -> None:
        self.conversation_id = conversation_id
        self.host_workspace = host_workspace.resolve()
        self.config = config
        self.client = docker.from_env()
        self.api = self.client.api
        self.container = None
        safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", conversation_id)[:80]
        self.name = f"openmanus_sandbox_{safe_id}"

    async def ensure(self) -> "ConversationSandbox":
        self.host_workspace.mkdir(parents=True, exist_ok=True)
        try:
            self.container = await asyncio.to_thread(
                self.client.containers.get, self.name
            )
            await self._start_if_needed()
            return self
        except NotFound:
            pass

        return await self._create_container()

    async def _create_container(self, _retried: bool = False) -> "ConversationSandbox":
        """Create a fresh sandbox container, auto-removing stale conflicts."""
        binds = {
            str(self.host_workspace): {
                "bind": self.config.work_dir,
                "mode": "rw",
            }
        }
        if self.config.docker_socket_enabled and os.path.exists("/var/run/docker.sock"):
            binds["/var/run/docker.sock"] = {
                "bind": "/var/run/docker.sock",
                "mode": "rw",
            }
        host_config = self.api.create_host_config(
            mem_limit=self.config.memory_limit,
            cpu_period=100000,
            cpu_quota=int(100000 * self.config.cpu_limit),
            network_mode="bridge" if self.config.network_enabled else "none",
            binds=binds,
        )
        try:
            container_data = await asyncio.to_thread(
                self.api.create_container,
                image=self.config.image,
                command="tail -f /dev/null",
                hostname="openmanus-sandbox",
                working_dir=self.config.work_dir,
                environment={"DOCKER_HOST": "unix:///var/run/docker.sock"},
                host_config=host_config,
                name=self.name,
                labels={
                    "openmanus.kind": "conversation-sandbox",
                    "openmanus.conversation_id": self.conversation_id,
                },
                tty=True,
                detach=True,
            )
        except APIError as exc:
            if exc.status_code == 409 and not _retried:
                # Stale container with the same name – remove it and retry once.
                try:
                    stale = await asyncio.to_thread(
                        self.client.containers.get, self.name
                    )
                    await asyncio.to_thread(stale.remove, force=True)
                except Exception:
                    pass
                return await self._create_container(_retried=True)
            raise
        self.container = self.client.containers.get(container_data["Id"])
        await asyncio.to_thread(self.container.start)
        return self

    async def status(self) -> dict[str, Any]:
        try:
            self.container = await asyncio.to_thread(
                self.client.containers.get, self.name
            )
        except NotFound:
            return {"exists": False, "status": "missing", "container": None}
        await asyncio.to_thread(self.container.reload)
        return {
            "exists": True,
            "status": self.container.status,
            "container": {
                "id": self.container.short_id,
                "name": self.container.name,
                "image": ",".join(self.container.image.tags)
                if self.container.image.tags
                else self.container.image.short_id,
            },
        }

    async def pause(self) -> None:
        await self.ensure()
        await asyncio.to_thread(self.container.pause)

    async def resume(self) -> None:
        try:
            self.container = await asyncio.to_thread(
                self.client.containers.get, self.name
            )
        except NotFound:
            await self.ensure()
            return
        await asyncio.to_thread(self.container.reload)
        if self.container.status == "paused":
            await asyncio.to_thread(self.container.unpause)
        elif self.container.status != "running":
            await asyncio.to_thread(self.container.start)

    async def delete(self) -> None:
        try:
            self.container = await asyncio.to_thread(
                self.client.containers.get, self.name
            )
        except NotFound:
            return
        await asyncio.to_thread(self.container.remove, force=True)

    async def _start_if_needed(self) -> None:
        assert self.container is not None
        await asyncio.to_thread(self.container.reload)
        if self.container.status == "paused":
            await asyncio.to_thread(self.container.unpause)
            return
        if self.container.status != "running":
            await asyncio.to_thread(self.container.start)

    def container_path(self, path: str | os.PathLike[str]) -> str:
        raw = str(path)
        if raw.startswith(str(self.host_workspace)):
            rel = os.path.relpath(raw, self.host_workspace)
            return os.path.join(self.config.work_dir, rel)
        if raw == "/workspace" or raw.startswith("/workspace/"):
            return raw
        if os.path.isabs(raw):
            return raw
        return os.path.join(self.config.work_dir, raw)

    async def run(
        self,
        command: str,
        timeout: Optional[int] = None,
        task: Optional[Any] = None,
        tool_call: Optional[dict] = None,
        tool_name: str = "bash",
    ) -> tuple[int, str, str]:
        await self.ensure()
        seconds = int(timeout or self.config.timeout or 300)
        wrapped = f"timeout -k 5s {seconds}s bash -lc {shlex.quote(command)}"

        def _run() -> tuple[int, str, str]:
            exec_data = self.api.exec_create(
                self.container.id,
                ["bash", "-lc", wrapped],
                stdout=True,
                stderr=True,
                tty=False,
                workdir=self.config.work_dir,
                environment={"PYTHONUNBUFFERED": "1"},
            )
            exec_id = exec_data["Id"]
            stdout_parts: list[str] = []
            stderr_parts: list[str] = []
            for stdout, stderr in self.api.exec_start(exec_id, stream=True, demux=True):
                if stdout:
                    text = stdout.decode("utf-8", errors="replace")
                    stdout_parts.append(text)
                    if task is not None:
                        task.emit(
                            "terminal_output",
                            {
                                "id": (tool_call or {}).get("id"),
                                "name": (tool_call or {}).get("name", tool_name),
                                "stream": "stdout",
                                "chunk": text,
                            },
                        )
                if stderr:
                    text = stderr.decode("utf-8", errors="replace")
                    stderr_parts.append(text)
                    if task is not None:
                        task.emit(
                            "terminal_output",
                            {
                                "id": (tool_call or {}).get("id"),
                                "name": (tool_call or {}).get("name", tool_name),
                                "stream": "stderr",
                                "chunk": text,
                            },
                        )
            inspect = self.api.exec_inspect(exec_id)
            return (
                int(inspect.get("ExitCode") or 0),
                "".join(stdout_parts),
                "".join(stderr_parts),
            )

        return await asyncio.to_thread(_run)

    async def read_file(self, path: str | os.PathLike[str]) -> str:
        container_path = self.container_path(path)
        code, stdout, stderr = await self.run(
            f"cat {shlex.quote(container_path)}", timeout=30
        )
        if code != 0:
            raise FileNotFoundError(stderr or f"Could not read {container_path}")
        return stdout

    async def write_file(self, path: str | os.PathLike[str], content: str) -> None:
        container_path = self.container_path(path)
        parent_dir = os.path.dirname(container_path) or self.config.work_dir
        await self.run(f"mkdir -p {shlex.quote(parent_dir)}", timeout=30)

        def _write() -> None:
            data = content.encode("utf-8")
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                tarinfo = tarfile.TarInfo(name=os.path.basename(container_path))
                tarinfo.size = len(data)
                tar.addfile(tarinfo, io.BytesIO(data))
            tar_stream.seek(0)
            self.container.put_archive(parent_dir, tar_stream.read())

        await asyncio.to_thread(_write)

    def host_path_for_container_path(self, path: str) -> Optional[Path]:
        if path == self.config.work_dir:
            return self.host_workspace
        prefix = self.config.work_dir.rstrip("/") + "/"
        if path.startswith(prefix):
            rel = path[len(prefix) :]
            return self.host_workspace / rel
        return None

    async def exists(self, path: str | os.PathLike[str]) -> bool:
        code, _, _ = await self.run(
            f"test -e {shlex.quote(self.container_path(path))}", timeout=10
        )
        return code == 0

    async def is_directory(self, path: str | os.PathLike[str]) -> bool:
        code, _, _ = await self.run(
            f"test -d {shlex.quote(self.container_path(path))}", timeout=10
        )
        return code == 0

    async def list_processes(self) -> list[dict[str, Any]]:
        """Return processes running inside this conversation container."""
        await self.ensure()
        code, stdout, _ = await self.run(
            "ps -eo pid=,ppid=,stat=,etime=,comm=,args= | sed '/ ps -eo /d'",
            timeout=10,
        )
        if code != 0:
            return []
        listen_ports = await self._list_listening_ports()

        processes: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            parts = line.strip().split(None, 5)
            if len(parts) < 6:
                continue
            pid, ppid, stat, elapsed, command, args = parts
            if command in {"ps", "sed"}:
                continue
            processes.append(
                {
                    "pid": int(pid),
                    "ppid": int(ppid),
                    "stat": stat,
                    "elapsed": elapsed,
                    "command": command,
                    "args": args,
                    "ports": listen_ports.get(int(pid), []),
                    "zombie": "Z" in stat,
                    "protected": int(pid) == 1
                    or args == "tail -f /dev/null"
                    or "Z" in stat,
                }
            )
        return processes

    async def list_exposed_urls(self) -> list[dict[str, Any]]:
        """Return likely HTTP URLs exposed by processes in the sandbox."""
        await self.ensure()
        await asyncio.to_thread(self.container.reload)
        attrs = self.container.attrs or {}
        networks = attrs.get("NetworkSettings", {}).get("Networks", {})
        ip_address = ""
        for network in networks.values():
            ip_address = network.get("IPAddress") or ip_address
        ports_by_pid = await self._list_listening_ports()
        processes = await self.list_processes()
        command_by_pid = {item["pid"]: item for item in processes}
        urls: list[dict[str, Any]] = []
        seen: set[str] = set()
        for pid, ports in ports_by_pid.items():
            process = command_by_pid.get(pid, {})
            for port in ports:
                if port in seen:
                    continue
                seen.add(port)
                urls.append(
                    {
                        "port": port,
                        "url": f"http://{ip_address}:{port}/" if ip_address else "",
                        "pid": pid,
                        "command": process.get("command", ""),
                        "args": process.get("args", ""),
                    }
                )
        return urls

    async def _list_listening_ports(self) -> dict[int, list[str]]:
        code, stdout, _ = await self.run("ss -tlnp 2>/dev/null || true", timeout=10)
        if code != 0:
            return {}
        ports_by_pid: dict[int, list[str]] = {}
        for line in stdout.splitlines():
            if "pid=" not in line or "LISTEN" not in line:
                continue
            pid_match = re.search(r"pid=(\d+)", line)
            address = line.split()[3] if len(line.split()) > 3 else ""
            port_match = re.search(r":(\d+)$", address)
            if not pid_match or not port_match:
                continue
            ports_by_pid.setdefault(int(pid_match.group(1)), []).append(
                port_match.group(1)
            )
        return ports_by_pid

    async def kill_process(self, pid: int, signal: str = "TERM") -> None:
        """Kill one process inside this conversation container."""
        if pid <= 1:
            raise ValueError("Refusing to kill the sandbox init process")
        safe_signal = re.sub(r"[^A-Z0-9]", "", signal.upper()) or "TERM"
        code, _, stderr = await self.run(
            f"kill -s {shlex.quote(safe_signal)} {int(pid)}", timeout=10
        )
        if code != 0:
            raise RuntimeError(stderr or f"Could not kill process {pid}")

    async def list_docker_containers(self) -> list[dict[str, Any]]:
        """Return Docker containers visible from the sandbox Docker socket."""
        await self.ensure()
        command = "docker ps --format " + shlex.quote(
            "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Command}}"
        )
        code, stdout, _ = await self.run(command, timeout=15)
        if code != 0:
            return []

        containers: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            container_id, name, image, status, command_text = parts[:5]
            protected = (
                name.startswith("openmanus-")
                or name == self.name
                or name.startswith("openmanus_sandbox_")
            )
            containers.append(
                {
                    "id": container_id,
                    "name": name,
                    "image": image,
                    "status": status,
                    "command": command_text,
                    "protected": protected,
                }
            )
        return containers

    async def stop_docker_container(self, container_id: str) -> None:
        """Stop a Docker container visible from the sandbox socket."""
        containers = await self.list_docker_containers()
        target = next(
            (
                item
                for item in containers
                if item["id"].startswith(container_id) or item["name"] == container_id
            ),
            None,
        )
        if target is None:
            raise ValueError("Container not found")
        if target.get("protected"):
            raise ValueError("Refusing to stop an OpenManus system container")
        code, _, stderr = await self.run(
            f"docker stop {shlex.quote(container_id)}", timeout=30
        )
        if code != 0:
            raise RuntimeError(stderr or f"Could not stop container {container_id}")
