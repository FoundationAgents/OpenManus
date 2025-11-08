"""
System Integration Service
Main coordinator for all subsystems
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.logger import logger
from app.config import config
from app.database.database_service import database_service
from app.guardian.guardian_service import guardian_service
from app.knowledge_graph.knowledge_graph_service import knowledge_graph_service
from app.knowledge_graph.graph_builder import graph_builder
from app.backup.backup_service import backup_service
from app.backup.backup_scheduler import backup_scheduler
from app.versioning.versioning_service import versioning_service
from app.versioning.snapshot_manager import snapshot_manager
from app.resources.catalog import resource_catalog
from .event_bus import EventBus
from .service_registry import ServiceRegistry


class SystemIntegrationService:
    """Main system integration coordinator"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self.service_registry = ServiceRegistry()
        self._startup_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Register services
        self._register_services()
        
        # Setup event handlers
        self._setup_event_handlers()
    
    def _register_services(self):
        """Register all services with the registry"""
        self.service_registry.register("database", database_service)
        self.service_registry.register("guardian", guardian_service)
        self.service_registry.register("knowledge_graph", knowledge_graph_service)
        self.service_registry.register("graph_builder", graph_builder)
        self.service_registry.register("backup", backup_service)
        self.service_registry.register("backup_scheduler", backup_scheduler)
        self.service_registry.register("versioning", versioning_service)
        self.service_registry.register("snapshot_manager", snapshot_manager)
        self.service_registry.register("resource_catalog", resource_catalog)
        self.service_registry.register("event_bus", self.event_bus)
    
    def _setup_event_handlers(self):
        """Setup event handlers for cross-service communication"""
        # Security events
        self.event_bus.subscribe("security.threat_detected", self._handle_threat_detected)
        self.event_bus.subscribe("security.rule_violation", self._handle_rule_violation)
        
        # Version events
        self.event_bus.subscribe("version.created", self._handle_version_created)
        self.event_bus.subscribe("version.restored", self._handle_version_restored)
        
        # Backup events
        self.event_bus.subscribe("backup.completed", self._handle_backup_completed)
        self.event_bus.subscribe("backup.failed", self._handle_backup_failed)
        
        # Knowledge graph events
        self.event_bus.subscribe("knowledge.node_added", self._handle_node_added)
        self.event_bus.subscribe("knowledge.relationship_added", self._handle_relationship_added)
        
        # System events
        self.event_bus.subscribe("system.startup", self._handle_system_startup)
        self.event_bus.subscribe("system.shutdown", self._handle_system_shutdown)
    
    async def initialize(self):
        """Initialize all subsystems"""
        logger.info("Initializing system integration service...")
        
        try:
            # Initialize database first
            await database_service.initialize()
            
            # Initialize other services
            await guardian_service.start()
            await knowledge_graph_service.initialize()
            await graph_builder.start()
            await versioning_service.initialize()
            await snapshot_manager.initialize()
            await backup_scheduler.start()
            await resource_catalog.initialize()
            
            # Start event processing
            await self.event_bus.start()
            
            self._running = True
            
            # Emit system startup event
            await self.event_bus.emit("system.startup", {
                "timestamp": datetime.now().isoformat(),
                "services_initialized": self.service_registry.list_services()
            })
            
            logger.info("System integration service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing system integration service: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown all subsystems"""
        logger.info("Shutting down system integration service...")
        
        try:
            # Emit system shutdown event
            await self.event_bus.emit("system.shutdown", {
                "timestamp": datetime.now().isoformat()
            })
            
            self._running = False
            
            # Stop services in reverse order
            await backup_scheduler.stop()
            await snapshot_manager.stop()
            await resource_catalog.shutdown()
            await versioning_service.stop()
            await graph_builder.stop()
            await knowledge_graph_service.stop()
            await guardian_service.stop()
            
            # Stop event bus
            await self.event_bus.stop()
            
            # Close database
            await database_service.close()
            
            logger.info("System integration service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "running": self._running,
                "services": {},
                "overall_health": "healthy"
            }
            
            # Get status from each service
            service_statuses = {
                "database": await self._get_database_status(),
                "guardian": await self._get_guardian_status(),
                "knowledge_graph": await self._get_knowledge_graph_status(),
                "backup": await self._get_backup_status(),
                "versioning": await self._get_versioning_status()
            }
            
            status["services"] = service_statuses
            
            # Determine overall health
            health_issues = []
            for service_name, service_status in service_statuses.items():
                if service_status.get("status") != "healthy":
                    health_issues.append(f"{service_name}: {service_status.get('status')}")
            
            if health_issues:
                status["overall_health"] = "degraded" if len(health_issues) < 3 else "unhealthy"
                status["health_issues"] = health_issues
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "running": self._running,
                "overall_health": "error",
                "error": str(e)
            }
    
    async def _get_database_status(self) -> Dict[str, Any]:
        """Get database service status"""
        try:
            # Test database connection
            async with await database_service.get_connection() as db:
                cursor = await db.execute("SELECT 1")
                await cursor.fetchone()
            
            return {"status": "healthy", "message": "Database connection OK"}
            
        except Exception as e:
            return {"status": "error", "message": f"Database error: {e}"}
    
    async def _get_guardian_status(self) -> Dict[str, Any]:
        """Get guardian service status"""
        try:
            if not config.guardian.enable_guardian:
                return {"status": "disabled", "message": "Guardian disabled in configuration"}
            
            summary = await guardian_service.get_security_summary()
            return {
                "status": "healthy",
                "message": "Guardian running",
                "summary": summary
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Guardian error: {e}"}
    
    async def _get_knowledge_graph_status(self) -> Dict[str, Any]:
        """Get knowledge graph service status"""
        try:
            if not config.knowledge_graph.enable_knowledge_graph:
                return {"status": "disabled", "message": "Knowledge graph disabled in configuration"}
            
            stats = await knowledge_graph_service.get_graph_statistics()
            return {
                "status": "healthy",
                "message": "Knowledge graph running",
                "statistics": stats
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Knowledge graph error: {e}"}
    
    async def _get_backup_status(self) -> Dict[str, Any]:
        """Get backup service status"""
        try:
            if not config.backup.enable_backups:
                return {"status": "disabled", "message": "Backups disabled in configuration"}
            
            stats = await backup_service.get_backup_statistics()
            return {
                "status": "healthy",
                "message": "Backup service running",
                "statistics": stats
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Backup error: {e}"}
    
    async def _get_versioning_status(self) -> Dict[str, Any]:
        """Get versioning service status"""
        try:
            if not config.versioning.enable_versioning:
                return {"status": "disabled", "message": "Versioning disabled in configuration"}
            
            stats = await versioning_service.get_version_statistics()
            return {
                "status": "healthy",
                "message": "Versioning service running",
                "statistics": stats
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Versioning error: {e}"}
    
    # Event handlers
    async def _handle_threat_detected(self, event_data: Dict[str, Any]):
        """Handle threat detection events"""
        try:
            logger.warning(f"Threat detected: {event_data}")
            
            # Could trigger automated responses here
            # e.g., create backup, notify admins, etc.
            
        except Exception as e:
            logger.error(f"Error handling threat detected event: {e}")
    
    async def _handle_rule_violation(self, event_data: Dict[str, Any]):
        """Handle security rule violation events"""
        try:
            logger.warning(f"Security rule violation: {event_data}")
            
            # Could trigger automated responses here
            
        except Exception as e:
            logger.error(f"Error handling rule violation event: {e}")
    
    async def _handle_version_created(self, event_data: Dict[str, Any]):
        """Handle version creation events"""
        try:
            logger.debug(f"Version created: {event_data}")
            
            # Could trigger knowledge graph updates, etc.
            
        except Exception as e:
            logger.error(f"Error handling version created event: {e}")
    
    async def _handle_version_restored(self, event_data: Dict[str, Any]):
        """Handle version restoration events"""
        try:
            logger.info(f"Version restored: {event_data}")
            
            # Could trigger backup creation, etc.
            
        except Exception as e:
            logger.error(f"Error handling version restored event: {e}")
    
    async def _handle_backup_completed(self, event_data: Dict[str, Any]):
        """Handle backup completion events"""
        try:
            logger.info(f"Backup completed: {event_data}")
            
            # Could trigger cleanup, notifications, etc.
            
        except Exception as e:
            logger.error(f"Error handling backup completed event: {e}")
    
    async def _handle_backup_failed(self, event_data: Dict[str, Any]):
        """Handle backup failure events"""
        try:
            logger.error(f"Backup failed: {event_data}")
            
            # Could trigger alerts, retry logic, etc.
            
        except Exception as e:
            logger.error(f"Error handling backup failed event: {e}")
    
    async def _handle_node_added(self, event_data: Dict[str, Any]):
        """Handle knowledge graph node addition events"""
        try:
            logger.debug(f"Knowledge node added: {event_data}")
            
        except Exception as e:
            logger.error(f"Error handling node added event: {e}")
    
    async def _handle_relationship_added(self, event_data: Dict[str, Any]):
        """Handle knowledge graph relationship addition events"""
        try:
            logger.debug(f"Knowledge relationship added: {event_data}")
            
        except Exception as e:
            logger.error(f"Error handling relationship added event: {e}")
    
    async def _handle_system_startup(self, event_data: Dict[str, Any]):
        """Handle system startup events"""
        try:
            logger.info(f"System startup: {event_data}")
            
        except Exception as e:
            logger.error(f"Error handling system startup event: {e}")
    
    async def _handle_system_shutdown(self, event_data: Dict[str, Any]):
        """Handle system shutdown events"""
        try:
            logger.info(f"System shutdown: {event_data}")
            
        except Exception as e:
            logger.error(f"Error handling system shutdown event: {e}")


# Global system integration service instance
system_integration = SystemIntegrationService()
