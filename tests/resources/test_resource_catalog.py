import pytest

from app.resources import catalog as catalog_module
from app.resources.catalog import (
    ResourceCatalogSettings,
    ResourceMetadata,
    ResourceType,
    SystemResourceCatalog,
)
from app.database.database_service import DatabaseService
from app.database.migration_manager import MigrationManager


@pytest.fixture
async def isolated_db(tmp_path):
    db_path = tmp_path / "resources.db"
    service = DatabaseService()
    service.db_path = str(db_path)
    service.migration_manager = MigrationManager(str(db_path))
    await service.initialize()
    try:
        yield service
    finally:
        await service.close()


@pytest.fixture
async def empty_catalog(isolated_db):
    settings = ResourceCatalogSettings(
        enable_catalog=True,
        auto_refresh_on_startup=False,
        enable_watchers=False,
        debounce_seconds=0,
        watch_interval_seconds=60,
    )
    catalog = SystemResourceCatalog(db_service=isolated_db, settings=settings, locators=[])
    await catalog.initialize()
    try:
        yield catalog
    finally:
        await catalog.shutdown()


def test_visual_studio_locator_reads_registry(monkeypatch):
    original_winreg = catalog_module.winreg_module
    original_platform = catalog_module.sys.platform
    monkeypatch.setattr(catalog_module.sys, "platform", "win32")

    class FakeKey:
        def __init__(self, values):
            self._values = values

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def EnumValue(self, index):
            try:
                value = self._values[index]
            except IndexError:
                raise OSError
            return value

    class FakeWinReg:
        HKEY_LOCAL_MACHINE = object()
        HKEY_CURRENT_USER = object()

        def __init__(self):
            self._values = [("17.0", "C:/VS/17.0", None)]

        def OpenKey(self, *_args, **_kwargs):
            return FakeKey(self._values)

    monkeypatch.setattr(catalog_module, "winreg_module", FakeWinReg())

    locator = catalog_module.VisualStudioLocator()
    results = locator._locate()

    assert results
    visual_studio = results[0]
    assert visual_studio.name == "Visual Studio 17.0"
    assert visual_studio.resource_type == ResourceType.IDE
    assert "c++" in visual_studio.capability_tags
    assert visual_studio.install_path.endswith("17.0")

    catalog_module.winreg_module = original_winreg
    monkeypatch.setattr(catalog_module.sys, "platform", original_platform)


def test_cmake_locator_uses_executable(monkeypatch):
    monkeypatch.setattr(catalog_module.shutil, "which", lambda binary: "/usr/bin/cmake" if binary == "cmake" else None)
    monkeypatch.setattr(catalog_module, "_command_version", lambda cmd: "3.26.0")

    locator = catalog_module.CMakeLocator()
    results = locator._locate()

    assert results
    cmake = results[0]
    assert cmake.name == "CMake"
    assert cmake.version == "3.26.0"
    assert cmake.install_path.endswith("/usr/bin")


def test_python_locator_discovers_multiple(monkeypatch):
    monkeypatch.setattr(catalog_module.sys, "executable", "/opt/python/bin/python3")

    def fake_which(binary):
        return {
            "python": "/usr/bin/python",
            "python3": "/usr/bin/python3",
        }.get(binary)

    monkeypatch.setattr(catalog_module.shutil, "which", fake_which)
    monkeypatch.setattr(catalog_module, "_command_version", lambda cmd: "3.12.1" if "python" in cmd[0] else None)

    locator = catalog_module.PythonLocator()
    results = locator._locate()

    paths = {resource.install_path for resource in results}
    assert any(path.endswith("/usr/bin") for path in paths)
    assert any(path.endswith("/opt/python/bin") for path in paths)


def test_ghidra_locator_respects_environment(monkeypatch, tmp_path):
    ghidra_path = tmp_path / "ghidra"
    ghidra_path.mkdir()
    monkeypatch.setenv("GHIDRA_HOME", str(ghidra_path))

    locator = catalog_module.GhidraLocator()
    results = locator._locate()

    assert results
    assert any(resource.install_path == str(ghidra_path) for resource in results)


