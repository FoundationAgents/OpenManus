"""
Agent Pool Service
Singleton service for managing agent pools across the system
"""

import asyncio
from typing import Optional

from app.logger import logger
from app.database.database_service import DatabaseService
from app.system_integration.event_bus import EventBus
from .pool_manager import PoolManager


class PoolService:
    """Service for managing agent pools"""
    
    _instance: Optional["PoolService"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.pool_manager: Optional[PoolManager] = None
        self._initialized = False
    
    async def initialize(self, db_service: DatabaseService, event_bus: Optional[EventBus] = None):
        """Initialize the pool service with dependencies"""
        if self._initialized:
            return
        
        logger.info("Initializing pool service...")
        
        self.pool_manager = PoolManager(db_service, event_bus)
        await self.pool_manager.initialize()
        
        self._initialized = True
        logger.info("Pool service initialized successfully")
    
    async def shutdown(self):
        """Shutdown the pool service"""
        if not self._initialized:
            return
        
        logger.info("Shutting down pool service...")
        if self.pool_manager:
            await self.pool_manager.stop()
        
        self._initialized = False
    
    def get_pool_manager(self) -> Optional[PoolManager]:
        """Get the pool manager instance"""
        return self.pool_manager


# Global pool service instance
pool_service = PoolService()
