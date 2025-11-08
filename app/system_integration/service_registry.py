"""
Service Registry
Manages registration and discovery of system services
"""

from typing import Dict, Any, Optional, List

from app.logger import logger


class ServiceRegistry:
    """Registry for system services"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
    
    def register(self, name: str, service: Any, metadata: Optional[Dict[str, Any]] = None):
        """Register a service"""
        self._services[name] = service
        self._metadata[name] = metadata or {}
        logger.info(f"Registered service: {name}")
    
    def unregister(self, name: str) -> bool:
        """Unregister a service"""
        if name in self._services:
            del self._services[name]
            if name in self._metadata:
                del self._metadata[name]
            logger.info(f"Unregistered service: {name}")
            return True
        return False
    
    def get(self, name: str) -> Optional[Any]:
        """Get a service by name"""
        return self._services.get(name)
    
    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Get service metadata"""
        return self._metadata.get(name)
    
    def list_services(self) -> List[str]:
        """List all registered service names"""
        return list(self._services.keys())
    
    def has_service(self, name: str) -> bool:
        """Check if a service is registered"""
        return name in self._services
    
    def get_service_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get service information"""
        if name not in self._services:
            return None
        
        service = self._services[name]
        metadata = self._metadata[name]
        
        return {
            "name": name,
            "service_type": type(service).__name__,
            "metadata": metadata,
            "methods": [method for method in dir(service) if not method.startswith('_')]
        }
    
    def get_all_services_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all services"""
        return {
            name: self.get_service_info(name)
            for name in self._services.keys()
        }
