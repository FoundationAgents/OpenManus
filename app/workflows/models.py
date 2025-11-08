"""Workflow models and definitions"""
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class NodeType(str, Enum):
    """Type of workflow node"""
    AGENT = "agent"
    TOOL = "tool"
    SERVICE = "service"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    SEQUENCE = "sequence"


class NodeStatus(str, Enum):
    """Status of a workflow node"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class RetryPolicy(BaseModel):
    """Retry configuration for a node"""
    max_attempts: int = Field(default=3, ge=1, description="Maximum retry attempts")
    backoff_factor: float = Field(default=2.0, ge=1.0, description="Exponential backoff factor")
    initial_delay: float = Field(default=1.0, ge=0, description="Initial delay in seconds")
    max_delay: float = Field(default=60.0, ge=0, description="Maximum delay in seconds")
    retry_on_errors: Optional[List[str]] = Field(
        default=None, 
        description="List of error types to retry on (None = retry all)"
    )


class Condition(BaseModel):
    """Conditional execution specification"""
    expression: str = Field(..., description="Python expression to evaluate")
    context_vars: List[str] = Field(
        default_factory=list,
        description="Variables from context to use in expression"
    )


class LoopConfig(BaseModel):
    """Loop configuration"""
    type: str = Field(..., description="Loop type: 'foreach' or 'while'")
    items: Optional[str] = Field(None, description="For foreach: context variable containing items")
    condition: Optional[str] = Field(None, description="For while: condition expression")
    max_iterations: int = Field(default=100, ge=1, description="Maximum loop iterations")
    item_var: str = Field(default="item", description="Variable name for current item")


class WorkflowNode(BaseModel):
    """Definition of a workflow node"""
    id: str = Field(..., description="Unique node identifier")
    type: NodeType = Field(..., description="Type of node")
    name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Node description")
    
    # Execution configuration
    target: Optional[str] = Field(None, description="Agent/Tool/Service identifier")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for execution")
    
    # Control flow
    depends_on: List[str] = Field(default_factory=list, description="List of node IDs this depends on")
    condition: Optional[Condition] = Field(None, description="Conditional execution")
    loop: Optional[LoopConfig] = Field(None, description="Loop configuration")
    
    # Error handling
    retry_policy: Optional[RetryPolicy] = Field(None, description="Retry configuration")
    on_failure: Optional[str] = Field(None, description="Action on failure: 'continue', 'stop', or node_id")
    
    # Timeout
    timeout: Optional[float] = Field(None, description="Execution timeout in seconds")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Node ID cannot be empty")
        return v.strip()


class WorkflowMetadata(BaseModel):
    """Workflow metadata"""
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    version: str = Field(default="1.0.0", description="Workflow version")
    author: Optional[str] = Field(None, description="Workflow author")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class WorkflowDefinition(BaseModel):
    """Complete workflow definition"""
    metadata: WorkflowMetadata = Field(..., description="Workflow metadata")
    nodes: List[WorkflowNode] = Field(..., description="List of workflow nodes")
    start_node: str = Field(..., description="ID of the starting node")
    end_nodes: List[str] = Field(default_factory=list, description="IDs of terminal nodes")
    global_timeout: Optional[float] = Field(None, description="Global workflow timeout in seconds")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Initial workflow variables")
    
    @field_validator('nodes')
    @classmethod
    def validate_nodes(cls, v: List[WorkflowNode]) -> List[WorkflowNode]:
        if not v:
            raise ValueError("Workflow must have at least one node")
        node_ids = [n.id for n in v]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Duplicate node IDs found")
        return v


class NodeExecutionResult(BaseModel):
    """Result of a node execution"""
    node_id: str
    status: NodeStatus
    output: Any = None
    error: Optional[str] = None
    start_time: float
    end_time: Optional[float] = None
    attempts: int = 1
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutionState(BaseModel):
    """Current state of workflow execution"""
    workflow_id: str
    definition: WorkflowDefinition
    status: str = Field(default="pending", description="Overall workflow status")
    
    # Execution tracking
    node_results: Dict[str, NodeExecutionResult] = Field(default_factory=dict)
    current_nodes: List[str] = Field(default_factory=list, description="Currently executing nodes")
    pending_nodes: List[str] = Field(default_factory=list, description="Nodes waiting to execute")
    
    # Context and variables
    context: Dict[str, Any] = Field(default_factory=dict, description="Workflow execution context")
    
    # Timing
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    # State persistence
    checkpoint_count: int = Field(default=0, description="Number of checkpoints created")
    last_checkpoint_time: Optional[float] = None

    class Config:
        arbitrary_types_allowed = True
