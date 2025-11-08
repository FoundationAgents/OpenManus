"""
Knowledge Graph Service
Manages knowledge nodes, relationships, and vector embeddings
"""

import asyncio
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import networkx as nx
import numpy as np
from pydantic import BaseModel

from app.logger import logger
from app.config import config
from app.database.database_service import database_service, knowledge_graph_service as db_kg_service
from .vector_store import VectorStore


class KnowledgeNode(BaseModel):
    """Represents a knowledge node"""
    id: Optional[int] = None
    node_type: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KnowledgeRelationship(BaseModel):
    """Represents a relationship between knowledge nodes"""
    id: Optional[int] = None
    source_node_id: int
    target_node_id: int
    relationship_type: str
    weight: float = 1.0
    metadata: Dict[str, Any] = {}
    created_at: Optional[datetime] = None


class KnowledgeGraphService:
    """Main knowledge graph service"""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.graph = nx.DiGraph()
        self._node_cache: Dict[int, KnowledgeNode] = {}
        self._relationship_cache: Dict[int, KnowledgeRelationship] = {}
        self._embedding_cache: Dict[str, np.ndarray] = {}
    
    async def initialize(self):
        """Initialize knowledge graph service"""
        if not config.knowledge_graph.enable_knowledge_graph:
            logger.info("Knowledge graph disabled in configuration")
            return
        
        logger.info("Initializing knowledge graph service...")
        
        # Initialize vector store
        await self.vector_store.initialize()
        
        # Load existing graph from database
        await self._load_graph_from_database()
        
        # Start auto-update task if enabled
        if config.knowledge_graph.auto_update:
            asyncio.create_task(self._auto_update_loop())
        
        logger.info("Knowledge graph service initialized")
    
    async def _load_graph_from_database(self):
        """Load existing knowledge graph from database"""
        try:
            # Load nodes
            nodes = await db_kg_service.search_nodes()
            for node_data in nodes:
                node = KnowledgeNode(**node_data)
                self.graph.add_node(
                    node.id, 
                    node_type=node.node_type,
                    content=node.content,
                    metadata=node.metadata
                )
                self._node_cache[node.id] = node
            
            # Load relationships
            async with await database_service.get_connection() as db:
                db.row_factory = None
                cursor = await db.execute("""
                    SELECT source_node_id, target_node_id, relationship_type, weight, metadata
                    FROM knowledge_relationships
                """)
                relationships = await cursor.fetchall()
                
                for rel_data in relationships:
                    source_id, target_id, rel_type, weight, metadata = rel_data
                    self.graph.add_edge(
                        source_id, target_id,
                        relationship_type=rel_type,
                        weight=weight,
                        metadata=json.loads(metadata) if metadata else {}
                    )
            
            logger.info(f"Loaded {len(self.graph.nodes)} nodes and {len(self.graph.edges)} relationships")
            
        except Exception as e:
            logger.error(f"Error loading graph from database: {e}")
    
    async def add_node(self, node_type: str, content: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> int:
        """Add a new knowledge node"""
        try:
            # Generate embedding
            embedding = await self.vector_store.get_embedding(content)
            
            # Save to database
            node_id = await db_kg_service.create_node(
                node_type=node_type,
                content=content,
                embedding=pickle.dumps(embedding) if embedding is not None else None,
                metadata=metadata or {}
            )
            
            # Add to in-memory graph
            node = KnowledgeNode(
                id=node_id,
                node_type=node_type,
                content=content,
                embedding=embedding.tolist() if embedding is not None else None,
                metadata=metadata or {},
                created_at=datetime.now()
            )
            
            self.graph.add_node(
                node_id,
                node_type=node.node_type,
                content=node.content,
                metadata=node.metadata
            )
            self._node_cache[node_id] = node
            
            # Add to vector store
            if embedding is not None:
                await self.vector_store.add_vector(node_id, embedding)
            
            logger.info(f"Added knowledge node {node_id} of type {node_type}")
            return node_id
            
        except Exception as e:
            logger.error(f"Error adding knowledge node: {e}")
            raise
    
    async def add_relationship(self, source_id: int, target_id: int, 
                             relationship_type: str, weight: float = 1.0,
                             metadata: Optional[Dict[str, Any]] = None) -> int:
        """Add a relationship between nodes"""
        try:
            # Validate nodes exist
            if source_id not in self.graph or target_id not in self.graph:
                raise ValueError("Source or target node does not exist")
            
            # Save to database
            rel_id = await db_kg_service.create_relationship(
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type,
                weight=weight,
                metadata=metadata or {}
            )
            
            # Add to in-memory graph
            rel = KnowledgeRelationship(
                id=rel_id,
                source_node_id=source_id,
                target_node_id=target_id,
                relationship_type=relationship_type,
                weight=weight,
                metadata=metadata or {},
                created_at=datetime.now()
            )
            
            self.graph.add_edge(
                source_id, target_id,
                relationship_type=relationship_type,
                weight=weight,
                metadata=rel.metadata
            )
            self._relationship_cache[rel_id] = rel
            
            logger.info(f"Added relationship {rel_id}: {source_id} -> {target_id} ({relationship_type})")
            return rel_id
            
        except Exception as e:
            logger.error(f"Error adding relationship: {e}")
            raise
    
    async def search_nodes(self, query: str, node_type: Optional[str] = None,
                         limit: int = 10) -> List[Tuple[KnowledgeNode, float]]:
        """Search for nodes using semantic similarity"""
        try:
            # Get query embedding
            query_embedding = await self.vector_store.get_embedding(query)
            
            # Search vector store
            similar_nodes = await self.vector_store.search_similar(
                query_embedding, limit=limit * 2  # Get more to filter
            )
            
            # Filter by node type if specified
            results = []
            for node_id, similarity in similar_nodes:
                if node_id in self._node_cache:
                    node = self._node_cache[node_id]
                    if node_type is None or node.node_type == node_type:
                        if similarity >= config.knowledge_graph.similarity_threshold:
                            results.append((node, similarity))
            
            # Sort by similarity and limit results
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching nodes: {e}")
            return []
    
    async def find_related_nodes(self, node_id: int, relationship_types: Optional[List[str]] = None,
                               max_depth: int = 2, limit: int = 20) -> List[KnowledgeNode]:
        """Find nodes related to a given node"""
        try:
            if node_id not in self.graph:
                return []
            
            related_nodes = set()
            
            # BFS to find related nodes
            visited = set()
            queue = [(node_id, 0)]
            
            while queue and len(related_nodes) < limit:
                current_id, depth = queue.pop(0)
                
                if current_id in visited or depth > max_depth:
                    continue
                
                visited.add(current_id)
                
                # Get neighbors
                for neighbor in self.graph.neighbors(current_id):
                    edge_data = self.graph[current_id][neighbor]
                    
                    # Filter by relationship type if specified
                    if relationship_types is None or edge_data.get('relationship_type') in relationship_types:
                        if neighbor != node_id:  # Don't include the original node
                            related_nodes.add(neighbor)
                            if neighbor not in visited:
                                queue.append((neighbor, depth + 1))
            
            # Convert to KnowledgeNode objects
            results = []
            for nid in related_nodes:
                if nid in self._node_cache:
                    results.append(self._node_cache[nid])
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error finding related nodes: {e}")
            return []
    
    async def get_node_neighbors(self, node_id: int) -> List[Tuple[KnowledgeNode, KnowledgeRelationship]]:
        """Get immediate neighbors of a node"""
        try:
            if node_id not in self.graph:
                return []
            
            neighbors = []
            
            for neighbor_id in self.graph.neighbors(node_id):
                if neighbor_id in self._node_cache:
                    edge_data = self.graph[node_id][neighbor_id]
                    
                    neighbor_node = self._node_cache[neighbor_id]
                    relationship = KnowledgeRelationship(
                        source_node_id=node_id,
                        target_node_id=neighbor_id,
                        relationship_type=edge_data.get('relationship_type', 'related'),
                        weight=edge_data.get('weight', 1.0),
                        metadata=edge_data.get('metadata', {})
                    )
                    
                    neighbors.append((neighbor_node, relationship))
            
            return neighbors
            
        except Exception as e:
            logger.error(f"Error getting node neighbors: {e}")
            return []
    
    async def update_node(self, node_id: int, content: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update an existing node"""
        try:
            if node_id not in self._node_cache:
                return False
            
            node = self._node_cache[node_id]
            
            # Update content and embedding if provided
            if content is not None:
                node.content = content
                embedding = await self.vector_store.get_embedding(content)
                node.embedding = embedding.tolist() if embedding is not None else None
                
                # Update database
                async with await database_service.get_connection() as db:
                    await db.execute("""
                        UPDATE knowledge_nodes 
                        SET content = ?, embedding = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (content, pickle.dumps(embedding) if embedding else None, node_id))
                    await db.commit()
                
                # Update vector store
                if embedding is not None:
                    await self.vector_store.update_vector(node_id, embedding)
            
            # Update metadata if provided
            if metadata is not None:
                node.metadata.update(metadata)
                
                # Update database
                async with await database_service.get_connection() as db:
                    await db.execute("""
                        UPDATE knowledge_nodes 
                        SET metadata = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (json.dumps(node.metadata), node_id))
                    await db.commit()
            
            # Update in-memory graph
            self.graph.nodes[node_id]['content'] = node.content
            self.graph.nodes[node_id]['metadata'] = node.metadata
            
            logger.info(f"Updated knowledge node {node_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating node {node_id}: {e}")
            return False
    
    async def delete_node(self, node_id: int) -> bool:
        """Delete a node and its relationships"""
        try:
            if node_id not in self._node_cache:
                return False
            
            # Delete from vector store
            await self.vector_store.delete_vector(node_id)
            
            # Delete from database
            async with await database_service.get_connection() as db:
                await db.execute("DELETE FROM knowledge_relationships WHERE source_node_id = ? OR target_node_id = ?", 
                               (node_id, node_id))
                await db.execute("DELETE FROM knowledge_nodes WHERE id = ?", (node_id,))
                await db.commit()
            
            # Remove from in-memory graph
            self.graph.remove_node(node_id)
            
            # Remove from cache
            del self._node_cache[node_id]
            
            # Remove related relationships from cache
            to_remove = []
            for rel_id, rel in self._relationship_cache.items():
                if rel.source_node_id == node_id or rel.target_node_id == node_id:
                    to_remove.append(rel_id)
            
            for rel_id in to_remove:
                del self._relationship_cache[rel_id]
            
            logger.info(f"Deleted knowledge node {node_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting node {node_id}: {e}")
            return False
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get graph statistics"""
        try:
            stats = {
                "total_nodes": len(self.graph.nodes),
                "total_relationships": len(self.graph.edges),
                "node_types": {},
                "relationship_types": {},
                "average_degree": 0.0,
                "graph_density": 0.0,
                "connected_components": 0
            }
            
            # Node type distribution
            for node_id in self.graph.nodes():
                node_type = self.graph.nodes[node_id].get('node_type', 'unknown')
                stats["node_types"][node_type] = stats["node_types"].get(node_type, 0) + 1
            
            # Relationship type distribution
            for source, target, data in self.graph.edges(data=True):
                rel_type = data.get('relationship_type', 'related')
                stats["relationship_types"][rel_type] = stats["relationship_types"].get(rel_type, 0) + 1
            
            # Graph metrics
            if len(self.graph.nodes) > 0:
                stats["average_degree"] = sum(dict(self.graph.degree()).values()) / len(self.graph.nodes)
                stats["graph_density"] = nx.density(self.graph)
                stats["connected_components"] = nx.number_connected_components(self.graph.to_undirected())
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating graph statistics: {e}")
            return {}
    
    async def _auto_update_loop(self):
        """Auto-update loop for knowledge graph"""
        while True:
            try:
                # This would integrate with other systems to auto-update the graph
                # For now, just log periodic maintenance
                await asyncio.sleep(3600)  # Check every hour
                
                # Perform cleanup if needed
                await self._perform_maintenance()
                
            except Exception as e:
                logger.error(f"Error in auto-update loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _perform_maintenance(self):
        """Perform graph maintenance tasks"""
        try:
            # Check if we need to prune old nodes
            if len(self.graph.nodes) > config.knowledge_graph.max_nodes:
                await self._prune_old_nodes()
            
            # Check if we need to prune relationships
            if len(self.graph.edges) > config.knowledge_graph.max_relationships:
                await self._prune_weak_relationships()
                
        except Exception as e:
            logger.error(f"Error during maintenance: {e}")
    
    async def _prune_old_nodes(self):
        """Prune old nodes based on some criteria"""
        # This would implement pruning logic based on age, usage, etc.
        logger.info("Pruning old nodes (placeholder)")
    
    async def _prune_weak_relationships(self):
        """Prune weak relationships"""
        # This would implement pruning logic based on weight, age, etc.
        logger.info("Pruning weak relationships (placeholder)")


# Global knowledge graph service instance
knowledge_graph_service = KnowledgeGraphService()
