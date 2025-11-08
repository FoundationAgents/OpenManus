"""Tests for DAG construction and validation"""
import pytest

from app.workflows.dag import WorkflowDAG
from app.workflows.models import (
    NodeType,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowNode,
)


def test_dag_creation():
    """Test basic DAG creation"""
    nodes = [
        WorkflowNode(id="start", type=NodeType.AGENT, name="Start"),
        WorkflowNode(id="middle", type=NodeType.TOOL, name="Middle", depends_on=["start"]),
        WorkflowNode(id="end", type=NodeType.AGENT, name="End", depends_on=["middle"])
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="start"
    )
    
    dag = WorkflowDAG(definition)
    
    assert "start" in dag.nodes
    assert "middle" in dag.nodes
    assert "end" in dag.nodes


def test_dag_dependencies():
    """Test DAG dependency relationships"""
    nodes = [
        WorkflowNode(id="a", type=NodeType.AGENT, name="A"),
        WorkflowNode(id="b", type=NodeType.AGENT, name="B", depends_on=["a"]),
        WorkflowNode(id="c", type=NodeType.AGENT, name="C", depends_on=["a"]),
        WorkflowNode(id="d", type=NodeType.AGENT, name="D", depends_on=["b", "c"])
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="a"
    )
    
    dag = WorkflowDAG(definition)
    
    # Check dependencies
    assert dag.get_dependencies("a") == []
    assert dag.get_dependencies("b") == ["a"]
    assert dag.get_dependencies("d") == ["b", "c"]
    
    # Check dependents
    assert set(dag.get_dependents("a")) == {"b", "c"}
    assert "d" in dag.get_dependents("b")


def test_dag_cycle_detection():
    """Test that cycles are detected"""
    nodes = [
        WorkflowNode(id="a", type=NodeType.AGENT, name="A", depends_on=["c"]),
        WorkflowNode(id="b", type=NodeType.AGENT, name="B", depends_on=["a"]),
        WorkflowNode(id="c", type=NodeType.AGENT, name="C", depends_on=["b"])
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="a"
    )
    
    with pytest.raises(ValueError, match="cycle"):
        WorkflowDAG(definition)


def test_dag_invalid_dependency():
    """Test detection of non-existent dependency"""
    nodes = [
        WorkflowNode(id="a", type=NodeType.AGENT, name="A"),
        WorkflowNode(id="b", type=NodeType.AGENT, name="B", depends_on=["nonexistent"])
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="a"
    )
    
    with pytest.raises(ValueError, match="non-existent"):
        WorkflowDAG(definition)


def test_dag_unreachable_nodes():
    """Test detection of unreachable nodes"""
    nodes = [
        WorkflowNode(id="a", type=NodeType.AGENT, name="A"),
        WorkflowNode(id="b", type=NodeType.AGENT, name="B", depends_on=["a"]),
        WorkflowNode(id="isolated", type=NodeType.AGENT, name="Isolated")
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="a"
    )
    
    with pytest.raises(ValueError, match="unreachable"):
        WorkflowDAG(definition)


def test_dag_execution_order():
    """Test topological execution order"""
    nodes = [
        WorkflowNode(id="a", type=NodeType.AGENT, name="A"),
        WorkflowNode(id="b", type=NodeType.AGENT, name="B", depends_on=["a"]),
        WorkflowNode(id="c", type=NodeType.AGENT, name="C", depends_on=["a"]),
        WorkflowNode(id="d", type=NodeType.AGENT, name="D", depends_on=["b", "c"])
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="a"
    )
    
    dag = WorkflowDAG(definition)
    levels = dag.get_execution_order()
    
    # Level 0 should have 'a'
    assert "a" in levels[0]
    
    # Level 1 should have 'b' and 'c' (can run in parallel)
    assert set(levels[1]) == {"b", "c"}
    
    # Level 2 should have 'd'
    assert "d" in levels[2]


def test_dag_get_ready_nodes():
    """Test getting ready nodes for execution"""
    nodes = [
        WorkflowNode(id="a", type=NodeType.AGENT, name="A"),
        WorkflowNode(id="b", type=NodeType.AGENT, name="B", depends_on=["a"]),
        WorkflowNode(id="c", type=NodeType.AGENT, name="C", depends_on=["a"]),
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="a"
    )
    
    dag = WorkflowDAG(definition)
    
    # Initially, only 'a' should be ready
    ready = dag.get_ready_nodes(completed=set(), running=set())
    assert "a" in ready
    
    # After 'a' completes, 'b' and 'c' should be ready
    ready = dag.get_ready_nodes(completed={"a"}, running=set())
    assert set(ready) == {"b", "c"}
    
    # If 'b' is running, only 'c' should be ready
    ready = dag.get_ready_nodes(completed={"a"}, running={"b"})
    assert ready == ["c"]


def test_dag_invalid_start_node():
    """Test that invalid start node raises error"""
    nodes = [
        WorkflowNode(id="a", type=NodeType.AGENT, name="A")
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="nonexistent"
    )
    
    with pytest.raises(ValueError, match="Start node"):
        WorkflowDAG(definition)


def test_dag_visualize():
    """Test DAG visualization text output"""
    nodes = [
        WorkflowNode(id="a", type=NodeType.AGENT, name="A"),
        WorkflowNode(id="b", type=NodeType.AGENT, name="B", depends_on=["a"])
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="a"
    )
    
    dag = WorkflowDAG(definition)
    viz = dag.visualize()
    
    assert "Workflow DAG" in viz
    assert "a" in viz
    assert "b" in viz
