"""
Component Auto-Discovery for the GUI.

Dynamically discovers and loads available UI components, checking dependencies
and gracefully handling missing components.
"""

import importlib
import inspect
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass

try:
    from PyQt6.QtWidgets import QWidget
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QWidget = object

from app.ui.state_manager import get_state_manager

logger = logging.getLogger(__name__)


@dataclass
class ComponentInfo:
    """Information about a discovered component."""
    name: str
    class_name: str
    module_path: str
    display_name: str
    description: str
    dependencies: List[str]
    enabled: bool = True
    available: bool = False
    error: Optional[str] = None


class ComponentDiscovery:
    """
    Discovers and loads UI components dynamically.
    
    Features:
    - Scans app/ui/panels/ for available panels
    - Checks if dependencies are loaded
    - Shows only available panels in dock
    - Hides disabled components gracefully
    - Auto-populates View menu
    
    Example:
        discovery = ComponentDiscovery()
        components = discovery.discover_components()
        
        for comp_info in components:
            if comp_info.available:
                panel = discovery.load_component(comp_info.name)
    """
    
    def __init__(self, panels_dir: Optional[Path] = None):
        """
        Initialize component discovery.
        
        Args:
            panels_dir: Directory to search for panels (default: app/ui/panels)
        """
        if panels_dir is None:
            # Get the panels directory
            ui_dir = Path(__file__).parent
            panels_dir = ui_dir / "panels"
        
        self.panels_dir = panels_dir
        self.state_manager = get_state_manager()
        self._component_registry: Dict[str, ComponentInfo] = {}
        self._loaded_components: Dict[str, Any] = {}
        
        logger.info(f"Component discovery initialized (panels dir: {panels_dir})")
    
    def discover_components(self) -> List[ComponentInfo]:
        """
        Discover all available components.
        
        Returns:
            List of ComponentInfo objects
        """
        self._component_registry.clear()
        
        if not self.panels_dir.exists():
            logger.warning(f"Panels directory not found: {self.panels_dir}")
            return []
        
        # Scan for panel modules
        for panel_file in self.panels_dir.glob("*.py"):
            if panel_file.name.startswith("_"):
                continue
            
            try:
                comp_info = self._discover_component_from_file(panel_file)
                if comp_info:
                    self._component_registry[comp_info.name] = comp_info
                    
                    # Register with state manager
                    self.state_manager.register_component(
                        comp_info.name,
                        dependencies=comp_info.dependencies
                    )
                    
            except Exception as e:
                logger.error(f"Error discovering component from {panel_file.name}: {e}")
        
        logger.info(f"Discovered {len(self._component_registry)} components")
        return list(self._component_registry.values())
    
    def _discover_component_from_file(self, panel_file: Path) -> Optional[ComponentInfo]:
        """
        Discover a component from a Python file.
        
        Args:
            panel_file: Path to the panel file
            
        Returns:
            ComponentInfo or None if not a valid component
        """
        module_name = panel_file.stem
        module_path = f"app.ui.panels.{module_name}"
        
        try:
            # Try to import the module
            module = importlib.import_module(module_path)
            
            # Look for Panel classes
            panel_classes = []
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name.endswith("Panel") and PYQT6_AVAILABLE:
                    # Check if it's a QWidget subclass
                    if issubclass(obj, QWidget) and obj is not QWidget:
                        panel_classes.append((name, obj))
            
            if not panel_classes:
                return None
            
            # Use the first panel class found
            class_name, panel_class = panel_classes[0]
            
            # Extract metadata from class or module
            display_name = getattr(panel_class, "DISPLAY_NAME", class_name.replace("Panel", ""))
            description = getattr(panel_class, "DESCRIPTION", panel_class.__doc__ or "")
            dependencies = getattr(panel_class, "DEPENDENCIES", [])
            
            # Clean up description
            if description:
                description = " ".join(description.split())[:200]
            
            # Check if component is available
            available = True
            error = None
            
            # Check dependencies
            for dep in dependencies:
                try:
                    importlib.import_module(dep)
                except ImportError as e:
                    available = False
                    error = f"Missing dependency: {dep}"
                    break
            
            comp_info = ComponentInfo(
                name=module_name,
                class_name=class_name,
                module_path=module_path,
                display_name=display_name,
                description=description,
                dependencies=dependencies,
                available=available,
                error=error
            )
            
            logger.debug(f"Discovered component: {comp_info.name} (available: {available})")
            return comp_info
            
        except Exception as e:
            logger.error(f"Error loading module {module_path}: {e}")
            return ComponentInfo(
                name=module_name,
                class_name="",
                module_path=module_path,
                display_name=module_name,
                description="Failed to load",
                dependencies=[],
                available=False,
                error=str(e)
            )
    
    def load_component(self, component_name: str) -> Optional[Any]:
        """
        Load a component by name.
        
        Args:
            component_name: Name of the component to load
            
        Returns:
            Component instance or None if failed
        """
        # Check if already loaded
        if component_name in self._loaded_components:
            return self._loaded_components[component_name]
        
        # Get component info
        comp_info = self._component_registry.get(component_name)
        if not comp_info:
            logger.error(f"Component not found: {component_name}")
            return None
        
        if not comp_info.available:
            logger.warning(f"Component not available: {component_name} ({comp_info.error})")
            self.state_manager.update_component_state(
                component_name,
                loaded=False,
                error=comp_info.error
            )
            return None
        
        try:
            # Import the module
            module = importlib.import_module(comp_info.module_path)
            
            # Get the class
            panel_class = getattr(module, comp_info.class_name)
            
            # Instantiate the component
            component = panel_class()
            
            # Cache the instance
            self._loaded_components[component_name] = component
            
            # Update state
            self.state_manager.update_component_state(
                component_name,
                loaded=True,
                error=None
            )
            
            logger.info(f"Loaded component: {component_name}")
            return component
            
        except Exception as e:
            logger.error(f"Error loading component {component_name}: {e}", exc_info=True)
            self.state_manager.update_component_state(
                component_name,
                loaded=False,
                error=str(e)
            )
            return None
    
    def get_component_info(self, component_name: str) -> Optional[ComponentInfo]:
        """
        Get information about a component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            ComponentInfo or None if not found
        """
        return self._component_registry.get(component_name)
    
    def get_all_components(self) -> List[ComponentInfo]:
        """
        Get all discovered components.
        
        Returns:
            List of ComponentInfo objects
        """
        return list(self._component_registry.values())
    
    def get_available_components(self) -> List[ComponentInfo]:
        """
        Get only available components.
        
        Returns:
            List of available ComponentInfo objects
        """
        return [comp for comp in self._component_registry.values() if comp.available]
    
    def get_unavailable_components(self) -> List[ComponentInfo]:
        """
        Get unavailable components.
        
        Returns:
            List of unavailable ComponentInfo objects
        """
        return [comp for comp in self._component_registry.values() if not comp.available]
    
    def reload_component(self, component_name: str) -> Optional[Any]:
        """
        Reload a component.
        
        Args:
            component_name: Name of the component to reload
            
        Returns:
            New component instance or None if failed
        """
        # Remove from cache
        if component_name in self._loaded_components:
            del self._loaded_components[component_name]
        
        # Reload module
        comp_info = self._component_registry.get(component_name)
        if comp_info:
            try:
                module = importlib.import_module(comp_info.module_path)
                importlib.reload(module)
            except Exception as e:
                logger.error(f"Error reloading module for {component_name}: {e}")
        
        # Load again
        return self.load_component(component_name)
    
    def check_component_dependencies(self, component_name: str) -> tuple[bool, List[str]]:
        """
        Check if all dependencies for a component are satisfied.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Tuple of (all_satisfied, missing_dependencies)
        """
        comp_info = self._component_registry.get(component_name)
        if not comp_info:
            return False, [component_name]
        
        missing = []
        for dep in comp_info.dependencies:
            try:
                importlib.import_module(dep)
            except ImportError:
                missing.append(dep)
        
        return len(missing) == 0, missing
    
    def get_load_order(self) -> List[str]:
        """
        Get the optimal load order for components based on dependencies.
        
        Returns:
            List of component names in load order
        """
        # Simple topological sort
        # For now, just return available components
        # TODO: Implement proper dependency resolution
        
        available = [comp.name for comp in self.get_available_components()]
        return available


# Global component discovery instance
_component_discovery: Optional[ComponentDiscovery] = None


def get_component_discovery() -> ComponentDiscovery:
    """
    Get the global component discovery instance (singleton).
    
    Returns:
        Global ComponentDiscovery instance
    """
    global _component_discovery
    
    if _component_discovery is None:
        _component_discovery = ComponentDiscovery()
    
    return _component_discovery
