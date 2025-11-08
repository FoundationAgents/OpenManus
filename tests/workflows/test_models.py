"""Tests for workflow models"""
import pytest
from app.workflows.models import (
    Condition,
    LoopConfig,
    NodeType,
    RetryPolicy,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowNode,
)


def test_retry_policy_creation():
    """Test retry policy model"""
    policy = RetryPolicy(
        max_attempts=5,
        backoff_factor=2.0,
        initial_delay=1.0,
        max_delay=30.0
    )
    
    assert policy.max_attempts == 5
    assert policy.backoff_factor == 2.0
    assert policy.initial_delay == 1.0
    assert policy.max_delay == 30.0


def test_workflow_node_creation():
    """Test workflow node creation"""
    node = WorkflowNode(
        id="test_node",
        type=NodeType.AGENT,
        name="Test Node",
        target="test_agent",
        params={"key": "value"},
        depends_on=["dep1", "dep2"]
    )
    
    assert node.id == "test_node"
    assert node.type == NodeType.AGENT
    assert node.name == "Test Node"
    assert node.target == "test_agent"
    assert node.params == {"key": "value"}
    assert node.depends_on == ["dep1", "dep2"]


def test_workflow_node_with_condition():
    """Test node with conditional execution"""
    condition = Condition(
        expression="x > 10",
        context_vars=["x"]
    )
    
    node = WorkflowNode(
        id="conditional_node",
        type=NodeType.AGENT,
        name="Conditional Node",
        condition=condition
    )
    
    assert node.condition is not None
    assert node.condition.expression == "x > 10"
    assert "x" in node.condition.context_vars


def test_workflow_node_with_loop():
    """Test node with loop configuration"""
    loop = LoopConfig(
        type="foreach",
        items="items_list",
        max_iterations=50
    )
    
    node = WorkflowNode(
        id="loop_node",
        type=NodeType.AGENT,
        name="Loop Node",
        loop=loop
    )
    
    assert node.loop is not None
    assert node.loop.type == "foreach"
    assert node.loop.items == "items_list"
    assert node.loop.max_iterations == 50


def test_workflow_definition_validation():
    """Test workflow definition validation"""
    metadata = WorkflowMetadata(
        name="Test Workflow",
        version="1.0.0"
    )
    
    nodes = [
        WorkflowNode(id="node1", type=NodeType.AGENT, name="Node 1"),
        WorkflowNode(id="node2", type=NodeType.TOOL, name="Node 2", depends_on=["node1"])
    ]
    
    definition = WorkflowDefinition(
        metadata=metadata,
        nodes=nodes,
        start_node="node1",
        end_nodes=["node2"]
    )
    
    assert definition.metadata.name == "Test Workflow"
    assert len(definition.nodes) == 2
    assert definition.start_node == "node1"


def test_workflow_definition_duplicate_ids():
    """Test that duplicate node IDs raise error"""
    metadata = WorkflowMetadata(name="Test")
    
    nodes = [
        WorkflowNode(id="node1", type=NodeType.AGENT, name="Node 1"),
        WorkflowNode(id="node1", type=NodeType.TOOL, name="Node 2")  # Duplicate ID
    ]
    
    with pytest.raises(ValueError, match="Duplicate node IDs"):
        WorkflowDefinition(
            metadata=metadata,
            nodes=nodes,
            start_node="node1"
        )


def test_workflow_node_id_validation():
    """Test node ID validation"""
    with pytest.raises(ValueError):
        WorkflowNode(
            id="",  # Empty ID
            type=NodeType.AGENT,
            name="Test"
        )


def test_workflow_definition_empty_nodes():
    """Test that empty node list raises error"""
    metadata = WorkflowMetadata(name="Test")
    
    with pytest.raises(ValueError, match="at least one node"):
        WorkflowDefinition(
            metadata=metadata,
            nodes=[],
            start_node="node1"
        )
