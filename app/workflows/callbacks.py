"""Callback and event hook system for workflow execution"""
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.workflows.models import NodeExecutionResult, WorkflowExecutionState


class EventType(str, Enum):
    """Types of workflow events"""
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    
    NODE_START = "node_start"
    NODE_COMPLETE = "node_complete"
    NODE_FAILED = "node_failed"
    NODE_RETRY = "node_retry"
    NODE_SKIPPED = "node_skipped"
    
    STATE_CHECKPOINT = "state_checkpoint"


class WorkflowEvent:
    """Represents a workflow event"""
    
    def __init__(
        self,
        event_type: EventType,
        workflow_id: str,
        timestamp: float,
        node_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ):
        self.event_type = event_type
        self.workflow_id = workflow_id
        self.node_id = node_id
        self.timestamp = timestamp
        self.data = data or {}
        self.error = error
    
    def __repr__(self) -> str:
        parts = [f"WorkflowEvent({self.event_type.value}"]
        if self.node_id:
            parts.append(f"node={self.node_id}")
        if self.error:
            parts.append(f"error={self.error}")
        return ", ".join(parts) + ")"


# Type alias for callback functions
CallbackFunction = Callable[[WorkflowEvent], None]


class CallbackManager:
    """Manages workflow event callbacks"""
    
    def __init__(self):
        self._callbacks: Dict[EventType, List[CallbackFunction]] = {
            event_type: [] for event_type in EventType
        }
        self._global_callbacks: List[CallbackFunction] = []
    
    def register(
        self,
        callback: CallbackFunction,
        event_type: Optional[EventType] = None
    ):
        """Register a callback for specific event type or all events"""
        if event_type is None:
            # Global callback for all events
            self._global_callbacks.append(callback)
        else:
            self._callbacks[event_type].append(callback)
    
    def unregister(
        self,
        callback: CallbackFunction,
        event_type: Optional[EventType] = None
    ):
        """Unregister a callback"""
        if event_type is None:
            if callback in self._global_callbacks:
                self._global_callbacks.remove(callback)
        else:
            if callback in self._callbacks[event_type]:
                self._callbacks[event_type].remove(callback)
    
    def emit(self, event: WorkflowEvent):
        """Emit an event to all registered callbacks"""
        # Call event-specific callbacks
        for callback in self._callbacks.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                # Log but don't fail on callback errors
                print(f"Callback error: {e}")
        
        # Call global callbacks
        for callback in self._global_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Global callback error: {e}")
    
    def clear(self, event_type: Optional[EventType] = None):
        """Clear callbacks for specific event type or all"""
        if event_type is None:
            for event_type in EventType:
                self._callbacks[event_type].clear()
            self._global_callbacks.clear()
        else:
            self._callbacks[event_type].clear()
    
    def get_callback_count(self, event_type: Optional[EventType] = None) -> int:
        """Get number of registered callbacks"""
        if event_type is None:
            return sum(len(cbs) for cbs in self._callbacks.values()) + len(self._global_callbacks)
        return len(self._callbacks[event_type])


class LoggingCallback:
    """Simple logging callback for debugging"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.events: List[WorkflowEvent] = []
    
    def __call__(self, event: WorkflowEvent):
        self.events.append(event)
        if self.verbose:
            msg = f"[{event.event_type.value}] workflow={event.workflow_id}"
            if event.node_id:
                msg += f" node={event.node_id}"
            if event.error:
                msg += f" error={event.error}"
            print(msg)
    
    def clear(self):
        """Clear event history"""
        self.events.clear()
    
    def get_events(self, event_type: Optional[EventType] = None) -> List[WorkflowEvent]:
        """Get recorded events, optionally filtered by type"""
        if event_type is None:
            return self.events.copy()
        return [e for e in self.events if e.event_type == event_type]


class MetricsCallback:
    """Callback for collecting execution metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            'total_nodes': 0,
            'completed_nodes': 0,
            'failed_nodes': 0,
            'retried_nodes': 0,
            'skipped_nodes': 0,
            'total_duration': 0.0,
            'node_durations': {},
            'retry_counts': {}
        }
    
    def __call__(self, event: WorkflowEvent):
        if event.event_type == EventType.NODE_START:
            self.metrics['total_nodes'] += 1
        
        elif event.event_type == EventType.NODE_COMPLETE:
            self.metrics['completed_nodes'] += 1
            if event.data.get('duration'):
                self.metrics['node_durations'][event.node_id] = event.data['duration']
        
        elif event.event_type == EventType.NODE_FAILED:
            self.metrics['failed_nodes'] += 1
        
        elif event.event_type == EventType.NODE_RETRY:
            self.metrics['retried_nodes'] += 1
            retry_count = self.metrics['retry_counts'].get(event.node_id, 0)
            self.metrics['retry_counts'][event.node_id] = retry_count + 1
        
        elif event.event_type == EventType.NODE_SKIPPED:
            self.metrics['skipped_nodes'] += 1
        
        elif event.event_type == EventType.WORKFLOW_COMPLETE:
            if event.data.get('duration'):
                self.metrics['total_duration'] = event.data['duration']
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics"""
        return self.metrics.copy()
    
    def reset(self):
        """Reset metrics"""
        self.metrics = {
            'total_nodes': 0,
            'completed_nodes': 0,
            'failed_nodes': 0,
            'retried_nodes': 0,
            'skipped_nodes': 0,
            'total_duration': 0.0,
            'node_durations': {},
            'retry_counts': {}
        }
