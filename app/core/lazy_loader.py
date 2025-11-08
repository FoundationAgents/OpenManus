"""
Lazy Component Loader
Load components on-demand when they are first accessed.
"""

import asyncio
import importlib
import threading
import time
from typing import Any, Callable, Dict, Optional

from app.core.component_registry import ComponentStatus, get_component_registry
from app.core.error_isolation import get_error_isolation
from app.logger import logger


class LazyLoader:
    """
    Load components on-demand when they are first accessed.
    Provides caching and progress tracking.
    """
    
    def __init__(self):
        self.registry = get_component_registry()
        self.error_isolation = get_error_isolation()
        self._lock = threading.RLock()
        self._loading_callbacks: Dict[str, list] = {}
        self._progress_callbacks: Dict[str, list] = {}
    
    def load_component(
        self,
        component_name: str,
        force_reload: bool = False,
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> tuple:
        """
        Load a component synchronously.
        
        Args:
            component_name: Name of component to load
            force_reload: Force reload even if already loaded
            on_progress: Progress callback (component_name, progress_percent)
        
        Returns:
            Tuple of (success: bool, instance: Any, error: Exception)
        """
        component = self.registry.get_component(component_name)
        if not component:
            error = ValueError(f"Component '{component_name}' not found in registry")
            logger.error(str(error))
            return False, None, error
        
        # Check if already loaded
        if component.status == ComponentStatus.LOADED and not force_reload:
            logger.debug(f"Component '{component_name}' already loaded")
            return True, component.instance, None
        
        # Check if currently loading
        if component.status == ComponentStatus.LOADING:
            logger.warning(f"Component '{component_name}' is already being loaded")
            return False, None, ValueError("Component is currently loading")
        
        # Check dependencies
        if not self.registry.can_load(component_name):
            missing_deps = [
                dep for dep in component.dependencies
                if not self.registry.is_loaded(dep)
            ]
            error = ValueError(
                f"Cannot load '{component_name}': missing dependencies {missing_deps}"
            )
            logger.error(str(error))
            return False, None, error
        
        # Mark as loading
        self.registry.update_status(component_name, ComponentStatus.LOADING)
        
        # Report progress
        if on_progress:
            on_progress(component_name, 0.0)
        self._notify_progress(component_name, 0.0)
        
        start_time = time.time()
        
        def loader():
            """Component loader function."""
            if not component.module_path:
                raise ValueError(f"No module path specified for component '{component_name}'")
            
            # Report progress
            if on_progress:
                on_progress(component_name, 30.0)
            self._notify_progress(component_name, 30.0)
            
            # Import module
            module = importlib.import_module(component.module_path)
            
            # Report progress
            if on_progress:
                on_progress(component_name, 60.0)
            self._notify_progress(component_name, 60.0)
            
            # For GUI panels, just return the module (actual instantiation happens in GUI)
            if component.gui_panel:
                return module
            
            # For other components, try to get default instance or factory
            if hasattr(module, 'get_instance'):
                return module.get_instance()
            elif hasattr(module, 'create_instance'):
                return module.create_instance()
            else:
                return module
        
        # Load with error isolation
        success, instance, error = self.error_isolation.safe_load(
            component_name,
            loader,
            on_success=lambda result: self._on_load_success(component_name, result, on_progress),
            on_failure=lambda err: self._on_load_failure(component_name, err, on_progress)
        )
        
        # Update load time
        load_time_ms = (time.time() - start_time) * 1000
        self.registry.set_load_time(component_name, load_time_ms)
        
        if success:
            logger.info(f"Component '{component_name}' loaded in {load_time_ms:.1f}ms")
        
        return success, instance, error
    
    async def load_component_async(
        self,
        component_name: str,
        force_reload: bool = False,
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> tuple:
        """
        Load a component asynchronously.
        
        Args:
            component_name: Name of component to load
            force_reload: Force reload even if already loaded
            on_progress: Progress callback (component_name, progress_percent)
        
        Returns:
            Tuple of (success: bool, instance: Any, error: Exception)
        """
        # Run synchronous load in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.load_component,
            component_name,
            force_reload,
            on_progress
        )
    
    def load_components(
        self,
        component_names: list,
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, tuple]:
        """
        Load multiple components sequentially.
        
        Args:
            component_names: List of component names to load
            on_progress: Progress callback (component_name, progress_percent)
        
        Returns:
            Dict mapping component name to (success, instance, error) tuple
        """
        results = {}
        
        for name in component_names:
            success, instance, error = self.load_component(name, on_progress=on_progress)
            results[name] = (success, instance, error)
        
        return results
    
    def unload_component(self, component_name: str) -> bool:
        """
        Unload a component.
        
        Args:
            component_name: Name of component to unload
        
        Returns:
            True if unloaded successfully
        """
        component = self.registry.get_component(component_name)
        if not component:
            logger.error(f"Component '{component_name}' not found")
            return False
        
        if component.status != ComponentStatus.LOADED:
            logger.warning(f"Component '{component_name}' is not loaded")
            return False
        
        # Call cleanup if available
        if component.instance and hasattr(component.instance, 'cleanup'):
            try:
                component.instance.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up component '{component_name}': {e}")
        
        # Update status
        self.registry.update_status(component_name, ComponentStatus.NOT_LOADED, instance=None)
        logger.info(f"Component '{component_name}' unloaded")
        
        return True
    
    def _on_load_success(self, component_name: str, instance: Any, on_progress: Optional[Callable]):
        """Handle successful component load."""
        self.registry.update_status(component_name, ComponentStatus.LOADED, instance=instance)
        
        if on_progress:
            on_progress(component_name, 100.0)
        self._notify_progress(component_name, 100.0)
        self._notify_loaded(component_name, instance)
    
    def _on_load_failure(self, component_name: str, error: Exception, on_progress: Optional[Callable]):
        """Handle component load failure."""
        self.registry.update_status(component_name, ComponentStatus.FAILED, error=error)
        
        if on_progress:
            on_progress(component_name, -1.0)  # -1 indicates failure
        self._notify_progress(component_name, -1.0)
    
    def register_loading_callback(self, component_name: str, callback: Callable):
        """Register callback for when component finishes loading."""
        with self._lock:
            if component_name not in self._loading_callbacks:
                self._loading_callbacks[component_name] = []
            self._loading_callbacks[component_name].append(callback)
    
    def register_progress_callback(self, component_name: str, callback: Callable):
        """Register callback for loading progress updates."""
        with self._lock:
            if component_name not in self._progress_callbacks:
                self._progress_callbacks[component_name] = []
            self._progress_callbacks[component_name].append(callback)
    
    def _notify_loaded(self, component_name: str, instance: Any):
        """Notify callbacks that component is loaded."""
        with self._lock:
            callbacks = self._loading_callbacks.get(component_name, [])
        
        for callback in callbacks:
            try:
                callback(component_name, instance)
            except Exception as e:
                logger.error(f"Error in loading callback for '{component_name}': {e}")
    
    def _notify_progress(self, component_name: str, progress: float):
        """Notify callbacks of loading progress."""
        with self._lock:
            callbacks = self._progress_callbacks.get(component_name, [])
        
        for callback in callbacks:
            try:
                callback(component_name, progress)
            except Exception as e:
                logger.error(f"Error in progress callback for '{component_name}': {e}")


# Global singleton
_lazy_loader = None


def get_lazy_loader() -> LazyLoader:
    """Get the global lazy loader singleton."""
    global _lazy_loader
    if _lazy_loader is None:
        _lazy_loader = LazyLoader()
    return _lazy_loader
