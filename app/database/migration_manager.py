"""
Database Migration Manager
Handles schema migrations for all system databases
"""

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import aiosqlite
from pydantic import BaseModel

from app.logger import logger
from app.config import config


class Migration(BaseModel):
    """Represents a database migration"""
    version: str
    description: str
    up_sql: str
    down_sql: Optional[str] = None
    dependencies: List[str] = []
    created_at: datetime = datetime.now()


class MigrationManager:
    """Manages database migrations for all subsystems"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or "./data/system.db"
        self.migrations: Dict[str, Migration] = {}
        self._ensure_data_directory()
    
    def _ensure_data_directory(self):
        """Ensure the data directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def register_migration(self, migration: Migration):
        """Register a migration"""
        self.migrations[migration.version] = migration
        logger.info(f"Registered migration {migration.version}: {migration.description}")
    
    async def initialize_database(self):
        """Initialize the database and create migrations table"""
        async with aiosqlite.connect(self.db_path) as db:
            # Create migrations tracking table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checksum TEXT
                )
            """)
            
            # Create initial tables for all subsystems
            await self._create_initial_tables(db)
            
            await db.commit()
            logger.info("Database initialized successfully")
    
    async def _create_initial_tables(self, db: aiosqlite.Connection):
        """Create initial tables for all subsystems"""
        
        # ACL tables
        await db.execute("""
            CREATE TABLE IF NOT EXISTS acl_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS acl_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                resource TEXT NOT NULL,
                action TEXT NOT NULL,
                granted BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES acl_users (id)
            )
        """)
        
        # Versioning tables
        await db.execute("""
            CREATE TABLE IF NOT EXISTS file_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                version INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                content BLOB,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_path, version)
            )
        """)
        
        # Backup tables
        await db.execute("""
            CREATE TABLE IF NOT EXISTS backup_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_name TEXT NOT NULL,
                backup_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                checksum TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                restored_at TIMESTAMP
            )
        """)
        
        # Knowledge graph tables
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_type TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_node_id INTEGER NOT NULL,
                target_node_id INTEGER NOT NULL,
                relationship_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_node_id) REFERENCES knowledge_nodes (id),
                FOREIGN KEY (target_node_id) REFERENCES knowledge_nodes (id)
            )
        """)
        
        # Audit logs tables
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                resource TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES acl_users (id)
            )
        """)
        
        # Guardian security tables
        await db.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT,
                source_ip TEXT,
                user_id INTEGER,
                metadata TEXT,
                resolved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES acl_users (id)
            )
        """)
        
        # System metrics tables
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                labels TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT version FROM schema_migrations ORDER BY version")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    
    async def apply_migrations(self):
        """Apply all pending migrations"""
        applied = await self.get_applied_migrations()
        
        # Sort migrations by version
        sorted_migrations = sorted(
            self.migrations.values(), 
            key=lambda m: m.version
        )
        
        for migration in sorted_migrations:
            if migration.version not in applied:
                await self._apply_migration(migration)
    
    async def _apply_migration(self, migration: Migration):
        """Apply a single migration"""
        logger.info(f"Applying migration {migration.version}: {migration.description}")
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                # Execute migration SQL
                await db.execute(migration.up_sql)
                
                # Record migration
                await db.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                    (migration.version, migration.description)
                )
                
                await db.commit()
                logger.info(f"Migration {migration.version} applied successfully")
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to apply migration {migration.version}: {e}")
                raise
    
    async def rollback_migration(self, version: str):
        """Rollback a specific migration"""
        if version not in self.migrations:
            raise ValueError(f"Migration {version} not found")
        
        migration = self.migrations[version]
        if not migration.down_sql:
            raise ValueError(f"Migration {version} cannot be rolled back")
        
        logger.info(f"Rolling back migration {version}")
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(migration.down_sql)
                await db.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
                await db.commit()
                logger.info(f"Migration {version} rolled back successfully")
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to rollback migration {version}: {e}")
                raise


# Register default migrations
def register_default_migrations(manager: MigrationManager):
    """Register default system migrations"""
    
    # Initial migration for indexes
    migration_001 = Migration(
        version="001",
        description="Add database indexes for performance",
        up_sql="""
            -- ACL indexes
            CREATE INDEX IF NOT EXISTS idx_acl_users_username ON acl_users(username);
            CREATE INDEX IF NOT EXISTS idx_acl_permissions_user_resource ON acl_permissions(user_id, resource);
            
            -- Versioning indexes
            CREATE INDEX IF NOT EXISTS idx_file_versions_path ON file_versions(file_path);
            CREATE INDEX IF NOT EXISTS idx_file_versions_created ON file_versions(created_at);
            
            -- Backup indexes
            CREATE INDEX IF NOT EXISTS idx_backup_records_type ON backup_records(backup_type);
            CREATE INDEX IF NOT EXISTS idx_backup_records_created ON backup_records(created_at);
            
            -- Knowledge graph indexes
            CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_type ON knowledge_nodes(node_type);
            CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_source ON knowledge_relationships(source_node_id);
            CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_target ON knowledge_relationships(target_node_id);
            
            -- Audit logs indexes
            CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
            
            -- Security events indexes
            CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events(severity);
            CREATE INDEX IF NOT EXISTS idx_security_events_created ON security_events(created_at);
            
            -- System metrics indexes
            CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name);
            CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);
        """,
        down_sql="""
            DROP INDEX IF EXISTS idx_acl_users_username;
            DROP INDEX IF EXISTS idx_acl_permissions_user_resource;
            DROP INDEX IF EXISTS idx_file_versions_path;
            DROP INDEX IF EXISTS idx_file_versions_created;
            DROP INDEX IF EXISTS idx_backup_records_type;
            DROP INDEX IF EXISTS idx_backup_records_created;
            DROP INDEX IF EXISTS idx_knowledge_nodes_type;
            DROP INDEX IF EXISTS idx_knowledge_relationships_source;
            DROP INDEX IF EXISTS idx_knowledge_relationships_target;
            DROP INDEX IF EXISTS idx_audit_logs_user;
            DROP INDEX IF EXISTS idx_audit_logs_timestamp;
            DROP INDEX IF EXISTS idx_audit_logs_action;
            DROP INDEX IF EXISTS idx_security_events_type;
            DROP INDEX IF EXISTS idx_security_events_severity;
            DROP INDEX IF EXISTS idx_security_events_created;
            DROP INDEX IF EXISTS idx_system_metrics_name;
            DROP INDEX IF EXISTS idx_system_metrics_timestamp;
        """
    )
    
    manager.register_migration(migration_001)
