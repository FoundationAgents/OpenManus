"""Workflow state management and persistence"""
import json
import pickle
import time
from pathlib import Path
from typing import Optional

from app.workflows.models import WorkflowExecutionState, WorkflowDefinition


class StateManager:
    """Manages workflow execution state persistence"""
    
    def __init__(self, checkpoint_dir: Optional[Path] = None):
        self.checkpoint_dir = checkpoint_dir or Path("workspace/workflows/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save_state(
        self,
        state: WorkflowExecutionState,
        create_checkpoint: bool = True
    ) -> Path:
        """Save workflow execution state"""
        workflow_dir = self.checkpoint_dir / state.workflow_id
        workflow_dir.mkdir(parents=True, exist_ok=True)
        
        # Save current state
        state_file = workflow_dir / "current_state.json"
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state.model_dump(), f, indent=2, default=str)
        
        # Create checkpoint if requested
        if create_checkpoint:
            checkpoint_num = state.checkpoint_count + 1
            checkpoint_file = workflow_dir / f"checkpoint_{checkpoint_num:04d}.json"
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(state.model_dump(), f, indent=2, default=str)
            
            state.checkpoint_count = checkpoint_num
            state.last_checkpoint_time = time.time()
        
        return state_file
    
    def load_state(self, workflow_id: str) -> Optional[WorkflowExecutionState]:
        """Load current workflow execution state"""
        state_file = self.checkpoint_dir / workflow_id / "current_state.json"
        
        if not state_file.exists():
            return None
        
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return WorkflowExecutionState(**data)
    
    def load_checkpoint(
        self,
        workflow_id: str,
        checkpoint_num: Optional[int] = None
    ) -> Optional[WorkflowExecutionState]:
        """Load a specific checkpoint (or latest if num not specified)"""
        workflow_dir = self.checkpoint_dir / workflow_id
        
        if not workflow_dir.exists():
            return None
        
        # Find checkpoint file
        if checkpoint_num is None:
            # Get latest checkpoint
            checkpoints = sorted(workflow_dir.glob("checkpoint_*.json"))
            if not checkpoints:
                return None
            checkpoint_file = checkpoints[-1]
        else:
            checkpoint_file = workflow_dir / f"checkpoint_{checkpoint_num:04d}.json"
            if not checkpoint_file.exists():
                return None
        
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return WorkflowExecutionState(**data)
    
    def list_checkpoints(self, workflow_id: str) -> list[tuple[int, float]]:
        """List available checkpoints with their timestamps"""
        workflow_dir = self.checkpoint_dir / workflow_id
        
        if not workflow_dir.exists():
            return []
        
        checkpoints = []
        for checkpoint_file in sorted(workflow_dir.glob("checkpoint_*.json")):
            # Extract checkpoint number from filename
            num_str = checkpoint_file.stem.split('_')[1]
            checkpoint_num = int(num_str)
            timestamp = checkpoint_file.stat().st_mtime
            checkpoints.append((checkpoint_num, timestamp))
        
        return checkpoints
    
    def delete_workflow_state(self, workflow_id: str):
        """Delete all state and checkpoints for a workflow"""
        workflow_dir = self.checkpoint_dir / workflow_id
        
        if workflow_dir.exists():
            import shutil
            shutil.rmtree(workflow_dir)
    
    def export_state(
        self,
        workflow_id: str,
        output_path: Path,
        include_definition: bool = True
    ):
        """Export workflow state to a portable format"""
        state = self.load_state(workflow_id)
        if not state:
            raise ValueError(f"No state found for workflow {workflow_id}")
        
        export_data = {
            'state': state.model_dump(),
            'checkpoints': self.list_checkpoints(workflow_id)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
    
    def import_state(self, import_path: Path) -> WorkflowExecutionState:
        """Import workflow state from exported file"""
        with open(import_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        state = WorkflowExecutionState(**export_data['state'])
        
        # Save imported state
        self.save_state(state, create_checkpoint=False)
        
        return state


class VersioningEngine:
    """Simple versioning engine for workflow definitions"""
    
    def __init__(self, versions_dir: Optional[Path] = None):
        self.versions_dir = versions_dir or Path("workspace/workflows/versions")
        self.versions_dir.mkdir(parents=True, exist_ok=True)
    
    def save_version(
        self,
        workflow_id: str,
        definition: WorkflowDefinition,
        message: Optional[str] = None
    ) -> int:
        """Save a new version of workflow definition"""
        workflow_dir = self.versions_dir / workflow_id
        workflow_dir.mkdir(parents=True, exist_ok=True)
        
        # Get next version number
        versions = sorted(workflow_dir.glob("v*.json"))
        version_num = len(versions) + 1
        
        version_file = workflow_dir / f"v{version_num:04d}.json"
        
        version_data = {
            'version': version_num,
            'timestamp': time.time(),
            'message': message,
            'definition': definition.model_dump()
        }
        
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2, default=str)
        
        return version_num
    
    def load_version(
        self,
        workflow_id: str,
        version_num: Optional[int] = None
    ) -> Optional[WorkflowDefinition]:
        """Load a specific version (or latest if not specified)"""
        workflow_dir = self.versions_dir / workflow_id
        
        if not workflow_dir.exists():
            return None
        
        if version_num is None:
            # Get latest version
            versions = sorted(workflow_dir.glob("v*.json"))
            if not versions:
                return None
            version_file = versions[-1]
        else:
            version_file = workflow_dir / f"v{version_num:04d}.json"
            if not version_file.exists():
                return None
        
        with open(version_file, 'r', encoding='utf-8') as f:
            version_data = json.load(f)
        
        return WorkflowDefinition(**version_data['definition'])
    
    def list_versions(self, workflow_id: str) -> list[tuple[int, float, Optional[str]]]:
        """List available versions with metadata"""
        workflow_dir = self.versions_dir / workflow_id
        
        if not workflow_dir.exists():
            return []
        
        versions = []
        for version_file in sorted(workflow_dir.glob("v*.json")):
            with open(version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            versions.append((
                data['version'],
                data['timestamp'],
                data.get('message')
            ))
        
        return versions


class BackupManager:
    """Manages workflow backups"""
    
    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or Path("workspace/workflows/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(
        self,
        workflow_id: str,
        state: WorkflowExecutionState,
        name: Optional[str] = None
    ) -> Path:
        """Create a backup of workflow state"""
        timestamp = int(time.time())
        backup_name = name or f"backup_{timestamp}"
        
        backup_file = self.backup_dir / f"{workflow_id}_{backup_name}.backup"
        
        backup_data = {
            'workflow_id': workflow_id,
            'timestamp': timestamp,
            'name': backup_name,
            'state': state.model_dump()
        }
        
        with open(backup_file, 'wb') as f:
            pickle.dump(backup_data, f)
        
        return backup_file
    
    def restore_backup(self, backup_file: Path) -> WorkflowExecutionState:
        """Restore workflow state from backup"""
        with open(backup_file, 'rb') as f:
            backup_data = pickle.load(f)
        
        return WorkflowExecutionState(**backup_data['state'])
    
    def list_backups(self, workflow_id: Optional[str] = None) -> list[tuple[str, Path, float]]:
        """List available backups"""
        pattern = f"{workflow_id}_*.backup" if workflow_id else "*.backup"
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob(pattern)):
            try:
                with open(backup_file, 'rb') as f:
                    backup_data = pickle.load(f)
                backups.append((
                    backup_data['name'],
                    backup_file,
                    backup_data['timestamp']
                ))
            except Exception:
                continue
        
        return backups
