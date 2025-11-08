"""Main workflow manager integrating all components"""
import asyncio
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from app.workflows.callbacks import CallbackManager, LoggingCallback, MetricsCallback
from app.workflows.dag import WorkflowDAG
from app.workflows.executor import WorkflowExecutor
from app.workflows.models import WorkflowDefinition, WorkflowExecutionState
from app.workflows.parser import WorkflowParser
from app.workflows.state import StateManager, VersioningEngine, BackupManager


class WorkflowManager:
    """Main workflow manager for loading, executing, and managing workflows"""
    
    def __init__(
        self,
        workspace_dir: Optional[Path] = None,
        enable_auto_checkpoint: bool = True,
        checkpoint_interval: int = 60
    ):
        self.workspace_dir = workspace_dir or Path("workspace/workflows")
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize managers
        self.state_manager = StateManager(self.workspace_dir / "checkpoints")
        self.versioning_engine = VersioningEngine(self.workspace_dir / "versions")
        self.backup_manager = BackupManager(self.workspace_dir / "backups")
        self.callback_manager = CallbackManager()
        
        # Auto-checkpoint configuration
        self.enable_auto_checkpoint = enable_auto_checkpoint
        self.checkpoint_interval = checkpoint_interval
        
        # Active executors
        self.active_executors: Dict[str, WorkflowExecutor] = {}
        
        # Loaded workflows
        self.workflows: Dict[str, WorkflowDefinition] = {}
    
    def load_workflow(
        self,
        file_path: Path,
        workflow_id: Optional[str] = None,
        save_version: bool = True
    ) -> str:
        """Load a workflow from file"""
        definition = WorkflowParser.parse_file(file_path)
        
        # Generate workflow ID if not provided
        if not workflow_id:
            workflow_id = f"{definition.metadata.name}_{uuid.uuid4().hex[:8]}"
        
        # Validate DAG
        dag = WorkflowDAG(definition)
        
        # Store workflow
        self.workflows[workflow_id] = definition
        
        # Save version
        if save_version:
            self.versioning_engine.save_version(
                workflow_id,
                definition,
                message=f"Loaded from {file_path}"
            )
        
        return workflow_id
    
    def load_workflow_from_dict(
        self,
        data: Dict[str, Any],
        workflow_id: Optional[str] = None
    ) -> str:
        """Load workflow from dictionary"""
        definition = WorkflowParser.parse_dict(data)
        
        if not workflow_id:
            workflow_id = f"{definition.metadata.name}_{uuid.uuid4().hex[:8]}"
        
        # Validate DAG
        dag = WorkflowDAG(definition)
        
        self.workflows[workflow_id] = definition
        
        return workflow_id
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get loaded workflow definition"""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self) -> Dict[str, WorkflowDefinition]:
        """List all loaded workflows"""
        return self.workflows.copy()
    
    async def execute_workflow(
        self,
        workflow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
        resume: bool = False
    ) -> WorkflowExecutionState:
        """Execute a workflow"""
        # Get workflow definition
        definition = self.workflows.get(workflow_id)
        if not definition:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # Check for existing state if resuming
        resume_state = None
        if resume:
            resume_state = self.state_manager.load_state(workflow_id)
            if not resume_state:
                raise ValueError(f"No saved state found for workflow {workflow_id}")
        
        # Create executor
        executor = WorkflowExecutor(definition, self.callback_manager)
        self.active_executors[workflow_id] = executor
        
        # Setup auto-checkpoint if enabled
        checkpoint_task = None
        if self.enable_auto_checkpoint and not resume:
            checkpoint_task = asyncio.create_task(
                self._auto_checkpoint_loop(workflow_id, executor)
            )
        
        try:
            # Execute workflow
            state = await executor.execute(
                workflow_id,
                initial_context,
                resume_state
            )
            
            # Save final state
            self.state_manager.save_state(state, create_checkpoint=True)
            
            return state
            
        finally:
            # Cleanup
            if checkpoint_task:
                checkpoint_task.cancel()
                try:
                    await checkpoint_task
                except asyncio.CancelledError:
                    pass
            
            if workflow_id in self.active_executors:
                del self.active_executors[workflow_id]
    
    async def _auto_checkpoint_loop(
        self,
        workflow_id: str,
        executor: WorkflowExecutor
    ):
        """Automatically checkpoint workflow state at intervals"""
        while True:
            await asyncio.sleep(self.checkpoint_interval)
            
            if executor.state:
                self.state_manager.save_state(
                    executor.state,
                    create_checkpoint=True
                )
    
    def pause_workflow(self, workflow_id: str):
        """Pause an active workflow"""
        executor = self.active_executors.get(workflow_id)
        if executor:
            executor.pause()
    
    def resume_workflow(self, workflow_id: str):
        """Resume a paused workflow"""
        executor = self.active_executors.get(workflow_id)
        if executor:
            executor.resume()
    
    def cancel_workflow(self, workflow_id: str):
        """Cancel an active workflow"""
        executor = self.active_executors.get(workflow_id)
        if executor:
            executor.cancel()
    
    def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowExecutionState]:
        """Get current execution state of a workflow"""
        # Check active executor first
        executor = self.active_executors.get(workflow_id)
        if executor and executor.state:
            return executor.state
        
        # Otherwise load from disk
        return self.state_manager.load_state(workflow_id)
    
    def get_workflow_dag(self, workflow_id: str) -> Optional[WorkflowDAG]:
        """Get DAG for a workflow"""
        definition = self.workflows.get(workflow_id)
        if not definition:
            return None
        return WorkflowDAG(definition)
    
    def export_workflow(
        self,
        workflow_id: str,
        output_path: Path,
        format: str = "yaml"
    ):
        """Export workflow definition to file"""
        definition = self.workflows.get(workflow_id)
        if not definition:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if format == "yaml":
            content = WorkflowParser.to_yaml(definition)
        elif format == "json":
            content = WorkflowParser.to_json(definition)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def create_backup(
        self,
        workflow_id: str,
        name: Optional[str] = None
    ) -> Path:
        """Create a backup of workflow state"""
        state = self.get_workflow_state(workflow_id)
        if not state:
            raise ValueError(f"No state found for workflow {workflow_id}")
        
        return self.backup_manager.create_backup(workflow_id, state, name)
    
    def restore_backup(
        self,
        backup_file: Path
    ) -> WorkflowExecutionState:
        """Restore workflow state from backup"""
        state = self.backup_manager.restore_backup(backup_file)
        
        # Save restored state
        self.state_manager.save_state(state, create_checkpoint=False)
        
        return state
    
    def list_checkpoints(self, workflow_id: str) -> list:
        """List checkpoints for a workflow"""
        return self.state_manager.list_checkpoints(workflow_id)
    
    def list_versions(self, workflow_id: str) -> list:
        """List versions of a workflow"""
        return self.versioning_engine.list_versions(workflow_id)
    
    def load_version(
        self,
        workflow_id: str,
        version_num: Optional[int] = None
    ) -> Optional[WorkflowDefinition]:
        """Load a specific version of a workflow"""
        return self.versioning_engine.load_version(workflow_id, version_num)
    
    def register_agent(self, workflow_id: str, agent_name: str, agent: Any):
        """Register an agent for workflow execution"""
        executor = self.active_executors.get(workflow_id)
        if executor:
            executor.get_node_executor().register_agent(agent_name, agent)
    
    def register_tool(self, workflow_id: str, tool_name: str, tool: Any):
        """Register a tool for workflow execution"""
        executor = self.active_executors.get(workflow_id)
        if executor:
            executor.get_node_executor().register_tool(tool_name, tool)
    
    def register_service(self, workflow_id: str, service_name: str, service: Any):
        """Register a service for workflow execution"""
        executor = self.active_executors.get(workflow_id)
        if executor:
            executor.get_node_executor().register_service(service_name, service)
    
    def add_callback(self, callback, event_type=None):
        """Register a callback for workflow events"""
        self.callback_manager.register(callback, event_type)
    
    def remove_callback(self, callback, event_type=None):
        """Unregister a callback"""
        self.callback_manager.unregister(callback, event_type)
    
    def get_metrics(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get execution metrics for a workflow"""
        state = self.get_workflow_state(workflow_id)
        if not state:
            return None
        
        metrics = {
            'total_nodes': len(state.definition.nodes),
            'completed_nodes': sum(
                1 for r in state.node_results.values()
                if r.status.value == "completed"
            ),
            'failed_nodes': sum(
                1 for r in state.node_results.values()
                if r.status.value == "failed"
            ),
            'skipped_nodes': sum(
                1 for r in state.node_results.values()
                if r.status.value == "skipped"
            ),
            'pending_nodes': len(state.pending_nodes),
            'running_nodes': len(state.current_nodes),
            'status': state.status,
            'start_time': state.start_time,
            'end_time': state.end_time
        }
        
        if state.start_time and state.end_time:
            metrics['duration'] = state.end_time - state.start_time
        
        return metrics


# Singleton instance
_workflow_manager: Optional[WorkflowManager] = None


def get_workflow_manager() -> WorkflowManager:
    """Get the global workflow manager instance"""
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = WorkflowManager()
    return _workflow_manager
