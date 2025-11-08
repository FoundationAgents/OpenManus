"""File-system level permission modelling for anti-modification guarantees."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

from app.safety.exceptions import PermissionDeniedError


@dataclass(frozen=True)
class FilePermissionMatrix:
    """Immutable file-system permission configuration."""

    read_only_paths: List[Path] = field(default_factory=list)
    writable_paths: List[Path] = field(default_factory=list)
    forbidden_paths: List[Path] = field(default_factory=list)


DEFAULT_MATRIX = FilePermissionMatrix(
    read_only_paths=[
        Path("/openmanus/app/agent"),
        Path("/openmanus/app/safety"),
        Path("/openmanus/app/core"),
    ],
    writable_paths=[
        Path("/openmanus/data"),
        Path("/openmanus/logs"),
        Path("/openmanus/cache"),
    ],
    forbidden_paths=[
        Path("/openmanus/system"),
    ],
)


class FileSystemPermissionManager:
    """Checks whether file-system operations comply with immutable policy."""

    def __init__(self, matrix: FilePermissionMatrix = DEFAULT_MATRIX) -> None:
        self.matrix = matrix

    def assert_read_allowed(self, path: Path) -> None:
        # Reads are broadly allowed but still blocked for forbidden paths.
        if self._is_under(path, self.matrix.forbidden_paths):
            raise PermissionDeniedError("Access to forbidden path is blocked")

    def assert_write_allowed(self, path: Path) -> None:
        if self._is_under(path, self.matrix.forbidden_paths):
            raise PermissionDeniedError("Write attempt to forbidden path detected")
        if self._is_under(path, self.matrix.read_only_paths):
            raise PermissionDeniedError("Read-only agent code cannot be modified")
        if not self._is_under(path, self.matrix.writable_paths):
            raise PermissionDeniedError("Writes restricted to data/log/cache directories")

    def policy_overview(self) -> dict:
        return {
            "read_only": [str(p) for p in self.matrix.read_only_paths],
            "writable": [str(p) for p in self.matrix.writable_paths],
            "forbidden": [str(p) for p in self.matrix.forbidden_paths],
        }

    @staticmethod
    def _is_under(path: Path, roots: Iterable[Path]) -> bool:
        path = path.resolve()
        for root in roots:
            resolved = root.resolve()
            try:
                if path.is_relative_to(resolved):
                    return True
            except AttributeError:  # pragma: no cover
                try:
                    path.relative_to(resolved)
                    return True
                except ValueError:
                    continue
            except ValueError:
                continue
        return False
