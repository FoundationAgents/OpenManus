"""Knowledge Graph module for managing concepts, documents, and code artifacts."""

import json
import sqlite3
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
from pydantic import BaseModel, Field


@dataclass
class NodeMetadata:
    """Metadata for graph nodes."""
    created_at: str
    updated_at: str
    version: int = 1
    tags: List[str] = None
    source: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "tags": self.tags,
            "source": self.source,
        }


class GraphNode(BaseModel):
    """Represents a node in the knowledge graph."""
    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(..., description="Type of node: concept, document, code_artifact, agent_memory")
    name: str = Field(..., description="Human-readable name")
    content: Optional[str] = Field(None, description="Node content/text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes")
    
    class Config:
        arbitrary_types_allowed = True


class GraphEdge(BaseModel):
    """Represents an edge in the knowledge graph."""
    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    edge_type: str = Field(..., description="Type of relationship: related_to, depends_on, references, implements, etc.")
    weight: float = Field(1.0, description="Edge weight/importance")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        arbitrary_types_allowed = True


class KnowledgeGraph:
    """Manages a knowledge graph with networkx and SQLite persistence."""
    
    def __init__(self, storage_path: str = "data/knowledge_graph", enable_persistence: bool = True):
        """Initialize the knowledge graph.
        
        Args:
            storage_path: Path for SQLite database storage
            enable_persistence: Whether to persist the graph to disk
        """
        self.storage_path = Path(storage_path)
        self.enable_persistence = enable_persistence
        self._lock = threading.RLock()
        self.graph: nx.DiGraph = nx.DiGraph()
        self._node_versions: Dict[str, int] = {}
        
        if self.enable_persistence:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self.db_path = self.storage_path / "knowledge_graph.db"
            self._init_database()
            self._load_from_db()
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create nodes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kg_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT,
                    metadata TEXT,
                    attributes TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    version INTEGER DEFAULT 1
                )
            """)
            
            # Create edges table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kg_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    metadata TEXT,
                    created_at TEXT,
                    FOREIGN KEY (source_id) REFERENCES kg_nodes(node_id),
                    FOREIGN KEY (target_id) REFERENCES kg_nodes(node_id),
                    UNIQUE(source_id, target_id, edge_type)
                )
            """)
            
            # Create indices for fast queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_node_type ON kg_nodes(node_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edge_type ON kg_edges(edge_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON kg_edges(source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_target ON kg_edges(target_id)")
            
            conn.commit()
    
    def add_node(
        self,
        node_id: str,
        node_type: str,
        name: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> GraphNode:
        """Add a node to the knowledge graph.
        
        Args:
            node_id: Unique node identifier
            node_type: Type of node (concept, document, code_artifact, agent_memory)
            name: Human-readable name
            content: Optional node content
            metadata: Optional metadata dictionary
            attributes: Optional custom attributes
            
        Returns:
            Created GraphNode
        """
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            
            if metadata is None:
                metadata = {}
            if attributes is None:
                attributes = {}
            
            # Add metadata
            node_metadata = NodeMetadata(
                created_at=metadata.get("created_at", now),
                updated_at=now,
                version=metadata.get("version", 1),
                tags=metadata.get("tags", []),
                source=metadata.get("source"),
            )
            
            metadata.update(node_metadata.to_dict())
            
            node = GraphNode(
                node_id=node_id,
                node_type=node_type,
                name=name,
                content=content,
                metadata=metadata,
                attributes=attributes,
            )
            
            self.graph.add_node(
                node_id,
                node_type=node_type,
                name=name,
                content=content,
                metadata=metadata,
                attributes=attributes,
            )
            
            self._node_versions[node_id] = metadata.get("version", 1)
            
            if self.enable_persistence:
                self._save_node_to_db(node)
            
            return node
    
    def update_node(
        self,
        node_id: str,
        name: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Optional[GraphNode]:
        """Update an existing node.
        
        Args:
            node_id: Node identifier
            name: Optional new name
            content: Optional new content
            metadata: Optional metadata updates
            attributes: Optional attributes updates
            
        Returns:
            Updated GraphNode or None if not found
        """
        with self._lock:
            if node_id not in self.graph:
                return None
            
            node_data = self.graph.nodes[node_id]
            now = datetime.now(timezone.utc).isoformat()
            
            if name is not None:
                node_data["name"] = name
            if content is not None:
                node_data["content"] = content
            
            node_metadata = node_data.get("metadata", {})
            node_metadata["updated_at"] = now
            node_metadata["version"] = node_metadata.get("version", 1) + 1
            
            if metadata is not None:
                node_metadata.update(metadata)
            
            node_data["metadata"] = node_metadata
            self._node_versions[node_id] = node_metadata["version"]
            
            if attributes is not None:
                node_attributes = node_data.get("attributes", {})
                node_attributes.update(attributes)
                node_data["attributes"] = node_attributes
            
            node = GraphNode(
                node_id=node_id,
                node_type=node_data["node_type"],
                name=node_data["name"],
                content=node_data.get("content"),
                metadata=node_data.get("metadata", {}),
                attributes=node_data.get("attributes", {}),
            )
            
            if self.enable_persistence:
                self._save_node_to_db(node)
            
            return node
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID.
        
        Args:
            node_id: Node identifier
            
        Returns:
            GraphNode or None if not found
        """
        with self._lock:
            if node_id not in self.graph:
                return None
            
            node_data = self.graph.nodes[node_id]
            return GraphNode(
                node_id=node_id,
                node_type=node_data["node_type"],
                name=node_data["name"],
                content=node_data.get("content"),
                metadata=node_data.get("metadata", {}),
                attributes=node_data.get("attributes", {}),
            )
    
    def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its edges.
        
        Args:
            node_id: Node identifier
            
        Returns:
            True if node was deleted, False if not found
        """
        with self._lock:
            if node_id not in self.graph:
                return False
            
            self.graph.remove_node(node_id)
            
            if node_id in self._node_versions:
                del self._node_versions[node_id]
            
            if self.enable_persistence:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM kg_nodes WHERE node_id = ?", (node_id,))
                    cursor.execute("DELETE FROM kg_edges WHERE source_id = ? OR target_id = ?", (node_id, node_id))
                    conn.commit()
            
            return True
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[GraphEdge]:
        """Add an edge between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            edge_type: Type of relationship
            weight: Edge weight/importance
            metadata: Optional metadata
            
        Returns:
            Created GraphEdge or None if nodes don't exist
        """
        with self._lock:
            if source_id not in self.graph or target_id not in self.graph:
                return None
            
            if metadata is None:
                metadata = {}
            
            now = datetime.now(timezone.utc).isoformat()
            metadata["created_at"] = metadata.get("created_at", now)
            
            edge = GraphEdge(
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                weight=weight,
                metadata=metadata,
            )
            
            self.graph.add_edge(
                source_id,
                target_id,
                edge_type=edge_type,
                weight=weight,
                metadata=metadata,
            )
            
            if self.enable_persistence:
                self._save_edge_to_db(edge)
            
            return edge
    
    def get_edge(self, source_id: str, target_id: str) -> Optional[GraphEdge]:
        """Get an edge between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            
        Returns:
            GraphEdge or None if not found
        """
        with self._lock:
            if not self.graph.has_edge(source_id, target_id):
                return None
            
            edge_data = self.graph.edges[source_id, target_id]
            return GraphEdge(
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_data["edge_type"],
                weight=edge_data.get("weight", 1.0),
                metadata=edge_data.get("metadata", {}),
            )
    
    def delete_edge(self, source_id: str, target_id: str) -> bool:
        """Delete an edge between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            
        Returns:
            True if edge was deleted, False if not found
        """
        with self._lock:
            if not self.graph.has_edge(source_id, target_id):
                return False
            
            self.graph.remove_edge(source_id, target_id)
            
            if self.enable_persistence:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM kg_edges WHERE source_id = ? AND target_id = ?",
                        (source_id, target_id),
                    )
                    conn.commit()
            
            return True
    
    def get_nodes_by_type(self, node_type: str) -> List[GraphNode]:
        """Get all nodes of a specific type.
        
        Args:
            node_type: Type of nodes to retrieve
            
        Returns:
            List of GraphNodes of the specified type
        """
        with self._lock:
            nodes = []
            for node_id, node_data in self.graph.nodes(data=True):
                if node_data.get("node_type") == node_type:
                    nodes.append(GraphNode(
                        node_id=node_id,
                        node_type=node_data["node_type"],
                        name=node_data["name"],
                        content=node_data.get("content"),
                        metadata=node_data.get("metadata", {}),
                        attributes=node_data.get("attributes", {}),
                    ))
            return nodes
    
    def get_neighbors(self, node_id: str, edge_type: Optional[str] = None) -> List[Tuple[str, str]]:
        """Get all neighbors of a node.
        
        Args:
            node_id: Node identifier
            edge_type: Optional filter by edge type
            
        Returns:
            List of (neighbor_id, edge_type) tuples
        """
        with self._lock:
            if node_id not in self.graph:
                return []
            
            neighbors = []
            for target in self.graph.successors(node_id):
                edge_data = self.graph.edges[node_id, target]
                edge_t = edge_data.get("edge_type", "")
                if edge_type is None or edge_t == edge_type:
                    neighbors.append((target, edge_t))
            
            return neighbors
    
    def get_predecessors(self, node_id: str, edge_type: Optional[str] = None) -> List[Tuple[str, str]]:
        """Get all predecessors of a node.
        
        Args:
            node_id: Node identifier
            edge_type: Optional filter by edge type
            
        Returns:
            List of (predecessor_id, edge_type) tuples
        """
        with self._lock:
            if node_id not in self.graph:
                return []
            
            predecessors = []
            for source in self.graph.predecessors(node_id):
                edge_data = self.graph.edges[source, node_id]
                edge_t = edge_data.get("edge_type", "")
                if edge_type is None or edge_t == edge_type:
                    predecessors.append((source, edge_t))
            
            return predecessors
    
    def find_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """Find a path between two nodes using BFS.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            
        Returns:
            List of node IDs forming a path, or None if no path exists
        """
        with self._lock:
            try:
                path = nx.shortest_path(self.graph, source_id, target_id)
                return path
            except (nx.NetworkXNoPath, nx.NetworkXError):
                return None
    
    def search_nodes(self, query: str, search_type: str = "name") -> List[GraphNode]:
        """Search for nodes by name or content.
        
        Args:
            query: Search query string
            search_type: Type of search - "name", "content", or "both"
            
        Returns:
            List of matching GraphNodes
        """
        with self._lock:
            results = []
            query_lower = query.lower()
            
            for node_id, node_data in self.graph.nodes(data=True):
                match = False
                
                if search_type in ("name", "both"):
                    if query_lower in node_data.get("name", "").lower():
                        match = True
                
                if search_type in ("content", "both") and not match:
                    content = node_data.get("content", "")
                    if content and query_lower in content.lower():
                        match = True
                
                if match:
                    results.append(GraphNode(
                        node_id=node_id,
                        node_type=node_data["node_type"],
                        name=node_data["name"],
                        content=node_data.get("content"),
                        metadata=node_data.get("metadata", {}),
                        attributes=node_data.get("attributes", {}),
                    ))
            
            return results
    
    def _save_node_to_db(self, node: GraphNode):
        """Save a node to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            metadata_json = json.dumps(node.metadata)
            attributes_json = json.dumps(node.attributes)
            
            cursor.execute("""
                INSERT OR REPLACE INTO kg_nodes 
                (node_id, node_type, name, content, metadata, attributes, created_at, updated_at, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node.node_id,
                node.node_type,
                node.name,
                node.content,
                metadata_json,
                attributes_json,
                node.metadata.get("created_at", datetime.now(timezone.utc).isoformat()),
                node.metadata.get("updated_at", datetime.now(timezone.utc).isoformat()),
                node.metadata.get("version", 1),
            ))
            
            conn.commit()
    
    def _save_edge_to_db(self, edge: GraphEdge):
        """Save an edge to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            metadata_json = json.dumps(edge.metadata)
            
            cursor.execute("""
                INSERT OR REPLACE INTO kg_edges 
                (source_id, target_id, edge_type, weight, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                edge.source_id,
                edge.target_id,
                edge.edge_type,
                edge.weight,
                metadata_json,
                edge.metadata.get("created_at", datetime.now(timezone.utc).isoformat()),
            ))
            
            conn.commit()
    
    def _load_from_db(self):
        """Load the graph from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Load nodes
            cursor.execute("SELECT * FROM kg_nodes")
            for row in cursor.fetchall():
                node_id, node_type, name, content, metadata_json, attributes_json, created_at, updated_at, version = row
                
                metadata = json.loads(metadata_json) if metadata_json else {}
                attributes = json.loads(attributes_json) if attributes_json else {}
                
                self.graph.add_node(
                    node_id,
                    node_type=node_type,
                    name=name,
                    content=content,
                    metadata=metadata,
                    attributes=attributes,
                )
                
                self._node_versions[node_id] = version
            
            # Load edges
            cursor.execute("SELECT source_id, target_id, edge_type, weight, metadata FROM kg_edges")
            for row in cursor.fetchall():
                source_id, target_id, edge_type, weight, metadata_json = row
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                self.graph.add_edge(
                    source_id,
                    target_id,
                    edge_type=edge_type,
                    weight=weight,
                    metadata=metadata,
                )
    
    def export_to_graphml(self, file_path: str):
        """Export the graph to GraphML format.
        
        Args:
            file_path: Path to save the GraphML file
        """
        with self._lock:
            export_graph = self.graph.copy()
            
            for node_id, node_data in export_graph.nodes(data=True):
                for key, value in node_data.items():
                    if value is None:
                        node_data[key] = ""
                    elif isinstance(value, dict):
                        node_data[key] = json.dumps(value)
                    elif not isinstance(value, (str, int, float, bool)):
                        node_data[key] = str(value)
            
            for source, target, edge_data in export_graph.edges(data=True):
                for key, value in edge_data.items():
                    if value is None:
                        edge_data[key] = ""
                    elif isinstance(value, dict):
                        edge_data[key] = json.dumps(value)
                    elif not isinstance(value, (str, int, float, bool)):
                        edge_data[key] = str(value)
            
            nx.write_graphml(export_graph, file_path)
    
    def import_from_graphml(self, file_path: str):
        """Import a graph from GraphML format.
        
        Args:
            file_path: Path to the GraphML file
        """
        with self._lock:
            self.graph = nx.read_graphml(file_path)
    
    def export_to_json(self, file_path: str):
        """Export the graph to JSON format.
        
        Args:
            file_path: Path to save the JSON file
        """
        with self._lock:
            nodes = []
            edges = []
            
            for node_id, node_data in self.graph.nodes(data=True):
                nodes.append({
                    "id": node_id,
                    "type": node_data.get("node_type"),
                    "name": node_data.get("name"),
                    "content": node_data.get("content"),
                    "metadata": node_data.get("metadata", {}),
                    "attributes": node_data.get("attributes", {}),
                })
            
            for source_id, target_id, edge_data in self.graph.edges(data=True):
                edges.append({
                    "source": source_id,
                    "target": target_id,
                    "type": edge_data.get("edge_type"),
                    "weight": edge_data.get("weight", 1.0),
                    "metadata": edge_data.get("metadata", {}),
                })
            
            data = {
                "nodes": nodes,
                "edges": edges,
                "exported_at": datetime.now(timezone.utc).isoformat(),
            }
            
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
    
    def import_from_json(self, file_path: str):
        """Import a graph from JSON format.
        
        Args:
            file_path: Path to the JSON file
        """
        with self._lock:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            self.graph.clear()
            self._node_versions.clear()
            
            for node_data in data.get("nodes", []):
                node_id = node_data.get("id")
                self.graph.add_node(
                    node_id,
                    node_type=node_data.get("type"),
                    name=node_data.get("name"),
                    content=node_data.get("content"),
                    metadata=node_data.get("metadata", {}),
                    attributes=node_data.get("attributes", {}),
                )
                
                version = node_data.get("metadata", {}).get("version", 1)
                self._node_versions[node_id] = version
            
            for edge_data in data.get("edges", []):
                self.graph.add_edge(
                    edge_data.get("source"),
                    edge_data.get("target"),
                    edge_type=edge_data.get("type"),
                    weight=edge_data.get("weight", 1.0),
                    metadata=edge_data.get("metadata", {}),
                )
            
            if self.enable_persistence:
                self._init_database()
                for node_id, node_data in self.graph.nodes(data=True):
                    node = GraphNode(
                        node_id=node_id,
                        node_type=node_data["node_type"],
                        name=node_data["name"],
                        content=node_data.get("content"),
                        metadata=node_data.get("metadata", {}),
                        attributes=node_data.get("attributes", {}),
                    )
                    self._save_node_to_db(node)
                
                for source_id, target_id, edge_data in self.graph.edges(data=True):
                    edge = GraphEdge(
                        source_id=source_id,
                        target_id=target_id,
                        edge_type=edge_data["edge_type"],
                        weight=edge_data.get("weight", 1.0),
                        metadata=edge_data.get("metadata", {}),
                    )
                    self._save_edge_to_db(edge)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics.
        
        Returns:
            Dictionary containing graph statistics
        """
        with self._lock:
            nodes_by_type = {}
            for node_id, node_data in self.graph.nodes(data=True):
                node_type = node_data.get("node_type", "unknown")
                nodes_by_type[node_type] = nodes_by_type.get(node_type, 0) + 1
            
            edges_by_type = {}
            for _, __, edge_data in self.graph.edges(data=True):
                edge_type = edge_data.get("edge_type", "unknown")
                edges_by_type[edge_type] = edges_by_type.get(edge_type, 0) + 1
            
            return {
                "total_nodes": self.graph.number_of_nodes(),
                "total_edges": self.graph.number_of_edges(),
                "nodes_by_type": nodes_by_type,
                "edges_by_type": edges_by_type,
                "density": nx.density(self.graph),
                "is_connected": nx.is_strongly_connected(self.graph),
            }
