"""System resource catalog with auto-discovery and caching support."""

from __future__ import annotations

import asyncio
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import aiosqlite
from enum import Enum
from pydantic import BaseModel, Field, validator

from app.config import ResourceCatalogSettings, config
from app.database.database_service import DatabaseService, database_service
from app.logger import logger

try:  # pragma: no cover - winreg not available on all platforms
    import winreg as winreg_module
except ImportError:  # pragma: no cover - fallback for non-Windows systems
    winreg_module = None

DEFAULT_DEBOUNCE_SECONDS = 300
DEFAULT_WATCH_INTERVAL_SECONDS = 900
MINIMUM_WATCH_INTERVAL_SECONDS = 30


def _path_exists(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        candidate = Path(path).expanduser()
        if candidate.exists():
            return str(candidate.resolve())
    except Exception:  # pragma: no cover - defensive coding
        return None
    return None


def _command_version(command: Sequence[str]) -> Optional[str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        output = completed.stdout or completed.stderr
        if not output:
            return None
        match = re.search(r"(\d+\.\d+(?:\.\d+)*)", output)
        if match:
            return match.group(1)
    except Exception:  # pragma: no cover - best effort only
        return None
    return None


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class ResourceType(str, Enum):
    COMPILER = "compiler"
    DEBUGGER = "debugger"
    TOOL = "tool"
    SDK = "sdk"
    RUNTIME = "runtime"
    IDE = "ide"
    SHELL = "shell"
    FRAMEWORK = "framework"


class ResourceRequirements(BaseModel):
    cpu: Optional[str] = None
    memory: Optional[str] = None
    gpu: Optional[str] = None
    disk: Optional[str] = None
    additional: Dict[str, str] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class ResourceMetadata(BaseModel):
    name: str
    resource_type: ResourceType
    version: Optional[str] = None
    install_path: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    min_requirements: Optional[ResourceRequirements] = None
    max_requirements: Optional[ResourceRequirements] = None
    capability_tags: List[str] = Field(default_factory=list)
    discovery_source: str = "unknown"
    available: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    @validator("install_path", pre=True)
    def _validate_path(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            return str(Path(value).expanduser())
        except Exception:  # pragma: no cover - defensive
            return value

    @validator("capability_tags", pre=True, always=True)
    def _normalize_capabilities(cls, value: Iterable[str]) -> List[str]:
        tags: List[str] = []
        for tag in value or []:
            lowered = str(tag).lower()
            if lowered not in tags:
                tags.append(lowered)
        return tags

    def normalized_key(self) -> Tuple[str, str]:
        path_key = (self.install_path or "").lower()
        return (self.name.lower(), path_key)


class BaseResourceLocator:
    name: str = "base"
    lookup_key: Optional[str] = None
    resource_type: ResourceType = ResourceType.TOOL
    capability_tags: Sequence[str] = ()
    discovery_source: str = "auto"

    def __init__(self, settings: Optional[ResourceCatalogSettings] = None):
        self.settings = settings
        self.lookup_key = self.lookup_key or self.name

    async def locate(self) -> List[ResourceMetadata]:
        return await asyncio.to_thread(self._locate)

    def _locate(self) -> List[ResourceMetadata]:  # pragma: no cover - interface
        raise NotImplementedError

    def known_paths(self) -> Sequence[str]:
        if not self.settings:
            return []
        return self.settings.known_install_paths.get(self.lookup_key or self.name, [])

    def _default_name(self) -> str:
        return self.name.replace("_", " ").title()

    def _build_metadata(
        self,
        *,
        name: Optional[str] = None,
        version: Optional[str] = None,
        install_path: Optional[str] = None,
        capability_tags: Optional[Sequence[str]] = None,
        discovery_source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResourceMetadata:
        return ResourceMetadata(
            name=name or self._default_name(),
            resource_type=self.resource_type,
            version=version,
            install_path=install_path,
            capability_tags=list(capability_tags or self.capability_tags),
            discovery_source=discovery_source or self.discovery_source,
            metadata=metadata or {},
        )

    def _append_resource(
        self,
        results: List[ResourceMetadata],
        seen: set,
        path: Optional[str],
        *,
        name: Optional[str] = None,
        version: Optional[str] = None,
        capability_tags: Optional[Sequence[str]] = None,
        discovery_source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        normalized = _path_exists(path)
        if not normalized:
            return
        key = normalized.lower()
        if key in seen:
            return
        seen.add(key)
        results.append(
            self._build_metadata(
                name=name,
                version=version,
                install_path=normalized,
                capability_tags=capability_tags,
                discovery_source=discovery_source,
                metadata=metadata,
            )
        )


class VisualStudioLocator(BaseResourceLocator):
    name = "visual_studio"
    resource_type = ResourceType.IDE
    capability_tags = ("c++", "c#", "ide", "debug", "gamedev", "windows")
    discovery_source = "windows_registry"

    def _locate(self) -> List[ResourceMetadata]:
        results: List[ResourceMetadata] = []
        seen: set = set()

        if sys.platform != "win32":
            return results

        winreg = winreg_module
        if winreg:
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\VisualStudio\SxS\VS7"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\SxS\VS7"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\VisualStudio\SxS\VS7"),
            ]
            for root, sub_key in registry_paths:
                try:
                    with winreg.OpenKey(root, sub_key) as key:
                        index = 0
                        while True:
                            try:
                                version, path, _ = winreg.EnumValue(key, index)
                            except OSError:
                                break
                            self._append_resource(
                                results,
                                seen,
                                path,
                                name=f"Visual Studio {version}",
                                version=version,
                            )
                            index += 1
                except OSError:
                    continue

        env_path = os.environ.get("VSINSTALLDIR")
        if env_path:
            version = os.environ.get("VisualStudioVersion")
            self._append_resource(
                results,
                seen,
                env_path,
                name="Visual Studio",
                version=version,
                discovery_source="environment",
            )

        for candidate in self.known_paths():
            self._append_resource(results, seen, candidate)

        return results


class CMakeLocator(BaseResourceLocator):
    name = "cmake"
    resource_type = ResourceType.TOOL
    capability_tags = ("c++", "build", "gamedev", "ci")
    discovery_source = "executable"

    def _locate(self) -> List[ResourceMetadata]:
        results: List[ResourceMetadata] = []
        seen: set = set()

        executable = shutil.which("cmake")
        if executable:
            version = _command_version([executable, "--version"])
            self._append_resource(
                results,
                seen,
                Path(executable).parent,
                name="CMake",
                version=version,
            )

        for env_key in ("CMAKE_ROOT", "CMAKE_HOME_DIRECTORY"):
            env_path = os.environ.get(env_key)
            if env_path:
                self._append_resource(
                    results,
                    seen,
                    env_path,
                    name="CMake",
                    discovery_source="environment",
                )

        common_paths = [
            Path("/usr/local/bin/cmake"),
            Path("/opt/cmake"),
            Path("C:/Program Files/CMake/bin"),
        ]
        for candidate in common_paths:
            self._append_resource(results, seen, candidate)

        for candidate in self.known_paths():
            self._append_resource(results, seen, candidate)

        return results


class GhidraLocator(BaseResourceLocator):
    name = "ghidra"
    resource_type = ResourceType.TOOL
    capability_tags = ("reverse_engineering", "analysis", "security")
    discovery_source = "filesystem"

    def _locate(self) -> List[ResourceMetadata]:
        results: List[ResourceMetadata] = []
        seen: set = set()

        env_path = os.environ.get("GHIDRA_HOME")
        if env_path:
            self._append_resource(
                results,
                seen,
                env_path,
                name="Ghidra",
                discovery_source="environment",
            )

        candidates = [
            Path.home() / "ghidra",
            Path("/opt/ghidra"),
            Path("C:/Program Files/ghidra"),
        ]
        for candidate in candidates:
            self._append_resource(results, seen, candidate)

        for candidate in self.known_paths():
            self._append_resource(results, seen, candidate)

        return results


class IDAProLocator(BaseResourceLocator):
    name = "ida_pro"
    resource_type = ResourceType.TOOL
    capability_tags = ("reverse_engineering", "debug", "windows")
    discovery_source = "filesystem"

    def _locate(self) -> List[ResourceMetadata]:
        results: List[ResourceMetadata] = []
        seen: set = set()

        env_path = os.environ.get("IDA_HOME")
        if env_path:
            self._append_resource(
                results,
                seen,
                env_path,
                name="IDA Pro",
                discovery_source="environment",
            )

        candidates = [
            Path("C:/Program Files/IDA Pro"),
            Path("C:/Program Files (x86)/IDA Pro"),
            Path.home() / "ida",
        ]
        for candidate in candidates:
            self._append_resource(results, seen, candidate)

        for candidate in self.known_paths():
            self._append_resource(results, seen, candidate)

        return results


class PythonLocator(BaseResourceLocator):
    name = "python"
    resource_type = ResourceType.RUNTIME
    capability_tags = ("python", "runtime", "scripting")
    discovery_source = "executable"

    def _locate(self) -> List[ResourceMetadata]:
        results: List[ResourceMetadata] = []
        seen: set = set()

        executables = set()
        if sys.executable:
            executables.add(sys.executable)

        for candidate in ("python", "python3", "python.exe", "py"):
            path = shutil.which(candidate)
            if path:
                executables.add(path)

        for executable in executables:
            parent = Path(executable).parent
            version = _command_version([executable, "--version"]) or platform.python_version()
            metadata = {"executable": executable}
            self._append_resource(
                results,
                seen,
                parent,
                name="Python",
                version=version,
                metadata=metadata,
            )

        for candidate in self.known_paths():
            self._append_resource(results, seen, candidate)

        return results


class CUDALocator(BaseResourceLocator):
    name = "cuda_toolkit"
    resource_type = ResourceType.SDK
    capability_tags = ("cuda", "gpu", "ml", "gamedev")
    discovery_source = "filesystem"

    def _locate(self) -> List[ResourceMetadata]:
        results: List[ResourceMetadata] = []
        seen: set = set()

        env_vars = ["CUDA_PATH", "CUDA_HOME"]
        for env in env_vars:
            env_path = os.environ.get(env)
            if env_path:
                self._append_resource(
                    results,
                    seen,
                    env_path,
                    name="CUDA Toolkit",
                    discovery_source="environment",
                )

        candidates = [
            Path("/usr/local/cuda"),
            Path("/usr/local/cuda-12"),
            Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA"),
        ]
        for candidate in candidates:
            self._append_resource(results, seen, candidate)

        for candidate in self.known_paths():
            self._append_resource(results, seen, candidate)

        return results


class PowerShellLocator(BaseResourceLocator):
    name = "powershell"
    resource_type = ResourceType.SHELL
    capability_tags = ("powershell", "automation", "windows")
    discovery_source = "executable"

    def _locate(self) -> List[ResourceMetadata]:
        results: List[ResourceMetadata] = []
        seen: set = set()

        if sys.platform == "win32":
            system_root = Path(os.environ.get("SystemRoot", "C:/Windows"))
            candidates = [
                system_root / "System32/WindowsPowerShell/v1.0",
                system_root / "SysWOW64/WindowsPowerShell/v1.0",
            ]
            for candidate in candidates:
                self._append_resource(
                    results,
                    seen,
                    candidate,
                    name="Windows PowerShell",
                )

        pwsh = shutil.which("pwsh")
        if pwsh:
            version = _command_version([pwsh, "--version"])
            self._append_resource(
                results,
                seen,
                Path(pwsh).parent,
                name="PowerShell",
                version=version,
            )

        for candidate in self.known_paths():
            self._append_resource(results, seen, candidate)

        return results


class DirectXSDKLocator(BaseResourceLocator):
    name = "directx_sdk"
    resource_type = ResourceType.SDK
    capability_tags = ("gamedev", "graphics", "windows", "sdk")
    discovery_source = "filesystem"

    def _locate(self) -> List[ResourceMetadata]:
        results: List[ResourceMetadata] = []
        seen: set = set()

        if sys.platform != "win32":
            return results

        env_path = os.environ.get("DXSDK_DIR")
        if env_path:
            self._append_resource(
                results,
                seen,
                env_path,
                name="DirectX SDK",
                discovery_source="environment",
            )

        candidates = [
            Path("C:/Program Files (x86)/Microsoft DirectX SDK (June 2010)"),
            Path("C:/Program Files/Microsoft DirectX SDK"),
        ]
        for candidate in candidates:
            self._append_resource(results, seen, candidate)

        for candidate in self.known_paths():
            self._append_resource(results, seen, candidate)

        return results


def _build_default_locators(settings: Optional[ResourceCatalogSettings]) -> List[BaseResourceLocator]:
    return [
        VisualStudioLocator(settings),
        CMakeLocator(settings),
        GhidraLocator(settings),
        IDAProLocator(settings),
        PythonLocator(settings),
        CUDALocator(settings),
        PowerShellLocator(settings),
        DirectXSDKLocator(settings),
    ]


class SystemResourceCatalog:
    """Discovers and caches system resources with query support."""

    def __init__(
        self,
        db_service: Optional[DatabaseService] = None,
        settings: Optional[ResourceCatalogSettings] = None,
        locators: Optional[Sequence[BaseResourceLocator]] = None,
    ):
        self.db_service = db_service or database_service
        self.settings = settings or getattr(config, "resource_catalog", ResourceCatalogSettings())
        self.settings.debounce_seconds = max(self.settings.debounce_seconds or 0, DEFAULT_DEBOUNCE_SECONDS)
        self.settings.watch_interval_seconds = max(
            self.settings.watch_interval_seconds or DEFAULT_WATCH_INTERVAL_SECONDS,
            MINIMUM_WATCH_INTERVAL_SECONDS,
        )
        self._locators: List[BaseResourceLocator] = list(locators or _build_default_locators(self.settings))
        self._resource_cache: Dict[Tuple[str, str], ResourceMetadata] = {}
        self._refresh_lock = asyncio.Lock()
        self._last_refresh: Optional[datetime] = None
        self._watch_task: Optional[asyncio.Task] = None
        self._watch_snapshot: Dict[str, Tuple[bool, Optional[float]]] = {}
        self._running = False

    async def initialize(self) -> None:
        if not self.settings.enable_catalog:
            logger.info("System resource catalog disabled via configuration")
            return

        await self._ensure_table()
        await self._load_cache_from_db()
        self._running = True

        if self.settings.auto_refresh_on_startup:
            await self.refresh(force=True)

        if self.settings.enable_watchers and self.settings.watch_paths:
            self._watch_snapshot = self._snapshot_paths(self._watch_targets())
            self._watch_task = asyncio.create_task(self._watch_filesystem())

    async def shutdown(self) -> None:
        self._running = False
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:  # pragma: no cover
                pass
            self._watch_task = None

    async def refresh(self, *, force: bool = False) -> Dict[str, Any]:
        if not self.settings.enable_catalog:
            return {"skipped": True, "reason": "disabled"}

        async with self._refresh_lock:
            now = datetime.utcnow()
            if not force and self._last_refresh and (
                now - self._last_refresh
            ) < timedelta(seconds=self.settings.debounce_seconds):
                return {"skipped": True, "reason": "debounced"}

            discovered = await self._discover_resources()
            await self._persist_resources(discovered)
            self._last_refresh = now
            return {"skipped": False, "count": len(discovered)}

    async def discover(self) -> List[ResourceMetadata]:
        """Public entrypoint to run discovery and receive results without persisting."""
        return await self._discover_resources()

    async def get_resources(
        self,
        *,
        resource_type: Optional[str] = None,
        capability: Optional[str] = None,
        name: Optional[str] = None,
        available_only: bool = True,
    ) -> List[ResourceMetadata]:
        query = "SELECT * FROM resources_catalog WHERE 1=1"
        params: List[Any] = []

        if available_only:
            query += " AND available = 1"
        if resource_type:
            query += " AND resource_type = ?"
            params.append(str(resource_type))
        if name:
            query += " AND LOWER(name) = ?"
            params.append(name.lower())

        async with await self.db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

        resources = [self._row_to_metadata(row) for row in rows]

        if capability:
            capability_lower = capability.lower()
            resources = [
                resource
                for resource in resources
                if capability_lower in resource.capability_tags
            ]

        return resources

    async def get_resources_by_capability(self, capability: str) -> List[ResourceMetadata]:
        return await self.get_resources(capability=capability)

    async def get_resources_by_type(self, resource_type: str) -> List[ResourceMetadata]:
        return await self.get_resources(resource_type=resource_type)

    async def get_resource(self, name: str) -> ResourceMetadata:
        resources = await self.get_resources(name=name, available_only=False)
        if not resources:
            raise ValueError(f"Resource '{name}' not found")
        return resources[0]

    async def register_custom_resource(
        self,
        metadata: ResourceMetadata,
        *,
        override: bool = True,
    ) -> None:
        metadata.discovery_source = metadata.discovery_source or "manual"
        metadata.available = True

        async with self._refresh_lock:
            await self._persist_resources(
                [metadata], override_existing=override, invalidate_missing=False
            )

    async def _ensure_table(self) -> None:
        async with await self.db_service.get_connection() as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS resources_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    version TEXT,
                    install_path TEXT,
                    dependencies TEXT,
                    min_requirements TEXT,
                    max_requirements TEXT,
                    capability_tags TEXT,
                    metadata TEXT,
                    discovery_source TEXT,
                    available BOOLEAN NOT NULL DEFAULT TRUE,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, install_path)
                )
                """
            )
            await db.commit()

    async def _discover_resources(self) -> List[ResourceMetadata]:
        tasks = [locator.locate() for locator in self._locators]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        aggregated: Dict[Tuple[str, str], ResourceMetadata] = {}

        for result in results:
            if isinstance(result, Exception):  # pragma: no cover - logging only
                logger.warning("Resource locator error: %s", result)
                continue
            for metadata in result:
                key = metadata.normalized_key()
                if key not in aggregated:
                    aggregated[key] = metadata

        return list(aggregated.values())

    async def _persist_resources(
        self,
        resources: List[ResourceMetadata],
        *,
        override_existing: bool = True,
        invalidate_missing: bool = True,
    ) -> None:
        if not resources:
            return

        async with await self.db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM resources_catalog")
            rows = await cursor.fetchall()
            existing: Dict[Tuple[str, str], aiosqlite.Row] = {}
            for row in rows:
                metadata = self._row_to_metadata(row)
                existing[metadata.normalized_key()] = row

            now = datetime.utcnow().isoformat()
            discovered_keys = set()

            for resource in resources:
                key = resource.normalized_key()
                discovered_keys.add(key)
                row = existing.get(key)
                dependencies = json.dumps(resource.dependencies or [])
                min_requirements = json.dumps(resource.min_requirements.dict() if resource.min_requirements else None)
                max_requirements = json.dumps(resource.max_requirements.dict() if resource.max_requirements else None)
                capability_tags = json.dumps(resource.capability_tags or [])
                metadata_blob = json.dumps(resource.metadata or {})

                if row and override_existing:
                    await db.execute(
                        """
                        UPDATE resources_catalog
                        SET name = ?, resource_type = ?, version = ?, install_path = ?,
                            dependencies = ?, min_requirements = ?, max_requirements = ?,
                            capability_tags = ?, metadata = ?, discovery_source = ?,
                            available = TRUE, last_seen = ?
                        WHERE id = ?
                        """,
                        (
                            resource.name,
                            resource.resource_type.value,
                            resource.version,
                            resource.install_path,
                            dependencies,
                            min_requirements,
                            max_requirements,
                            capability_tags,
                            metadata_blob,
                            resource.discovery_source,
                            now,
                            row["id"],
                        ),
                    )
                elif not row:
                    await db.execute(
                        """
                        INSERT INTO resources_catalog (
                            name, resource_type, version, install_path, dependencies,
                            min_requirements, max_requirements, capability_tags, metadata,
                            discovery_source, available, first_seen, last_seen
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, ?, ?)
                        """,
                        (
                            resource.name,
                            resource.resource_type.value,
                            resource.version,
                            resource.install_path,
                            dependencies,
                            min_requirements,
                            max_requirements,
                            capability_tags,
                            metadata_blob,
                            resource.discovery_source,
                            now,
                            now,
                        ),
                    )

            if invalidate_missing:
                missing_keys = set(existing.keys()) - discovered_keys
                if missing_keys:
                    for key in missing_keys:
                        row = existing[key]
                        await db.execute(
                            "UPDATE resources_catalog SET available = FALSE WHERE id = ?",
                            (row["id"],),
                        )

            await db.commit()

        await self._load_cache_from_db()
        if self.settings.enable_watchers:
            self._watch_snapshot = self._snapshot_paths(self._watch_targets())

    async def _load_cache_from_db(self) -> None:
        async with await self.db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM resources_catalog WHERE available = 1")
            rows = await cursor.fetchall()

        cache: Dict[Tuple[str, str], ResourceMetadata] = {}
        for row in rows:
            metadata = self._row_to_metadata(row)
            cache[metadata.normalized_key()] = metadata
        self._resource_cache = cache

    def _row_to_metadata(self, row: aiosqlite.Row) -> ResourceMetadata:
        dependencies = json.loads(row["dependencies"]) if row["dependencies"] else []
        min_req = json.loads(row["min_requirements"]) if row["min_requirements"] else None
        max_req = json.loads(row["max_requirements"]) if row["max_requirements"] else None
        capability_tags = json.loads(row["capability_tags"]) if row["capability_tags"] else []
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        return ResourceMetadata(
            name=row["name"],
            resource_type=ResourceType(row["resource_type"]),
            version=row["version"],
            install_path=row["install_path"],
            dependencies=dependencies,
            min_requirements=ResourceRequirements(**min_req) if min_req else None,
            max_requirements=ResourceRequirements(**max_req) if max_req else None,
            capability_tags=capability_tags,
            discovery_source=row["discovery_source"] or "unknown",
            available=bool(row["available"]),
            metadata=metadata,
            first_seen=_parse_datetime(row["first_seen"]),
            last_seen=_parse_datetime(row["last_seen"]),
        )

    def _watch_targets(self) -> List[str]:
        targets = set(self.settings.watch_paths or [])
        for metadata in self._resource_cache.values():
            if metadata.install_path:
                targets.add(metadata.install_path)
        return list(targets)

    def _snapshot_paths(self, paths: Sequence[str]) -> Dict[str, Tuple[bool, Optional[float]]]:
        snapshot: Dict[str, Tuple[bool, Optional[float]]] = {}
        for path in paths:
            normalized = str(Path(path).expanduser())
            candidate = Path(normalized)
            if candidate.exists():
                try:
                    stat = candidate.stat()
                    snapshot[normalized] = (True, stat.st_mtime)
                except Exception:  # pragma: no cover
                    snapshot[normalized] = (True, None)
            else:
                snapshot[normalized] = (False, None)
        return snapshot

    def _snapshot_changed(self, new_snapshot: Dict[str, Tuple[bool, Optional[float]]]) -> bool:
        if self._watch_snapshot.keys() != new_snapshot.keys():
            return True
        for key, value in new_snapshot.items():
            if self._watch_snapshot.get(key) != value:
                return True
        return False

    async def _watch_filesystem(self) -> None:
        try:
            while self._running:
                await asyncio.sleep(self.settings.watch_interval_seconds)
                targets = self._watch_targets()
                snapshot = self._snapshot_paths(targets)
                if self._snapshot_changed(snapshot):
                    logger.info("Detected change in resource watch paths, refreshing catalog")
                    await self.refresh(force=True)
                self._watch_snapshot = snapshot
        except asyncio.CancelledError:  # pragma: no cover
            pass
        except Exception as exc:  # pragma: no cover
            logger.error("Resource catalog watcher error: %s", exc)


resource_catalog = SystemResourceCatalog()
