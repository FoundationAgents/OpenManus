"""
Tests for Component Registry.
"""

import pytest
from app.core.component_registry import (
    ComponentRegistry,
    ComponentMetadata,
    ComponentType,
    ComponentStatus,
    get_component_registry
)


def test_component_registry_initialization():
    """Test component registry initializes with default components."""
    registry = ComponentRegistry()
    
    # Should have default components
    components = registry.get_all_components()
    assert len(components) > 0
    
    # Should have core components
    config_comp = registry.get_component("config")
    assert config_comp is not None
    assert config_comp.component_type == ComponentType.CORE
    assert not config_comp.optional


def test_get_component():
    """Test getting a component by name."""
    registry = ComponentRegistry()
    
    component = registry.get_component("config")
    assert component is not None
    assert component.name == "config"
    
    # Non-existent component
    assert registry.get_component("nonexistent") is None


def test_get_components_by_type():
    """Test getting components by type."""
    registry = ComponentRegistry()
    
    core_components = registry.get_components_by_type(ComponentType.CORE)
    assert len(core_components) > 0
    assert all(c.component_type == ComponentType.CORE for c in core_components)


def test_get_required_components():
    """Test getting required components."""
    registry = ComponentRegistry()
    
    required = registry.get_required_components()
    assert len(required) > 0
    assert all(not c.optional for c in required)


def test_get_optional_components():
    """Test getting optional components."""
    registry = ComponentRegistry()
    
    optional = registry.get_optional_components()
    assert len(optional) > 0
    assert all(c.optional for c in optional)


def test_get_components_by_priority():
    """Test getting components sorted by priority."""
    registry = ComponentRegistry()
    
    by_priority = registry.get_components_by_priority()
    assert len(by_priority) > 0
    
    # Should be sorted by load_priority
    for i in range(len(by_priority) - 1):
        assert by_priority[i].load_priority <= by_priority[i + 1].load_priority


def test_get_dependencies():
    """Test getting component dependencies."""
    registry = ComponentRegistry()
    
    # Database depends on config and logger
    deps = registry.get_dependencies("database")
    assert "config" in deps
    assert "logger" in deps


def test_get_dependency_chain():
    """Test getting full dependency chain."""
    registry = ComponentRegistry()
    
    # Get dependency chain for a component with dependencies
    chain = registry.get_dependency_chain("database")
    assert "database" in chain
    assert "config" in chain
    assert "logger" in chain
    
    # Dependencies should come before the component
    db_index = chain.index("database")
    config_index = chain.index("config")
    assert config_index < db_index


def test_update_status():
    """Test updating component status."""
    registry = ComponentRegistry()
    
    component_name = "config"
    instance = object()
    
    registry.update_status(component_name, ComponentStatus.LOADING)
    component = registry.get_component(component_name)
    assert component.status == ComponentStatus.LOADING
    
    registry.update_status(component_name, ComponentStatus.LOADED, instance=instance)
    component = registry.get_component(component_name)
    assert component.status == ComponentStatus.LOADED
    assert component.instance is instance


def test_set_load_time():
    """Test setting component load time."""
    registry = ComponentRegistry()
    
    component_name = "config"
    load_time = 123.45
    
    registry.set_load_time(component_name, load_time)
    component = registry.get_component(component_name)
    assert component.load_time_ms == load_time


def test_is_loaded():
    """Test checking if component is loaded."""
    registry = ComponentRegistry()
    
    component_name = "config"
    
    # Initially not loaded
    assert not registry.is_loaded(component_name)
    
    # Mark as loaded
    registry.update_status(component_name, ComponentStatus.LOADED)
    assert registry.is_loaded(component_name)


def test_can_load():
    """Test checking if component can be loaded."""
    registry = ComponentRegistry()
    
    # Config has no dependencies, should be loadable
    assert registry.can_load("config")
    
    # Database depends on config and logger
    # Mark config as loaded
    registry.update_status("config", ComponentStatus.LOADED)
    # Still can't load because logger is not loaded
    assert not registry.can_load("database")
    
    # Mark logger as loaded
    registry.update_status("logger", ComponentStatus.LOADED)
    # Now can load
    assert registry.can_load("database")


def test_get_loadable_components():
    """Test getting components that can be loaded."""
    registry = ComponentRegistry()
    
    # Initially, only components with no dependencies should be loadable
    loadable = registry.get_loadable_components()
    assert len(loadable) > 0
    assert all(len(c.dependencies) == 0 or c.condition is not None for c in loadable)


def test_get_total_resource_requirement():
    """Test calculating total resource requirement."""
    registry = ComponentRegistry()
    
    components = ["config", "logger", "database"]
    total = registry.get_total_resource_requirement(components)
    
    # Should be sum of individual requirements
    expected = sum(
        registry.get_component(c).resource_requirement_mb
        for c in components
    )
    assert total == expected


def test_register_component():
    """Test registering a new component."""
    registry = ComponentRegistry()
    
    new_component = ComponentMetadata(
        name="test_component",
        component_type=ComponentType.TOOL,
        dependencies=["config"],
        optional=True,
        resource_requirement_mb=50,
        load_priority=10,
        description="Test component"
    )
    
    registry.register_component(new_component)
    
    component = registry.get_component("test_component")
    assert component is not None
    assert component.name == "test_component"
    assert component.component_type == ComponentType.TOOL


def test_singleton():
    """Test that get_component_registry returns singleton."""
    registry1 = get_component_registry()
    registry2 = get_component_registry()
    
    assert registry1 is registry2
