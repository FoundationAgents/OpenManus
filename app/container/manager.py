import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import docker
from docker.errors import DockerException
from pydantic import BaseModel, Field

from app.logger import logger


class ContainerConfig(BaseModel):
    """Container configuration model."""

    image: str
    name: str
    command: Optional[str] = None
    environment: Dict[str, str] = Field(default_factory=dict)
    volumes: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    ports: Dict[str, str] = Field(default_factory=dict)
    network: str = "openmanus-container-network"
    memory_limit: str = "1g"
    cpu_limit: float = 1.0
    restart_policy: str = "no"
    user: str = "nobody"
    stdin_open: bool = True
    tty: bool = True


class ContainerManager:
    """Manager for user containers with security and resource limits."""

    def __init__(self):
        self.client = docker.from_env()
        self.container_data_dir = os.getenv("CONTAINER_DATA_DIR", "/container_data")
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Ensure container data directory exists."""
        Path(self.container_data_dir).mkdir(parents=True, exist_ok=True)

    async def create_container(self, config: ContainerConfig) -> str:
        """Create a new container with security constraints."""
        try:
            # Generate unique container name
            container_name = f"user-container-{uuid.uuid4().hex[:8]}"

            # Create container data directory
            container_dir = Path(self.container_data_dir) / container_name
            container_dir.mkdir(parents=True, exist_ok=True)

            # Prepare volumes
            volumes = {str(container_dir): {"bind": "/data", "mode": "rw"}}
            volumes.update(config.volumes)

            # Create container
            container = self.client.containers.create(
                image=config.image,
                name=container_name,
                command=config.command,
                environment=config.environment,
                volumes=volumes,
                ports=config.ports,
                network=config.network,
                mem_limit=config.memory_limit,
                cpu_quota=int(config.cpu_limit * 100000),
                restart_policy={"Name": config.restart_policy},
                user=config.user,
                cap_drop=["ALL"],
                security_opt=["no-new-privileges"],
                read_only=True,
                tmpfs={"/tmp": "rw,noexec,nosuid,size=100m"},
                stdin_open=config.stdin_open,
                tty=config.tty,
            )

            # Start container
            container.start()

            # Save container metadata
            metadata = {
                "id": container.id,
                "name": container_name,
                "image": config.image,
                "created_at": datetime.utcnow().isoformat(),
                "status": "running",
            }
            with open(container_dir / "metadata.json", "w") as f:
                json.dump(metadata, f)

            return container_name

        except DockerException as e:
            logger.error(f"Failed to create container: {str(e)}")
            raise

    async def attach_to_container(
        self, container_name: str
    ) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Attach to container's stdio streams."""
        try:
            container = self.client.containers.get(container_name)

            # Create async streams
            reader = asyncio.StreamReader()
            writer = asyncio.StreamWriter(
                asyncio.StreamReader(),
                asyncio.StreamWriter,
                None,
                asyncio.get_event_loop(),
            )

            # Attach to container
            socket = container.attach_socket(
                params={"stdin": 1, "stdout": 1, "stderr": 1, "stream": 1}
            )

            # Create transport
            transport, protocol = await asyncio.get_event_loop().create_connection(
                lambda: asyncio.StreamReaderProtocol(reader), sock=socket
            )

            return reader, writer

        except DockerException as e:
            logger.error(f"Failed to attach to container {container_name}: {str(e)}")
            raise

    async def exec_command(self, container_name: str, command: str) -> str:
        """Execute a command in the container and return output."""
        try:
            container = self.client.containers.get(container_name)
            result = container.exec_run(
                cmd=command, stdout=True, stderr=True, stdin=False, tty=False
            )
            return result.output.decode()
        except DockerException as e:
            logger.error(
                f"Failed to execute command in container {container_name}: {str(e)}"
            )
            raise

    async def stop_container(self, container_name: str) -> bool:
        """Stop a running container."""
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            container.remove()

            # Update metadata
            container_dir = Path(self.container_data_dir) / container_name
            if container_dir.exists():
                metadata_path = container_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    metadata["status"] = "stopped"
                    metadata["stopped_at"] = datetime.utcnow().isoformat()
                    with open(metadata_path, "w") as f:
                        json.dump(metadata, f)

            return True
        except DockerException as e:
            logger.error(f"Failed to stop container {container_name}: {str(e)}")
            return False

    async def get_container_status(self, container_name: str) -> Optional[Dict]:
        """Get container status and metadata."""
        try:
            container_dir = Path(self.container_data_dir) / container_name
            metadata_path = container_dir / "metadata.json"

            if not metadata_path.exists():
                return None

            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            container = self.client.containers.get(container_name)
            metadata["status"] = container.status
            metadata["logs"] = container.logs().decode()

            return metadata
        except DockerException as e:
            logger.error(f"Failed to get container status {container_name}: {str(e)}")
            return None

    async def list_containers(self) -> List[Dict]:
        """List all user containers."""
        containers = []
        for container_dir in Path(self.container_data_dir).iterdir():
            if container_dir.is_dir():
                metadata_path = container_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    containers.append(metadata)
        return containers

    async def cleanup_old_containers(self, max_age_hours: int = 24):
        """Clean up containers older than specified hours."""
        now = datetime.utcnow()
        for container_dir in Path(self.container_data_dir).iterdir():
            if container_dir.is_dir():
                metadata_path = container_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    created_at = datetime.fromisoformat(metadata["created_at"])
                    age_hours = (now - created_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        await self.stop_container(metadata["name"])
