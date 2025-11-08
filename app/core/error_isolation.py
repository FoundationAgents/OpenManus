"""
Error Isolation
Isolate component loading errors to prevent system crashes.
"""

import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from app.logger import logger


@dataclass
class ComponentError:
    """Information about a component loading error."""
    component_name: str
    error: Exception
    traceback: str
    timestamp: datetime
    retry_count: int = 0
    can_retry: bool = True


class ErrorIsolation:
    """
    Isolate component loading errors to prevent system crashes.
    Provides error tracking, retry logic, and fallback mechanisms.
    """
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._errors: Dict[str, ComponentError] = {}
        self._success_callbacks: Dict[str, List[Callable]] = {}
        self._failure_callbacks: Dict[str, List[Callable]] = {}
    
    def safe_load(
        self,
        component_name: str,
        loader_func: Callable[[], Any],
        on_success: Optional[Callable[[Any], None]] = None,
        on_failure: Optional[Callable[[Exception], None]] = None
    ) -> tuple:
        """
        Safely load a component with error isolation.
        
        Args:
            component_name: Name of the component
            loader_func: Function to load the component
            on_success: Callback on successful load
            on_failure: Callback on failure
        
        Returns:
            Tuple of (success: bool, result: Any, error: Exception)
        """
        try:
            logger.info(f"Loading component: {component_name}")
            result = loader_func()
            
            # Clear any previous errors
            if component_name in self._errors:
                del self._errors[component_name]
            
            logger.info(f"Successfully loaded component: {component_name}")
            
            # Call success callback
            if on_success:
                try:
                    on_success(result)
                except Exception as e:
                    logger.error(f"Error in success callback for {component_name}: {e}")
            
            # Call registered callbacks
            for callback in self._success_callbacks.get(component_name, []):
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Error in registered callback for {component_name}: {e}")
            
            return True, result, None
            
        except Exception as e:
            logger.error(f"Failed to load component {component_name}: {e}")
            tb = traceback.format_exc()
            
            # Record error
            error_info = ComponentError(
                component_name=component_name,
                error=e,
                traceback=tb,
                timestamp=datetime.now(),
                retry_count=self._errors.get(component_name, ComponentError(
                    component_name, e, tb, datetime.now()
                )).retry_count + 1 if component_name in self._errors else 0,
                can_retry=True
            )
            self._errors[component_name] = error_info
            
            # Call failure callback
            if on_failure:
                try:
                    on_failure(e)
                except Exception as callback_error:
                    logger.error(f"Error in failure callback for {component_name}: {callback_error}")
            
            # Call registered callbacks
            for callback in self._failure_callbacks.get(component_name, []):
                try:
                    callback(e)
                except Exception as callback_error:
                    logger.error(f"Error in registered failure callback for {component_name}: {callback_error}")
            
            return False, None, e
    
    async def safe_load_async(
        self,
        component_name: str,
        loader_func: Callable,
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None
    ) -> tuple:
        """
        Safely load a component asynchronously with error isolation.
        
        Args:
            component_name: Name of the component
            loader_func: Async function to load the component
            on_success: Async callback on successful load
            on_failure: Async callback on failure
        
        Returns:
            Tuple of (success: bool, result: Any, error: Exception)
        """
        try:
            logger.info(f"Loading component (async): {component_name}")
            result = await loader_func()
            
            # Clear any previous errors
            if component_name in self._errors:
                del self._errors[component_name]
            
            logger.info(f"Successfully loaded component (async): {component_name}")
            
            # Call success callback
            if on_success:
                try:
                    if callable(on_success):
                        await on_success(result)
                except Exception as e:
                    logger.error(f"Error in async success callback for {component_name}: {e}")
            
            return True, result, None
            
        except Exception as e:
            logger.error(f"Failed to load component (async) {component_name}: {e}")
            tb = traceback.format_exc()
            
            # Record error
            error_info = ComponentError(
                component_name=component_name,
                error=e,
                traceback=tb,
                timestamp=datetime.now(),
                retry_count=self._errors.get(component_name, ComponentError(
                    component_name, e, tb, datetime.now()
                )).retry_count + 1 if component_name in self._errors else 0,
                can_retry=True
            )
            self._errors[component_name] = error_info
            
            # Call failure callback
            if on_failure:
                try:
                    if callable(on_failure):
                        await on_failure(e)
                except Exception as callback_error:
                    logger.error(f"Error in async failure callback for {component_name}: {callback_error}")
            
            return False, None, e
    
    def can_retry(self, component_name: str) -> bool:
        """Check if component can be retried."""
        error = self._errors.get(component_name)
        if not error:
            return True
        
        return error.can_retry and error.retry_count < self.max_retries
    
    def get_error(self, component_name: str) -> Optional[ComponentError]:
        """Get error information for a component."""
        return self._errors.get(component_name)
    
    def get_all_errors(self) -> Dict[str, ComponentError]:
        """Get all component errors."""
        return self._errors.copy()
    
    def clear_error(self, component_name: str):
        """Clear error for a component."""
        if component_name in self._errors:
            del self._errors[component_name]
    
    def clear_all_errors(self):
        """Clear all errors."""
        self._errors.clear()
    
    def mark_cannot_retry(self, component_name: str):
        """Mark component as cannot retry."""
        error = self._errors.get(component_name)
        if error:
            error.can_retry = False
    
    def register_success_callback(self, component_name: str, callback: Callable):
        """Register a callback to be called on successful component load."""
        if component_name not in self._success_callbacks:
            self._success_callbacks[component_name] = []
        self._success_callbacks[component_name].append(callback)
    
    def register_failure_callback(self, component_name: str, callback: Callable):
        """Register a callback to be called on component load failure."""
        if component_name not in self._failure_callbacks:
            self._failure_callbacks[component_name] = []
        self._failure_callbacks[component_name].append(callback)
    
    def format_error_report(self) -> str:
        """Format all errors as a human-readable report."""
        if not self._errors:
            return "No component errors recorded."
        
        lines = ["Component Loading Errors:", ""]
        
        for name, error in self._errors.items():
            lines.append(f"Component: {name}")
            lines.append(f"  Error: {error.error}")
            lines.append(f"  Time: {error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"  Retry count: {error.retry_count}/{self.max_retries}")
            lines.append(f"  Can retry: {error.can_retry}")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_failed_components(self) -> List[str]:
        """Get list of failed component names."""
        return list(self._errors.keys())
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self._errors) > 0


# Global singleton
_error_isolation = None


def get_error_isolation() -> ErrorIsolation:
    """Get the global error isolation singleton."""
    global _error_isolation
    if _error_isolation is None:
        _error_isolation = ErrorIsolation()
    return _error_isolation
