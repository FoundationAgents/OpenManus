"""System resource catalog package."""

from .catalog import (
    SystemResourceCatalog,
    ResourceMetadata,
    ResourceRequirements,
    ResourceType,
    BaseResourceLocator,
    resource_catalog,
)

__all__ = [
    "SystemResourceCatalog",
    "ResourceMetadata",
    "ResourceRequirements",
    "ResourceType",
    "BaseResourceLocator",
    "resource_catalog",
]
