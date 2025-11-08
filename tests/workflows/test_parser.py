"""Tests for workflow parser"""
import json
import tempfile
from pathlib import Path

import pytest
import yaml

from app.workflows.models import NodeType, WorkflowDefinition
from app.workflows.parser import WorkflowParser


def test_parse_yaml_workflow():
    """Test parsing YAML workflow"""
    yaml_content = """
metadata:
  name: Test Workflow
  version: 1.0.0
  description: A test workflow

nodes:
  - id: start
    type: agent
    name: Start Node
    target: test_agent
    params:
      key: value

  - id: process
    type: tool
    name: Process Node
    target: process_tool
    depends_on:
      - start

start_node: start
end_nodes:
  - process
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = Path(f.name)
    
    try:
        definition = WorkflowParser.parse_file(temp_path)
        
        assert definition.metadata.name == "Test Workflow"
        assert definition.metadata.version == "1.0.0"
        assert len(definition.nodes) == 2
        assert definition.start_node == "start"
        assert "process" in definition.end_nodes
        
    finally:
        temp_path.unlink()


def test_parse_json_workflow():
    """Test parsing JSON workflow"""
    json_content = {
        "metadata": {
            "name": "JSON Workflow",
            "version": "2.0.0"
        },
        "nodes": [
            {
                "id": "node1",
                "type": "service",
                "name": "Service Node",
                "target": "api_service"
            }
        ],
        "start_node": "node1"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(json_content, f)
        temp_path = Path(f.name)
    
    try:
        definition = WorkflowParser.parse_file(temp_path)
        
        assert definition.metadata.name == "JSON Workflow"
        assert definition.metadata.version == "2.0.0"
        assert len(definition.nodes) == 1
        
    finally:
        temp_path.unlink()


def test_parse_workflow_with_retry():
    """Test parsing workflow with retry policy"""
    data = {
        "metadata": {"name": "Test"},
        "nodes": [
            {
                "id": "retry_node",
                "type": "agent",
                "name": "Retry Node",
                "retry_policy": {
                    "max_attempts": 5,
                    "backoff_factor": 3.0,
                    "initial_delay": 2.0,
                    "max_delay": 120.0
                }
            }
        ],
        "start_node": "retry_node"
    }
    
    definition = WorkflowParser.parse_dict(data)
    node = definition.nodes[0]
    
    assert node.retry_policy is not None
    assert node.retry_policy.max_attempts == 5
    assert node.retry_policy.backoff_factor == 3.0


def test_parse_workflow_with_condition():
    """Test parsing workflow with conditions"""
    data = {
        "metadata": {"name": "Test"},
        "nodes": [
            {
                "id": "cond_node",
                "type": "agent",
                "name": "Conditional Node",
                "condition": {
                    "expression": "result == 'success'",
                    "context_vars": ["result"]
                }
            }
        ],
        "start_node": "cond_node"
    }
    
    definition = WorkflowParser.parse_dict(data)
    node = definition.nodes[0]
    
    assert node.condition is not None
    assert node.condition.expression == "result == 'success'"


def test_parse_workflow_with_loop():
    """Test parsing workflow with loop"""
    data = {
        "metadata": {"name": "Test"},
        "nodes": [
            {
                "id": "loop_node",
                "type": "agent",
                "name": "Loop Node",
                "loop": {
                    "type": "foreach",
                    "items": "data_items",
                    "max_iterations": 100
                }
            }
        ],
        "start_node": "loop_node"
    }
    
    definition = WorkflowParser.parse_dict(data)
    node = definition.nodes[0]
    
    assert node.loop is not None
    assert node.loop.type == "foreach"
    assert node.loop.items == "data_items"


def test_parse_invalid_file_format():
    """Test parsing unsupported file format"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("invalid content")
        temp_path = Path(f.name)
    
    try:
        with pytest.raises(ValueError, match="Unsupported file format"):
            WorkflowParser.parse_file(temp_path)
    finally:
        temp_path.unlink()


def test_parse_missing_start_node():
    """Test parsing workflow without start_node"""
    data = {
        "metadata": {"name": "Test"},
        "nodes": [
            {"id": "node1", "type": "agent", "name": "Node 1"}
        ]
    }
    
    with pytest.raises(ValueError, match="start_node"):
        WorkflowParser.parse_dict(data)


def test_to_yaml():
    """Test converting workflow to YAML"""
    from app.workflows.models import WorkflowMetadata, WorkflowNode
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test", version="1.0.0"),
        nodes=[
            WorkflowNode(id="node1", type=NodeType.AGENT, name="Node 1")
        ],
        start_node="node1"
    )
    
    yaml_str = WorkflowParser.to_yaml(definition)
    
    assert "name: Test" in yaml_str
    assert "version: 1.0.0" in yaml_str
    assert "node1" in yaml_str


def test_to_json():
    """Test converting workflow to JSON"""
    from app.workflows.models import WorkflowMetadata, WorkflowNode
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test", version="1.0.0"),
        nodes=[
            WorkflowNode(id="node1", type=NodeType.AGENT, name="Node 1")
        ],
        start_node="node1"
    )
    
    json_str = WorkflowParser.to_json(definition)
    data = json.loads(json_str)
    
    assert data["metadata"]["name"] == "Test"
    assert data["start_node"] == "node1"
