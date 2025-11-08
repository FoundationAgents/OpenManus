"""Tests for workflow state management"""
import tempfile
from pathlib import Path

import pytest

from app.workflows.models import (
    NodeExecutionResult,
    NodeStatus,
    WorkflowDefinition,
    WorkflowExecutionState,
    WorkflowMetadata,
    WorkflowNode,
    NodeType,
)
from app.workflows.state import StateManager, VersioningEngine, BackupManager


@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_definition():
    """Create sample workflow definition"""
    return WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test", version="1.0.0"),
        nodes=[
            WorkflowNode(id="node1", type=NodeType.AGENT, name="Node 1")
        ],
        start_node="node1"
    )


@pytest.fixture
def sample_state(sample_definition):
    """Create sample execution state"""
    state = WorkflowExecutionState(
        workflow_id="test_wf",
        definition=sample_definition,
        status="running",
        start_time=1000.0
    )
    
    state.node_results["node1"] = NodeExecutionResult(
        node_id="node1",
        status=NodeStatus.COMPLETED,
        output={"result": "success"},
        start_time=1000.0,
        end_time=1001.0
    )
    
    return state


def test_state_manager_save_load(temp_dir, sample_state):
    """Test saving and loading state"""
    manager = StateManager(checkpoint_dir=temp_dir)
    
    # Save state
    state_file = manager.save_state(sample_state, create_checkpoint=False)
    assert state_file.exists()
    
    # Load state
    loaded_state = manager.load_state("test_wf")
    assert loaded_state is not None
    assert loaded_state.workflow_id == "test_wf"
    assert loaded_state.status == "running"
    assert "node1" in loaded_state.node_results


def test_state_manager_checkpoints(temp_dir, sample_state):
    """Test checkpoint creation"""
    manager = StateManager(checkpoint_dir=temp_dir)
    
    # Save with checkpoint
    manager.save_state(sample_state, create_checkpoint=True)
    
    # List checkpoints
    checkpoints = manager.list_checkpoints("test_wf")
    assert len(checkpoints) > 0
    
    # Load checkpoint
    loaded = manager.load_checkpoint("test_wf")
    assert loaded is not None
    # Checkpoint contains the state at save time, before checkpoint_count was incremented
    assert loaded.workflow_id == "test_wf"


def test_state_manager_multiple_checkpoints(temp_dir, sample_state):
    """Test multiple checkpoints"""
    manager = StateManager(checkpoint_dir=temp_dir)
    
    # Create multiple checkpoints
    for i in range(3):
        sample_state.checkpoint_count = i
        manager.save_state(sample_state, create_checkpoint=True)
    
    checkpoints = manager.list_checkpoints("test_wf")
    assert len(checkpoints) == 3
    
    # Load specific checkpoint
    loaded = manager.load_checkpoint("test_wf", checkpoint_num=2)
    assert loaded is not None


def test_state_manager_delete(temp_dir, sample_state):
    """Test deleting workflow state"""
    manager = StateManager(checkpoint_dir=temp_dir)
    
    manager.save_state(sample_state)
    assert manager.load_state("test_wf") is not None
    
    manager.delete_workflow_state("test_wf")
    assert manager.load_state("test_wf") is None


def test_state_manager_export_import(temp_dir, sample_state):
    """Test exporting and importing state"""
    manager = StateManager(checkpoint_dir=temp_dir)
    
    # Save and export
    manager.save_state(sample_state)
    export_file = temp_dir / "exported_state.json"
    manager.export_state("test_wf", export_file)
    
    assert export_file.exists()
    
    # Delete original and import
    manager.delete_workflow_state("test_wf")
    imported = manager.import_state(export_file)
    
    assert imported.workflow_id == "test_wf"
    assert imported.status == "running"


def test_versioning_engine_save_load(temp_dir, sample_definition):
    """Test versioning workflow definitions"""
    engine = VersioningEngine(versions_dir=temp_dir)
    
    # Save version
    version_num = engine.save_version(
        "test_wf",
        sample_definition,
        message="Initial version"
    )
    
    assert version_num == 1
    
    # Load version
    loaded = engine.load_version("test_wf")
    assert loaded is not None
    assert loaded.metadata.name == "Test"


def test_versioning_engine_multiple_versions(temp_dir, sample_definition):
    """Test multiple versions"""
    engine = VersioningEngine(versions_dir=temp_dir)
    
    # Save multiple versions
    for i in range(3):
        sample_definition.metadata.version = f"1.{i}.0"
        engine.save_version("test_wf", sample_definition, message=f"Version {i}")
    
    versions = engine.list_versions("test_wf")
    assert len(versions) == 3
    
    # Load specific version
    loaded = engine.load_version("test_wf", version_num=2)
    assert loaded.metadata.version == "1.1.0"


def test_backup_manager_create_restore(temp_dir, sample_state):
    """Test creating and restoring backups"""
    manager = BackupManager(backup_dir=temp_dir)
    
    # Create backup
    backup_file = manager.create_backup(
        "test_wf",
        sample_state,
        name="test_backup"
    )
    
    assert backup_file.exists()
    
    # Restore backup
    restored = manager.restore_backup(backup_file)
    assert restored.workflow_id == "test_wf"
    assert restored.status == "running"


def test_backup_manager_list_backups(temp_dir, sample_state):
    """Test listing backups"""
    manager = BackupManager(backup_dir=temp_dir)
    
    # Create multiple backups
    for i in range(3):
        manager.create_backup("test_wf", sample_state, name=f"backup_{i}")
    
    backups = manager.list_backups("test_wf")
    assert len(backups) == 3
    
    # List all backups
    all_backups = manager.list_backups()
    assert len(all_backups) >= 3
