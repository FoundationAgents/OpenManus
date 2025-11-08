"""
Database Service
Provides database access for all subsystems
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import aiosqlite
from pydantic import BaseModel

from app.logger import logger
from app.config import config
from .migration_manager import MigrationManager, register_default_migrations


class DatabaseService:
    """Main database service for all subsystems"""
    
    def __init__(self):
        self.db_path = "./data/system.db"
        self.migration_manager = MigrationManager(self.db_path)
        self._connection_pool: Optional[aiosqlite.Connection] = None
    
    async def initialize(self):
        """Initialize database and apply migrations"""
        logger.info("Initializing database service...")
        
        # Register default migrations
        register_default_migrations(self.migration_manager)
        
        # Initialize database
        await self.migration_manager.initialize_database()
        
        # Apply pending migrations
        await self.migration_manager.apply_migrations()
        
        logger.info("Database service initialized successfully")
    
    async def get_connection(self) -> aiosqlite.Connection:
        """Get a database connection"""
        if not self._connection_pool:
            self._connection_pool = await aiosqlite.connect(self.db_path)
        return self._connection_pool
    
    async def close(self):
        """Close database connections"""
        if self._connection_pool:
            await self._connection_pool.close()
            self._connection_pool = None


# ACL Service
class ACLService:
    """Access Control Layer service"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    async def create_user(self, username: str, email: str, role: str = "user") -> int:
        """Create a new user"""
        async with await self.db_service.get_connection() as db:
            cursor = await db.execute(
                "INSERT INTO acl_users (username, email, role) VALUES (?, ?, ?)",
                (username, email, role)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        async with await self.db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM acl_users WHERE id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def check_permission(self, user_id: int, resource: str, action: str) -> bool:
        """Check if user has permission for action on resource"""
        async with await self.db_service.get_connection() as db:
            cursor = await db.execute(
                """
                SELECT granted FROM acl_permissions 
                WHERE user_id = ? AND resource = ? AND action = ? AND granted = TRUE
                """,
                (user_id, resource, action)
            )
            row = await cursor.fetchone()
            return row is not None
    
    async def grant_permission(self, user_id: int, resource: str, action: str, granted: bool = True):
        """Grant or revoke permission"""
        async with await self.db_service.get_connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO acl_permissions (user_id, resource, action, granted)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, resource, action, granted)
            )
            await db.commit()


# Versioning Service  
class VersioningService:
    """File versioning service"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    async def create_version(self, file_path: str, content: bytes, metadata: Dict[str, Any] = None) -> int:
        """Create a new file version"""
        import hashlib
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Get next version number
        async with await self.db_service.get_connection() as db:
            cursor = await db.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM file_versions WHERE file_path = ?",
                (file_path,)
            )
            version = (await cursor.fetchone())[0]
            
            # Insert version
            cursor = await db.execute(
                """
                INSERT INTO file_versions (file_path, version, content_hash, content, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (file_path, version, content_hash, content, json.dumps(metadata or {}))
            )
            await db.commit()
            return cursor.lastrowid
    
    async def get_version(self, file_path: str, version: int) -> Optional[Dict[str, Any]]:
        """Get specific file version"""
        async with await self.db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM file_versions WHERE file_path = ? AND version = ?",
                (file_path, version)
            )
            row = await cursor.fetchone()
            if row:
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
                return result
            return None
    
    async def get_latest_version(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get latest file version"""
        async with await self.db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM file_versions 
                WHERE file_path = ? 
                ORDER BY version DESC 
                LIMIT 1
                """,
                (file_path,)
            )
            row = await cursor.fetchone()
            if row:
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
                return result
            return None
    
    async def list_versions(self, file_path: str) -> List[Dict[str, Any]]:
        """List all versions of a file"""
        async with await self.db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT version, content_hash, created_at, metadata
                FROM file_versions 
                WHERE file_path = ? 
                ORDER BY version DESC
                """,
                (file_path,)
            )
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
                results.append(result)
            return results


# Backup Service
class BackupService:
    """Backup management service"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    async def record_backup(self, backup_name: str, backup_type: str, file_path: str, 
                          file_size: int, checksum: str) -> int:
        """Record a backup operation"""
        async with await self.db_service.get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO backup_records (backup_name, backup_type, file_path, file_size, checksum)
                VALUES (?, ?, ?, ?, ?)
                """,
                (backup_name, backup_type, file_path, file_size, checksum)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def list_backups(self, backup_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List backup records"""
        async with await self.db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            if backup_type:
                cursor = await db.execute(
                    "SELECT * FROM backup_records WHERE backup_type = ? ORDER BY created_at DESC",
                    (backup_type,)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM backup_records ORDER BY created_at DESC"
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# Knowledge Graph Service
class KnowledgeGraphService:
    """Knowledge graph management service"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    async def create_node(self, node_type: str, content: str, 
                         embedding: Optional[bytes] = None, 
                         metadata: Dict[str, Any] = None) -> int:
        """Create a knowledge node"""
        async with await self.db_service.get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO knowledge_nodes (node_type, content, embedding, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (node_type, content, embedding, json.dumps(metadata or {}))
            )
            await db.commit()
            return cursor.lastrowid
    
    async def create_relationship(self, source_id: int, target_id: int, 
                                relationship_type: str, weight: float = 1.0,
                                metadata: Dict[str, Any] = None) -> int:
        """Create a relationship between nodes"""
        async with await self.db_service.get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO knowledge_relationships 
                (source_node_id, target_node_id, relationship_type, weight, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (source_id, target_id, relationship_type, weight, json.dumps(metadata or {}))
            )
            await db.commit()
            return cursor.lastrowid
    
    async def search_nodes(self, node_type: Optional[str] = None, 
                          content_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search knowledge nodes"""
        async with await self.db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM knowledge_nodes WHERE 1=1"
            params = []
            
            if node_type:
                query += " AND node_type = ?"
                params.append(node_type)
            
            if content_query:
                query += " AND content LIKE ?"
                params.append(f"%{content_query}%")
            
            query += " ORDER BY created_at DESC"
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
                results.append(result)
            return results


# Audit Service
class AuditService:
    """Audit logging service"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    async def log_action(self, user_id: Optional[int], action: str, resource: Optional[str] = None,
                        details: Optional[str] = None, ip_address: Optional[str] = None,
                        user_agent: Optional[str] = None):
        """Log an audit action"""
        async with await self.db_service.get_connection() as db:
            await db.execute(
                """
                INSERT INTO audit_logs (user_id, action, resource, details, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, action, resource, details, ip_address, user_agent)
            )
            await db.commit()
    
    async def get_audit_logs(self, user_id: Optional[int] = None, 
                           action: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit logs"""
        async with await self.db_service.get_connection() as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if action:
                query += " AND action = ?"
                params.append(action)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# Global database service instance
database_service = DatabaseService()
acl_service = ACLService(database_service)
versioning_service = VersioningService(database_service)
backup_service = BackupService(database_service)
knowledge_graph_service = KnowledgeGraphService(database_service)
audit_service = AuditService(database_service)