def test_ida_locator_uses_environment(monkeypatch, tmp_path):
    ida_path = tmp_path / "ida"
    ida_path.mkdir()
    monkeypatch.setenv("IDA_HOME", str(ida_path))

    locator = catalog_module.IDAProLocator()
    results = locator._locate()

    assert results
    assert results[0].install_path == str(ida_path)


def test_cuda_locator_environment(monkeypatch, tmp_path):
    cuda_path = tmp_path / "cuda"
    cuda_path.mkdir()
    monkeypatch.setenv("CUDA_PATH", str(cuda_path))

    locator = catalog_module.CUDALocator()
    results = locator._locate()

    assert results
    assert results[0].install_path == str(cuda_path)


def test_powershell_locator_detects_pwsh(monkeypatch, tmp_path):
    pwsh_dir = tmp_path / "bin"
    pwsh_dir.mkdir()
    pwsh_path = pwsh_dir / "pwsh"
    pwsh_path.write_text("#!/bin/pwsh")

    monkeypatch.setattr(catalog_module.sys, "platform", "linux")
    monkeypatch.setattr(
        catalog_module.shutil,
        "which",
        lambda binary: str(pwsh_path) if binary == "pwsh" else None,
    )
    monkeypatch.setattr(catalog_module, "_command_version", lambda cmd: "7.4.0")

    locator = catalog_module.PowerShellLocator()
    results = locator._locate()

    assert results
    assert any(resource.install_path == str(pwsh_dir) for resource in results)


def test_directx_locator_environment(monkeypatch, tmp_path):
    original_platform = catalog_module.sys.platform
    monkeypatch.setattr(catalog_module.sys, "platform", "win32")
    dx_path = tmp_path / "DirectX"
    dx_path.mkdir()
    monkeypatch.setenv("DXSDK_DIR", str(dx_path))

    locator = catalog_module.DirectXSDKLocator()
    results = locator._locate()

    assert results
    assert results[0].install_path == str(dx_path)

    monkeypatch.setattr(catalog_module.sys, "platform", original_platform)


@pytest.mark.asyncio
async def test_resource_catalog_manual_registration(empty_catalog):
    resource = ResourceMetadata(
        name="Custom Tool",
        resource_type=ResourceType.TOOL,
        version="1.0",
        install_path="/opt/custom/tool",
        capability_tags=["custom", "tool"],
        metadata={"vendor": "Acme"},
    )

    await empty_catalog.register_custom_resource(resource)
    stored = await empty_catalog.get_resources(name="Custom Tool", available_only=False)

    assert stored
    assert stored[0].available is True
    assert stored[0].metadata["vendor"] == "Acme"


@pytest.mark.asyncio
async def test_resource_catalog_refresh_marks_missing(isolated_db, monkeypatch):
    settings = ResourceCatalogSettings(
        enable_catalog=True,
        auto_refresh_on_startup=False,
        enable_watchers=False,
        debounce_seconds=0,
        watch_interval_seconds=60,
    )

    class StaticLocator(catalog_module.BaseResourceLocator):
        def __init__(self, resources):
            super().__init__()
            self._resources = resources

        def _locate(self):
            return list(self._resources)

    resource = ResourceMetadata(
        name="Visual Studio 17",
        resource_type=ResourceType.IDE,
        version="17.0",
        install_path="C:/VS/17",
        capability_tags=["c++"],
    )

    locator = StaticLocator([resource])
    catalog = SystemResourceCatalog(
        db_service=isolated_db,
        settings=settings,
        locators=[locator],
    )
    await catalog.initialize()

    await catalog.refresh(force=True)
    available = await catalog.get_resources(name="Visual Studio 17")
    assert available and available[0].available

    locator._resources = []
    await catalog.refresh(force=True)
    unavailable = await catalog.get_resources(name="Visual Studio 17", available_only=False)
    assert unavailable and not unavailable[0].available

    await catalog.shutdown()
