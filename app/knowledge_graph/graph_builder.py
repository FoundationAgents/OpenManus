"""
Graph Builder
Automatically builds and updates the knowledge graph from system interactions
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from app.logger import logger
from app.config import config
from app.database.database_service import database_service, audit_service
from .knowledge_graph_service import knowledge_graph_service


class GraphBuilder:
    """Automatically builds knowledge graph from system data"""
    
    def __init__(self):
        self._update_task: Optional[asyncio.Task] = None
        self._running = False
        self._node_extractors = {
            "user": self._extract_user_nodes,
            "file": self._extract_file_nodes,
            "api": self._extract_api_nodes,
            "agent": self._extract_agent_nodes,
            "project": self._extract_project_nodes
        }
        self._relationship_extractors = {
            "user_file": self._extract_user_file_relationships,
            "user_agent": self._extract_user_agent_relationships,
            "file_api": self._extract_file_api_relationships,
            "agent_project": self._extract_agent_project_relationships
        }
    
    async def start(self):
        """Start the graph builder"""
        if not config.knowledge_graph.auto_update:
            logger.info("Graph builder auto-update disabled")
            return
        
        logger.info("Starting graph builder...")
        self._running = True
        self._update_task = asyncio.create_task(self._update_loop())
        logger.info("Graph builder started")
    
    async def stop(self):
        """Stop the graph builder"""
        logger.info("Stopping graph builder...")
        self._running = False
        
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Graph builder stopped")
    
    async def _update_loop(self):
        """Main update loop"""
        while self._running:
            try:
                await self._update_graph_from_system_data()
                await asyncio.sleep(3600)  # Update every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in graph builder loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _update_graph_from_system_data(self):
        """Update graph with recent system data"""
        try:
            logger.info("Updating knowledge graph from system data...")
            
            # Get recent data from various sources
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            # Extract nodes
            await self._extract_all_nodes(cutoff_time)
            
            # Extract relationships
            await self._extract_all_relationships(cutoff_time)
            
            logger.info("Knowledge graph update completed")
            
        except Exception as e:
            logger.error(f"Error updating graph from system data: {e}")
    
    async def _extract_all_nodes(self, cutoff_time: datetime):
        """Extract all types of nodes"""
        for node_type, extractor in self._node_extractors.items():
            try:
                await extractor(cutoff_time)
            except Exception as e:
                logger.error(f"Error extracting {node_type} nodes: {e}")
    
    async def _extract_all_relationships(self, cutoff_time: datetime):
        """Extract all types of relationships"""
        for rel_type, extractor in self._relationship_extractors.items():
            try:
                await extractor(cutoff_time)
            except Exception as e:
                logger.error(f"Error extracting {rel_type} relationships: {e}")
    
    async def _extract_user_nodes(self, cutoff_time: datetime):
        """Extract user nodes from audit logs"""
        try:
            async with await database_service.get_connection() as db:
                db.row_factory = None
                cursor = await db.execute("""
                    SELECT DISTINCT user_id, username, role, COUNT(*) as activity_count
                    FROM audit_logs al
                    LEFT JOIN acl_users u ON al.user_id = u.id
                    WHERE al.timestamp > ?
                    AND al.user_id IS NOT NULL
                    GROUP BY al.user_id, u.username, u.role
                """, (cutoff_time.isoformat(),))
                
                users = await cursor.fetchall()
                
                for user_id, username, role, activity_count in users:
                    if username is None:
                        continue
                    
                    # Create user node content
                    content = f"User: {username} (Role: {role or 'unknown'})"
                    metadata = {
                        "node_type": "user",
                        "username": username,
                        "role": role or "unknown",
                        "activity_count": activity_count,
                        "last_seen": datetime.now().isoformat()
                    }
                    
                    # Check if node already exists
                    existing_nodes = await knowledge_graph_service.search_nodes(
                        query=username,
                        node_type="user",
                        limit=1
                    )
                    
                    if existing_nodes:
                        # Update existing node
                        node_id = existing_nodes[0][0].id
                        await knowledge_graph_service.update_node(
                            node_id=node_id,
                            metadata=metadata
                        )
                    else:
                        # Create new node
                        await knowledge_graph_service.add_node(
                            node_type="user",
                            content=content,
                            metadata=metadata
                        )
            
            logger.debug(f"Processed {len(users)} user nodes")
            
        except Exception as e:
            logger.error(f"Error extracting user nodes: {e}")
    
    async def _extract_file_nodes(self, cutoff_time: datetime):
        """Extract file nodes from audit logs"""
        try:
            async with await database_service.get_connection() as db:
                db.row_factory = None
                cursor = await db.execute("""
                    SELECT DISTINCT resource, COUNT(*) as access_count,
                           SUM(CASE WHEN action LIKE '%read%' THEN 1 ELSE 0 END) as read_count,
                           SUM(CASE WHEN action LIKE '%write%' THEN 1 ELSE 0 END) as write_count
                    FROM audit_logs
                    WHERE timestamp > ?
                    AND resource IS NOT NULL
                    AND resource LIKE '%/%'  -- Filter for file paths
                    GROUP BY resource
                    HAVING access_count > 1  -- Only include accessed files
                """, (cutoff_time.isoformat(),))
                
                files = await cursor.fetchall()
                
                for file_path, access_count, read_count, write_count in files:
                    # Create file node content
                    content = f"File: {file_path}"
                    metadata = {
                        "node_type": "file",
                        "file_path": file_path,
                        "access_count": access_count,
                        "read_count": read_count,
                        "write_count": write_count,
                        "last_accessed": datetime.now().isoformat()
                    }
                    
                    # Check if node already exists
                    existing_nodes = await knowledge_graph_service.search_nodes(
                        query=file_path,
                        node_type="file",
                        limit=1
                    )
                    
                    if existing_nodes:
                        # Update existing node
                        node_id = existing_nodes[0][0].id
                        await knowledge_graph_service.update_node(
                            node_id=node_id,
                            metadata=metadata
                        )
                    else:
                        # Create new node
                        await knowledge_graph_service.add_node(
                            node_type="file",
                            content=content,
                            metadata=metadata
                        )
            
            logger.debug(f"Processed {len(files)} file nodes")
            
        except Exception as e:
            logger.error(f"Error extracting file nodes: {e}")
    
    async def _extract_api_nodes(self, cutoff_time: datetime):
        """Extract API nodes from audit logs"""
        try:
            async with await database_service.get_connection() as db:
                db.row_factory = None
                cursor = await db.execute("""
                    SELECT DISTINCT action, COUNT(*) as call_count,
                           AVG(CASE WHEN details LIKE '%response_time%' THEN 
                               CAST(SUBSTR(details, INSTR(details, ':') + 2) AS REAL)
                               ELSE NULL END) as avg_response_time
                    FROM audit_logs
                    WHERE timestamp > ?
                    AND action LIKE 'api_%'
                    GROUP BY action
                """, (cutoff_time.isoformat(),))
                
                apis = await cursor.fetchall()
                
                for action, call_count, avg_response_time in apis:
                    # Extract endpoint from action
                    endpoint = action.replace('api_', '').replace('_', '/')
                    
                    # Create API node content
                    content = f"API: {endpoint}"
                    metadata = {
                        "node_type": "api",
                        "endpoint": endpoint,
                        "call_count": call_count,
                        "avg_response_time": float(avg_response_time) if avg_response_time else None,
                        "last_called": datetime.now().isoformat()
                    }
                    
                    # Check if node already exists
                    existing_nodes = await knowledge_graph_service.search_nodes(
                        query=endpoint,
                        node_type="api",
                        limit=1
                    )
                    
                    if existing_nodes:
                        # Update existing node
                        node_id = existing_nodes[0][0].id
                        await knowledge_graph_service.update_node(
                            node_id=node_id,
                            metadata=metadata
                        )
                    else:
                        # Create new node
                        await knowledge_graph_service.add_node(
                            node_type="api",
                            content=content,
                            metadata=metadata
                        )
            
            logger.debug(f"Processed {len(apis)} API nodes")
            
        except Exception as e:
            logger.error(f"Error extracting API nodes: {e}")
    
    async def _extract_agent_nodes(self, cutoff_time: datetime):
        """Extract agent nodes from system logs"""
        try:
            # This would extract from agent activity logs
            # For now, create placeholder data
            agents = [
                {"name": "Architect Agent", "role": "architect"},
                {"name": "Developer Agent", "role": "developer"},
                {"name": "Tester Agent", "role": "tester"},
                {"name": "Security Agent", "role": "security"}
            ]
            
            for agent in agents:
                content = f"Agent: {agent['name']}"
                metadata = {
                    "node_type": "agent",
                    "agent_name": agent['name'],
                    "agent_role": agent['role'],
                    "status": "active",
                    "last_active": datetime.now().isoformat()
                }
                
                # Check if node already exists
                existing_nodes = await knowledge_graph_service.search_nodes(
                    query=agent['name'],
                    node_type="agent",
                    limit=1
                )
                
                if not existing_nodes:
                    # Create new node
                    await knowledge_graph_service.add_node(
                        node_type="agent",
                        content=content,
                        metadata=metadata
                    )
            
            logger.debug(f"Processed {len(agents)} agent nodes")
            
        except Exception as e:
            logger.error(f"Error extracting agent nodes: {e}")
    
    async def _extract_project_nodes(self, cutoff_time: datetime):
        """Extract project nodes from system data"""
        try:
            # This would extract from project management data
            # For now, create placeholder data
            projects = [
                {"name": "System Integration", "status": "in_progress"},
                {"name": "Knowledge Graph", "status": "active"},
                {"name": "Security Monitoring", "status": "active"}
            ]
            
            for project in projects:
                content = f"Project: {project['name']}"
                metadata = {
                    "node_type": "project",
                    "project_name": project['name'],
                    "status": project['status'],
                    "created_date": datetime.now().isoformat()
                }
                
                # Check if node already exists
                existing_nodes = await knowledge_graph_service.search_nodes(
                    query=project['name'],
                    node_type="project",
                    limit=1
                )
                
                if not existing_nodes:
                    # Create new node
                    await knowledge_graph_service.add_node(
                        node_type="project",
                        content=content,
                        metadata=metadata
                    )
            
            logger.debug(f"Processed {len(projects)} project nodes")
            
        except Exception as e:
            logger.error(f"Error extracting project nodes: {e}")
    
    async def _extract_user_file_relationships(self, cutoff_time: datetime):
        """Extract user-file relationships"""
        try:
            async with await database_service.get_connection() as db:
                cursor = await db.execute("""
                    SELECT u.username, al.resource, COUNT(*) as access_count
                    FROM audit_logs al
                    LEFT JOIN acl_users u ON al.user_id = u.id
                    WHERE al.timestamp > ?
                    AND al.resource IS NOT NULL
                    AND al.resource LIKE '%/%'
                    AND u.username IS NOT NULL
                    GROUP BY al.user_id, al.resource, u.username
                    HAVING access_count > 1
                """, (cutoff_time.isoformat(),))
                
                relationships = await cursor.fetchall()
                
                for username, file_path, access_count in relationships:
                    # Find user and file nodes
                    user_nodes = await knowledge_graph_service.search_nodes(username, "user", 1)
                    file_nodes = await knowledge_graph_service.search_nodes(file_path, "file", 1)
                    
                    if user_nodes and file_nodes:
                        user_id = user_nodes[0][0].id
                        file_id = file_nodes[0][0].id
                        
                        # Check if relationship already exists
                        neighbors = await knowledge_graph_service.get_node_neighbors(user_id)
                        existing_rel = any(
                            neighbor[0].id == file_id for neighbor in neighbors
                        )
                        
                        if not existing_rel:
                            await knowledge_graph_service.add_relationship(
                                source_id=user_id,
                                target_id=file_id,
                                relationship_type="accesses",
                                weight=float(access_count) / 10.0,  # Normalize weight
                                metadata={"access_count": access_count}
                            )
            
            logger.debug(f"Processed {len(relationships)} user-file relationships")
            
        except Exception as e:
            logger.error(f"Error extracting user-file relationships: {e}")
    
    async def _extract_user_agent_relationships(self, cutoff_time: datetime):
        """Extract user-agent relationships"""
        try:
            # This would extract from user-agent interaction logs
            # For now, create some example relationships
            user_agent_interactions = [
                ("admin", "Architect Agent", "manages"),
                ("admin", "Security Agent", "monitors"),
                ("developer", "Developer Agent", "uses"),
                ("tester", "Tester Agent", "uses")
            ]
            
            for username, agent_name, relationship_type in user_agent_interactions:
                user_nodes = await knowledge_graph_service.search_nodes(username, "user", 1)
                agent_nodes = await knowledge_graph_service.search_nodes(agent_name, "agent", 1)
                
                if user_nodes and agent_nodes:
                    user_id = user_nodes[0][0].id
                    agent_id = agent_nodes[0][0].id
                    
                    # Check if relationship already exists
                    neighbors = await knowledge_graph_service.get_node_neighbors(user_id)
                    existing_rel = any(
                        neighbor[0].id == agent_id for neighbor in neighbors
                    )
                    
                    if not existing_rel:
                        await knowledge_graph_service.add_relationship(
                            source_id=user_id,
                            target_id=agent_id,
                            relationship_type=relationship_type,
                            weight=1.0
                        )
            
            logger.debug("Processed user-agent relationships")
            
        except Exception as e:
            logger.error(f"Error extracting user-agent relationships: {e}")
    
    async def _extract_file_api_relationships(self, cutoff_time: datetime):
        """Extract file-API relationships"""
        try:
            # This would extract from API access logs that reference files
            # For now, create placeholder relationships
            pass
            
        except Exception as e:
            logger.error(f"Error extracting file-API relationships: {e}")
    
    async def _extract_agent_project_relationships(self, cutoff_time: datetime):
        """Extract agent-project relationships"""
        try:
            # This would extract from project assignment data
            agent_project_assignments = [
                ("Architect Agent", "System Integration", "works_on"),
                ("Security Agent", "Security Monitoring", "works_on"),
                ("Developer Agent", "System Integration", "works_on"),
                ("Developer Agent", "Knowledge Graph", "works_on")
            ]
            
            for agent_name, project_name, relationship_type in agent_project_assignments:
                agent_nodes = await knowledge_graph_service.search_nodes(agent_name, "agent", 1)
                project_nodes = await knowledge_graph_service.search_nodes(project_name, "project", 1)
                
                if agent_nodes and project_nodes:
                    agent_id = agent_nodes[0][0].id
                    project_id = project_nodes[0][0].id
                    
                    # Check if relationship already exists
                    neighbors = await knowledge_graph_service.get_node_neighbors(agent_id)
                    existing_rel = any(
                        neighbor[0].id == project_id for neighbor in neighbors
                    )
                    
                    if not existing_rel:
                        await knowledge_graph_service.add_relationship(
                            source_id=agent_id,
                            target_id=project_id,
                            relationship_type=relationship_type,
                            weight=1.0
                        )
            
            logger.debug("Processed agent-project relationships")
            
        except Exception as e:
            logger.error(f"Error extracting agent-project relationships: {e}")


# Global graph builder instance
graph_builder = GraphBuilder()
