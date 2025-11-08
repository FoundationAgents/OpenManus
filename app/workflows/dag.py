"""DAG (Directed Acyclic Graph) construction and validation"""
from typing import Dict, List, Set

from app.workflows.models import WorkflowDefinition, WorkflowNode


class DAGNode:
    """Node in the DAG with adjacency information"""
    
    def __init__(self, node: WorkflowNode):
        self.node = node
        self.id = node.id
        self.dependencies: List[str] = node.depends_on.copy()
        self.dependents: List[str] = []
        self.in_degree: int = len(node.depends_on)
        self.depth: int = 0  # For topological ordering
    
    def __repr__(self) -> str:
        return f"DAGNode({self.id}, deps={self.dependencies}, dependents={self.dependents})"


class WorkflowDAG:
    """Directed Acyclic Graph representation of a workflow"""
    
    def __init__(self, definition: WorkflowDefinition):
        self.definition = definition
        self.nodes: Dict[str, DAGNode] = {}
        self.node_map: Dict[str, WorkflowNode] = {}
        self._build_dag()
        self._validate()
    
    def _build_dag(self):
        """Build the DAG from workflow definition"""
        # Create nodes
        for node in self.definition.nodes:
            dag_node = DAGNode(node)
            self.nodes[node.id] = dag_node
            self.node_map[node.id] = node
        
        # Build adjacency lists
        for node_id, dag_node in self.nodes.items():
            for dep_id in dag_node.dependencies:
                if dep_id not in self.nodes:
                    raise ValueError(f"Node {node_id} depends on non-existent node {dep_id}")
                self.nodes[dep_id].dependents.append(node_id)
    
    def _validate(self):
        """Validate the DAG structure"""
        # Check start node exists
        if self.definition.start_node not in self.nodes:
            raise ValueError(f"Start node '{self.definition.start_node}' not found in workflow")
        
        # Check end nodes exist
        for end_node in self.definition.end_nodes:
            if end_node not in self.nodes:
                raise ValueError(f"End node '{end_node}' not found in workflow")
        
        # Check for cycles
        if self._has_cycle():
            raise ValueError("Workflow contains cycles - not a valid DAG")
        
        # Check all nodes are reachable from start
        reachable = self._get_reachable_nodes(self.definition.start_node)
        unreachable = set(self.nodes.keys()) - reachable
        if unreachable:
            raise ValueError(f"Nodes unreachable from start: {unreachable}")
        
        # Calculate depths for topological ordering
        self._calculate_depths()
    
    def _has_cycle(self) -> bool:
        """Detect cycles using DFS"""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for dependent in self.nodes[node_id].dependents:
                if dependent not in visited:
                    if dfs(dependent):
                        return True
                elif dependent in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        
        return False
    
    def _get_reachable_nodes(self, start_id: str) -> Set[str]:
        """Get all nodes reachable from start using BFS"""
        reachable: Set[str] = set()
        queue: List[str] = [start_id]
        
        while queue:
            node_id = queue.pop(0)
            if node_id in reachable:
                continue
            
            reachable.add(node_id)
            queue.extend(self.nodes[node_id].dependents)
        
        return reachable
    
    def _calculate_depths(self):
        """Calculate depth of each node for execution ordering"""
        # Topological sort using Kahn's algorithm
        in_degree = {nid: node.in_degree for nid, node in self.nodes.items()}
        queue = [nid for nid, degree in in_degree.items() if degree == 0]
        depth = 0
        
        while queue:
            next_level = []
            for node_id in queue:
                self.nodes[node_id].depth = depth
                for dependent in self.nodes[node_id].dependents:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_level.append(dependent)
            queue = next_level
            depth += 1
    
    def get_ready_nodes(self, completed: Set[str], running: Set[str]) -> List[str]:
        """Get nodes that are ready to execute"""
        ready = []
        for node_id, dag_node in self.nodes.items():
            # Skip if already completed or running
            if node_id in completed or node_id in running:
                continue
            
            # Check if all dependencies are satisfied
            deps_satisfied = all(dep in completed for dep in dag_node.dependencies)
            if deps_satisfied:
                ready.append(node_id)
        
        return ready
    
    def get_node(self, node_id: str) -> WorkflowNode:
        """Get workflow node by ID"""
        return self.node_map[node_id]
    
    def get_dependencies(self, node_id: str) -> List[str]:
        """Get direct dependencies of a node"""
        return self.nodes[node_id].dependencies
    
    def get_dependents(self, node_id: str) -> List[str]:
        """Get direct dependents of a node"""
        return self.nodes[node_id].dependents
    
    def get_execution_order(self) -> List[List[str]]:
        """Get execution order as levels (nodes in same level can run in parallel)"""
        max_depth = max(node.depth for node in self.nodes.values())
        levels: List[List[str]] = [[] for _ in range(max_depth + 1)]
        
        for node_id, dag_node in self.nodes.items():
            levels[dag_node.depth].append(node_id)
        
        return levels
    
    def visualize(self) -> str:
        """Generate a simple text representation of the DAG"""
        lines = ["Workflow DAG:", ""]
        levels = self.get_execution_order()
        
        for i, level in enumerate(levels):
            lines.append(f"Level {i}:")
            for node_id in level:
                node = self.node_map[node_id]
                deps = ", ".join(self.nodes[node_id].dependencies) or "none"
                lines.append(f"  - {node_id} ({node.type.value}) [deps: {deps}]")
            lines.append("")
        
        return "\n".join(lines)
