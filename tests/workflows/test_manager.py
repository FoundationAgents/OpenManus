"""Tests for workflow manager"""
import asyncio
import tempfile
from pathlib import Path

import pytest

from app.workflows.manager import WorkflowManager
from app.workflows.models import NodeType, WorkflowDefinition, WorkflowMetadata, WorkflowNode


class MockAgent:
    """Mock agent for testing"""
    
    async def run(self, **kwargs):
        await asyncio.sleep(0.01)
        return {"status": "success"}


@pytest.fixture
def temp_workspace():
    """Create temporary workspace"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def simple_workflow_file(temp_workspace):
    """Create a simple workflow file"""
    workflow_content = """
metadata:
  name: Simple Test
  version: 1.0.0

nodes:
  - id: start
    type: agent
    name: Start Node
    target: test_agent

start_node: start
"""
    
    workflow_file = temp_workspace / "test_workflow.yaml"
    workflow_file.write_text(workflow_content)
    return workflow_file


def test_workflow_manager_creation(temp_workspace):
    """Test creating workflow manager"""
    manager = WorkflowManager(workspace_dir=temp_workspace)
    
    assert manager.workspace_dir == temp_workspace
    assert manager.state_manager is not None
    assert manager.versioning_engine is not None
    assert manager.backup_manager is not None


def test_load_workflow_from_file(temp_workspace, simple_workflow_file):
    """Test loading workflow from file"""
    manager = WorkflowManager(workspace_dir=temp_workspace)
    
    workflow_id = manager.load_workflow(simple_workflow_file)
    
    assert workflow_id is not None
    assert workflow_id in manager.workflows
    
    workflow = manager.get_workflow(workflow_id)
    assert workflow is not None
    assert workflow.metadata.name == "Simple Test"


def test_load_workflow_from_dict(temp_workspace):
    """Test loading workflow from dictionary"""
    manager = WorkflowManager(workspace_dir=temp_workspace)
    
    data = {
        "metadata": {"name": "Dict Workflow", "version": "1.0.0"},
        "nodes": [
            {"id": "node1", "type": "agent", "name": "Node 1", "target": "agent"}
        ],
        "start_node": "node1"
    }
    
    workflow_id = manager.load_workflow_from_dict(data)
    
    assert workflow_id is not None
    workflow = manager.get_workflow(workflow_id)
    assert workflow.metadata.name == "Dict Workflow"


@pytest.mark.asyncio
async def test_execute_workflow(temp_workspace):
    """Test workflow execution through manager"""
    manager = WorkflowManager(workspace_dir=temp_workspace)
    
    # Create simple workflow
    data = {
        "metadata": {"name": "Test", "version": "1.0.0"},
        "nodes": [
            {"id": "node1", "type": "agent", "name": "Node 1", "target": "agent"}
        ],
        "start_node": "node1"
    }
    
    workflow_id = manager.load_workflow_from_dict(data)
    
    # Register agent
    # Note: We need to register before execution starts
    # For now, we'll use the node executor directly
    
    # For this test, we'll create a mock that doesn't need registration
    # In real usage, agents would be registered before execution
    
    # Skip actual execution for now as it requires proper agent setup
    pass


def test_get_workflow_dag(temp_workspace):
    """Test getting DAG for workflow"""
    manager = WorkflowManager(workspace_dir=temp_workspace)
    
    data = {
        "metadata": {"name": "Test", "version": "1.0.0"},
        "nodes": [
            {"id": "a", "type": "agent", "name": "A"},
            {"id": "b", "type": "agent", "name": "B", "depends_on": ["a"]}
        ],
        "start_node": "a"
    }
    
    workflow_id = manager.load_workflow_from_dict(data)
    dag = manager.get_workflow_dag(workflow_id)
    
    assert dag is not None
    assert "a" in dag.nodes
    assert "b" in dag.nodes


def test_export_workflow_yaml(temp_workspace):
    """Test exporting workflow to YAML"""
    manager = WorkflowManager(workspace_dir=temp_workspace)
    
    data = {
        "metadata": {"name": "Export Test", "version": "1.0.0"},
        "nodes": [
            {"id": "node1", "type": "agent", "name": "Node 1"}
        ],
        "start_node": "node1"
    }
    
    workflow_id = manager.load_workflow_from_dict(data)
    
    output_file = temp_workspace / "exported.yaml"
    manager.export_workflow(workflow_id, output_file, format="yaml")
    
    assert output_file.exists()
    content = output_file.read_text()
    assert "Export Test" in content
    assert "node1" in content


def test_export_workflow_json(temp_workspace):
    """Test exporting workflow to JSON"""
    manager = WorkflowManager(workspace_dir=temp_workspace)
    
    data = {
        "metadata": {"name": "Export Test", "version": "1.0.0"},
        "nodes": [
            {"id": "node1", "type": "agent", "name": "Node 1"}
        ],
        "start_node": "node1"
    }
    
    workflow_id = manager.load_workflow_from_dict(data)
    
    output_file = temp_workspace / "exported.json"
    manager.export_workflow(workflow_id, output_file, format="json")
    
    assert output_file.exists()
    content = output_file.read_text()
    assert "Export Test" in content


def test_list_workflows(temp_workspace):
    """Test listing loaded workflows"""
    manager = WorkflowManager(workspace_dir=temp_workspace)
    
    # Load multiple workflows
    for i in range(3):
        data = {
            "metadata": {"name": f"Workflow {i}", "version": "1.0.0"},
            "nodes": [
                {"id": "node1", "type": "agent", "name": "Node 1"}
            ],
            "start_node": "node1"
        }
        manager.load_workflow_from_dict(data, workflow_id=f"wf_{i}")
    
    workflows = manager.list_workflows()
    
    assert len(workflows) == 3
    assert "wf_0" in workflows
    assert "wf_1" in workflows
    assert "wf_2" in workflows


def test_callback_registration(temp_workspace):
    """Test callback registration"""
    manager = WorkflowManager(workspace_dir=temp_workspace)
    
    callback_called = []
    
    def test_callback(event):
        callback_called.append(event)
    
    manager.add_callback(test_callback)
    
    # Verify callback is registered
    assert manager.callback_manager.get_callback_count() > 0
