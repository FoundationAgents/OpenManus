"""Knowledge graph implementation for hierarchical memory organization."""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""
    CONCEPT = "concept"
    DOCUMENT = "document"
    TASK = "task"
    AGENT = "agent"
    TOOL = "tool"
    RESULT = "result"
    CONTEXT = "context"


class EdgeType(str, Enum):
    """Types of relationships between nodes."""
    REFERENCES = "references"
    DEPENDS_ON = "depends_on"
    CONTAINS = "contains"
    RELATED_TO = "related_to"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    IMPLEMENTS = "implements"


@dataclass
class GraphNode:
    """Represents a node in the knowledge graph."""
    id: str
    node_type: NodeType
    content: str
    metadata: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: __import__('time').time())
    weight: float = 1.0
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, GraphNode):
            return False
        return self.id == other.id


@dataclass
class GraphEdge:
    """Represents an edge (relationship) in the knowledge graph."""
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    metadata: Dict = field(default_factory=dict)
    
    def __hash__(self):
        return hash((self.source_id, self.target_id, self.edge_type))
    
    def __eq__(self, other):
        if not isinstance(other, GraphEdge):
            return False
        return (
            self.source_id == other.source_id
            and self.target_id == other.target_id
            and self.edge_type == other.edge_type
        )


class KnowledgeGraph(BaseModel):
    """In-memory knowledge graph with traversal capabilities."""
    
    nodes: Dict[str, GraphNode] = Field(default_factory=dict)
    edges: List[GraphEdge] = Field(default_factory=list)
    adjacency_list: Dict[str, List[str]] = Field(default_factory=dict)
    reverse_adjacency_list: Dict[str, List[str]] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
    
    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        if node.id not in self.adjacency_list:
            self.adjacency_list[node.id] = []
        if node.id not in self.reverse_adjacency_list:
            self.reverse_adjacency_list[node.id] = []
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its connected edges."""
        if node_id not in self.nodes:
            return False
        
        # Remove connected edges
        self.edges = [
            e for e in self.edges
            if e.source_id != node_id and e.target_id != node_id
        ]
        
        # Clean adjacency lists
        if node_id in self.adjacency_list:
            for target in self.adjacency_list[node_id]:
                if target in self.reverse_adjacency_list:
                    self.reverse_adjacency_list[target] = [
                        n for n in self.reverse_adjacency_list[target] if n != node_id
                    ]
        
        if node_id in self.reverse_adjacency_list:
            for source in self.reverse_adjacency_list[node_id]:
                if source in self.adjacency_list:
                    self.adjacency_list[source] = [
                        n for n in self.adjacency_list[source] if n != node_id
                    ]
        
        del self.nodes[node_id]
        del self.adjacency_list[node_id]
        del self.reverse_adjacency_list[node_id]
        
        return True
    
    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge between two nodes."""
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            raise ValueError(
                f"Both nodes must exist: {edge.source_id}, {edge.target_id}"
            )
        
        # Avoid duplicate edges
        for existing_edge in self.edges:
            if (existing_edge.source_id == edge.source_id
                and existing_edge.target_id == edge.target_id
                and existing_edge.edge_type == edge.edge_type):
                return
        
        self.edges.append(edge)
        self.adjacency_list[edge.source_id].append(edge.target_id)
        self.reverse_adjacency_list[edge.target_id].append(edge.source_id)
    
    def remove_edge(self, source_id: str, target_id: str, edge_type: EdgeType) -> bool:
        """Remove an edge between two nodes."""
        for i, edge in enumerate(self.edges):
            if (edge.source_id == source_id
                and edge.target_id == target_id
                and edge.edge_type == edge_type):
                self.edges.pop(i)
                
                # Update adjacency lists
                if target_id in self.adjacency_list[source_id]:
                    self.adjacency_list[source_id].remove(target_id)
                if source_id in self.reverse_adjacency_list[target_id]:
                    self.reverse_adjacency_list[target_id].remove(source_id)
                
                return True
        return False
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_neighbors(self, node_id: str) -> List[GraphNode]:
        """Get immediate neighbors of a node."""
        if node_id not in self.adjacency_list:
            return []
        
        neighbors = []
        for target_id in self.adjacency_list[node_id]:
            if target_id in self.nodes:
                neighbors.append(self.nodes[target_id])
        
        return neighbors
    
    def get_incoming(self, node_id: str) -> List[GraphNode]:
        """Get nodes pointing to this node."""
        if node_id not in self.reverse_adjacency_list:
            return []
        
        incoming = []
        for source_id in self.reverse_adjacency_list[node_id]:
            if source_id in self.nodes:
                incoming.append(self.nodes[source_id])
        
        return incoming
    
    def bfs_traversal(
        self, 
        start_node_id: str, 
        max_depth: int = 3,
        node_types: Optional[List[NodeType]] = None
    ) -> List[GraphNode]:
        """Breadth-first search traversal from a starting node."""
        if start_node_id not in self.nodes:
            return []
        
        visited = set()
        queue = [(start_node_id, 0)]
        result = []
        
        while queue:
            node_id, depth = queue.pop(0)
            
            if node_id in visited or depth > max_depth:
                continue
            
            visited.add(node_id)
            node = self.nodes.get(node_id)
            
            if node and (node_types is None or node.node_type in node_types):
                result.append(node)
            
            # Add neighbors to queue
            for neighbor_id in self.adjacency_list.get(node_id, []):
                if neighbor_id not in visited:
                    queue.append((neighbor_id, depth + 1))
        
        return result
    
    def weighted_traversal(
        self,
        start_node_id: str,
        max_depth: int = 3,
        weight_threshold: float = 0.1
    ) -> List[Tuple[GraphNode, float]]:
        """Traverse graph considering node and edge weights."""
        if start_node_id not in self.nodes:
            return []
        
        visited = {}
        queue = [(start_node_id, 0, 1.0)]  # (node_id, depth, accumulated_weight)
        result = []
        
        while queue:
            node_id, depth, acc_weight = queue.pop(0)
            
            if node_id in visited or depth > max_depth or acc_weight < weight_threshold:
                continue
            
            visited[node_id] = acc_weight
            node = self.nodes.get(node_id)
            
            if node:
                result.append((node, acc_weight))
            
            # Add weighted neighbors
            for edge in self.edges:
                if edge.source_id == node_id and edge.target_id not in visited:
                    new_weight = acc_weight * edge.weight * node.weight
                    if new_weight >= weight_threshold:
                        queue.append((edge.target_id, depth + 1, new_weight))
        
        return result
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> Optional[List[str]]:
        """Find shortest path between two nodes using BFS."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return None
        
        if source_id == target_id:
            return [source_id]
        
        visited = set()
        queue = [(source_id, [source_id])]
        
        while queue:
            node_id, path = queue.pop(0)
            
            if node_id in visited or len(path) > max_depth:
                continue
            
            visited.add(node_id)
            
            for neighbor_id in self.adjacency_list.get(node_id, []):
                if neighbor_id == target_id:
                    return path + [target_id]
                
                if neighbor_id not in visited:
                    queue.append((neighbor_id, path + [neighbor_id]))
        
        return None
    
    def clear(self) -> None:
        """Clear all nodes and edges."""
        self.nodes.clear()
        self.edges.clear()
        self.adjacency_list.clear()
        self.reverse_adjacency_list.clear()
    
    def size(self) -> Tuple[int, int]:
        """Get the number of nodes and edges."""
        return len(self.nodes), len(self.edges)
