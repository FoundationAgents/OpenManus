"""
Tests for GUI architecture components.

Tests the core GUI-first architecture components:
- Message Bus
- State Manager
- Component Discovery
- Progressive Loading
- Async UI Updates
"""

import pytest
from pathlib import Path


def test_message_bus_import():
    """Test that message bus can be imported."""
    from app.ui.message_bus import get_message_bus, MessageBus, EventTypes
    
    bus = get_message_bus()
    assert bus is not None
    assert isinstance(bus, MessageBus)


def test_message_bus_pubsub():
    """Test message bus publish/subscribe."""
    from app.ui.message_bus import get_message_bus
    
    bus = get_message_bus()
    bus.clear_history()
    
    received_messages = []
    
    def handler(message):
        received_messages.append(message)
    
    # Subscribe
    bus.subscribe("test_event", handler)
    
    # Publish
    bus.publish("test_event", {"data": "test"})
    
    assert len(received_messages) == 1
    assert received_messages[0].event_type == "test_event"
    assert received_messages[0].data["data"] == "test"


def test_state_manager_import():
    """Test that state manager can be imported."""
    from app.ui.state_manager import get_state_manager, StateManager
    
    manager = get_state_manager()
    assert manager is not None
    assert isinstance(manager, StateManager)


def test_state_manager_components():
    """Test state manager component registration."""
    from app.ui.state_manager import get_state_manager
    
    manager = get_state_manager()
    
    # Register component
    manager.register_component("test_component", dependencies=["dep1"])
    
    # Get component state
    state = manager.get_component_state("test_component")
    assert state is not None
    assert state.name == "test_component"
    assert "dep1" in state.dependencies


def test_component_discovery_import():
    """Test that component discovery can be imported."""
    from app.ui.component_discovery import get_component_discovery, ComponentDiscovery
    
    discovery = get_component_discovery()
    assert discovery is not None
    assert isinstance(discovery, ComponentDiscovery)


def test_component_discovery_scan():
    """Test component discovery scanning."""
    from app.ui.component_discovery import get_component_discovery
    
    discovery = get_component_discovery()
    components = discovery.discover_components()
    
    # Should discover some components
    assert isinstance(components, list)


def test_async_updates_import():
    """Test async UI updates import."""
    from app.ui.async_ui_updates import get_task_manager, AsyncTaskManager
    
    manager = get_task_manager()
    assert manager is not None


def test_error_dialogs_import():
    """Test error dialogs import."""
    from app.ui.error_dialogs import ErrorHandler
    
    handler = ErrorHandler("test")
    assert handler is not None


def test_keyboard_navigation_import():
    """Test keyboard navigation import."""
    from app.ui.keyboard_navigation import KeyboardNavigationManager, KeySequences
    
    assert KeySequences.NEW_FILE == "Ctrl+N"
    assert KeySequences.SAVE_FILE == "Ctrl+S"


def test_theme_engine_import():
    """Test theme engine import."""
    from app.ui.themes import get_theme_manager, LightTheme, DarkTheme
    
    manager = get_theme_manager()
    assert manager is not None
    
    light = LightTheme()
    assert light.name == "light"
    
    dark = DarkTheme()
    assert dark.name == "dark"


def test_ui_package_imports():
    """Test that all UI components can be imported from package."""
    from app.ui import (
        MainWindow,
        get_message_bus,
        get_state_manager,
        get_component_discovery,
        get_task_manager,
        show_error,
        ErrorHandler,
        KeyboardNavigationManager,
    )
    
    # All should be importable
    assert MainWindow is not None
    assert get_message_bus is not None
    assert get_state_manager is not None
    assert get_component_discovery is not None
    assert get_task_manager is not None
    assert show_error is not None
    assert ErrorHandler is not None
    assert KeyboardNavigationManager is not None


def test_settings_panel_import():
    """Test settings panel import."""
    from app.ui.settings_panel import SettingsPanel
    assert SettingsPanel is not None


def test_project_manager_import():
    """Test project manager import."""
    from app.ui.project_manager import ProjectManager
    assert ProjectManager is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
