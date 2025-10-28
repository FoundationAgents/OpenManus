"""
Deprecation utilities for AgentBay SDK.
Provides decorators and utilities for marking APIs as deprecated.
"""

import warnings
from functools import wraps
from typing import Optional


def deprecated(reason: str, replacement: Optional[str] = None, version: Optional[str] = None):
    """
    Mark a function as deprecated.
    
    Args:
        reason (str): The reason why the function is deprecated.
        replacement (Optional[str]): The recommended replacement function.
        version (Optional[str]): The version when the function was deprecated.
    
    Returns:
        Decorator function that adds deprecation warning.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            message = f"{func.__qualname__} is deprecated"
            if version:
                message += f" since version {version}"
            message += f". {reason}"
            if replacement:
                message += f" Use {replacement} instead."
            
            warnings.warn(
                message,
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        
        # Update docstring to include deprecation notice
        if func.__doc__:
            deprecation_notice = f"\n\n    .. deprecated::"
            if version:
                deprecation_notice += f" {version}"
            deprecation_notice += f"\n        {reason}"
            if replacement:
                deprecation_notice += f" Use {replacement} instead."
            wrapper.__doc__ = func.__doc__ + deprecation_notice
        
        return wrapper
    return decorator 