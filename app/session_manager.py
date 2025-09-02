"""
OpenManus Session Manager

Manages user-specific OpenManus agent instances for multi-user support.
Each user gets their own isolated agent instance with TTL-based lifecycle management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from app.agent.manus import Manus
from app.logger import logger


class ManusSession:
    """Individual user session containing a Manus agent instance"""
    
    def __init__(self, user_id: str, agent: Manus):
        self.user_id = user_id
        self.agent = agent
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.is_active = True
    
    def touch(self) -> None:
        """Update last used timestamp"""
        self.last_used = datetime.now()
    
    async def cleanup(self) -> None:
        """Clean up session resources"""
        if self.agent:
            try:
                await self.agent.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up agent for user {self.user_id}: {e}")
        self.is_active = False


class ManusSessionManager:
    """
    Session manager for OpenManus agents with multi-user support
    
    Features:
    - User-specific agent instances
    - TTL-based automatic cleanup
    - Resource management with maximum session limits
    - Thread-safe operations with per-user locks
    """
    
    def __init__(self, ttl_minutes: int = 30, max_sessions: int = 100, cleanup_interval_minutes: int = 5):
        self.sessions: Dict[str, ManusSession] = {}
        self.user_locks: Dict[str, asyncio.Lock] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_sessions = max_sessions
        self.cleanup_interval = timedelta(minutes=cleanup_interval_minutes)
        
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
    async def start(self) -> None:
        """Start the session manager and cleanup task"""
        logger.info("Starting OpenManus session manager")
        self._shutdown_event.clear()
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Session manager started successfully")
    
    async def stop(self) -> None:
        """Stop the session manager and cleanup all sessions"""
        logger.info("Stopping OpenManus session manager")
        self._shutdown_event.set()
        
        if self._cleanup_task:
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Cleanup task did not finish within timeout, cancelling")
                self._cleanup_task.cancel()
        
        # Cleanup all remaining sessions
        await self._cleanup_all_sessions()
        logger.info("Session manager stopped")
    
    def _get_user_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create a lock for a specific user"""
        if user_id not in self.user_locks:
            self.user_locks[user_id] = asyncio.Lock()
        return self.user_locks[user_id]
    
    def _is_expired(self, user_id: str) -> bool:
        """Check if a user's session has expired"""
        if user_id not in self.sessions:
            return True
        
        session = self.sessions[user_id]
        return datetime.now() - session.last_used > self.ttl
    
    async def get_agent(self, user_id: str, room_id: Optional[str] = None) -> Manus:
        """
        Get a Manus agent instance for the specified user
        
        Creates a new session if one doesn't exist or has expired.
        Thread-safe with per-user locking.
        """
        async with self._get_user_lock(user_id):
            # Check if session exists and is still valid
            if user_id not in self.sessions or self._is_expired(user_id):
                logger.info(f"Creating new session for user: {user_id}")
                
                # Cleanup expired session if it exists
                if user_id in self.sessions:
                    await self._remove_session_unsafe(user_id)
                
                # Check session limit
                if len(self.sessions) >= self.max_sessions:
                    await self._cleanup_oldest_sessions(1)
                
                # Create new session
                await self._create_session_unsafe(user_id, room_id)
            
            # Update last used time and return agent
            session = self.sessions[user_id]
            session.touch()
            
            logger.debug(f"Retrieved agent for user: {user_id}")
            return session.agent
    
    async def _create_session_unsafe(self, user_id: str, room_id: Optional[str] = None) -> None:
        """Create a new session (not thread-safe, use within lock)"""
        try:
            # Create new Manus agent instance with user-specific configuration
            agent = await Manus.create(user_id=user_id, room_id=room_id)
            session = ManusSession(user_id, agent)
            
            self.sessions[user_id] = session
            logger.info(f"Created session for user {user_id} (total sessions: {len(self.sessions)})")
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            raise
    
    async def remove_session(self, user_id: str) -> None:
        """Manually remove a user's session"""
        async with self._get_user_lock(user_id):
            await self._remove_session_unsafe(user_id)
    
    async def _remove_session_unsafe(self, user_id: str) -> None:
        """Remove session without locking (use within lock)"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            await session.cleanup()
            del self.sessions[user_id]
            logger.info(f"Removed session for user {user_id} (total sessions: {len(self.sessions)})")
    
    def touch_session(self, user_id: str) -> None:
        """Update the last used time for a user's session"""
        if user_id in self.sessions:
            self.sessions[user_id].touch()
    
    async def _cleanup_loop(self) -> None:
        """Background task to cleanup expired sessions"""
        while not self._shutdown_event.is_set():
            try:
                await self._cleanup_expired_sessions()
                
                # Wait for next cleanup cycle or shutdown
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), 
                        timeout=self.cleanup_interval.total_seconds()
                    )
                    break  # Shutdown event was set
                except asyncio.TimeoutError:
                    continue  # Timeout is normal, continue loop
                    
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait a bit before retrying
    
    async def _cleanup_expired_sessions(self) -> None:
        """Clean up all expired sessions"""
        expired_users = []
        
        # Find expired sessions
        for user_id, session in self.sessions.items():
            if datetime.now() - session.last_used > self.ttl:
                expired_users.append(user_id)
        
        # Remove expired sessions
        if expired_users:
            logger.info(f"Cleaning up {len(expired_users)} expired sessions")
            
            for user_id in expired_users:
                try:
                    async with self._get_user_lock(user_id):
                        await self._remove_session_unsafe(user_id)
                except Exception as e:
                    logger.error(f"Error removing expired session for user {user_id}: {e}")
    
    async def _cleanup_oldest_sessions(self, count: int) -> None:
        """Remove the oldest sessions to make room for new ones"""
        if not self.sessions:
            return
            
        # Sort sessions by last used time
        sorted_sessions = sorted(
            self.sessions.items(), 
            key=lambda item: item[1].last_used
        )
        
        # Remove the oldest sessions
        sessions_to_remove = sorted_sessions[:count]
        
        for user_id, _ in sessions_to_remove:
            try:
                async with self._get_user_lock(user_id):
                    await self._remove_session_unsafe(user_id)
                    logger.info(f"Removed oldest session for user {user_id} to make room")
            except Exception as e:
                logger.error(f"Error removing oldest session for user {user_id}: {e}")
    
    async def _cleanup_all_sessions(self) -> None:
        """Clean up all sessions during shutdown"""
        if not self.sessions:
            return
            
        logger.info(f"Cleaning up all {len(self.sessions)} sessions")
        
        # Create list to avoid modifying dict during iteration
        user_ids = list(self.sessions.keys())
        
        for user_id in user_ids:
            try:
                async with self._get_user_lock(user_id):
                    await self._remove_session_unsafe(user_id)
            except Exception as e:
                logger.error(f"Error cleaning up session for user {user_id}: {e}")
    
    def get_stats(self) -> Dict:
        """Get session manager statistics"""
        active_sessions = len(self.sessions)
        
        if not self.sessions:
            return {
                "active_sessions": 0,
                "oldest_session": None,
                "newest_session": None,
                "total_locks": len(self.user_locks)
            }
        
        oldest_session = min(self.sessions.values(), key=lambda s: s.created_at)
        newest_session = max(self.sessions.values(), key=lambda s: s.created_at)
        
        return {
            "active_sessions": active_sessions,
            "max_sessions": self.max_sessions,
            "ttl_minutes": self.ttl.total_seconds() / 60,
            "oldest_session": {
                "user_id": oldest_session.user_id,
                "created_at": oldest_session.created_at.isoformat(),
                "last_used": oldest_session.last_used.isoformat()
            },
            "newest_session": {
                "user_id": newest_session.user_id,
                "created_at": newest_session.created_at.isoformat(),
                "last_used": newest_session.last_used.isoformat()
            },
            "total_locks": len(self.user_locks)
        }