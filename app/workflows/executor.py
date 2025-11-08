"""Workflow execution engine"""
import asyncio
import time
from typing import Any, Dict, Optional, Set

from app.workflows.callbacks import CallbackManager, EventType, WorkflowEvent
from app.workflows.dag import WorkflowDAG
from app.workflows.models import (
    NodeExecutionResult,
    NodeStatus,
    NodeType,
    WorkflowDefinition,
    WorkflowExecutionState,
    WorkflowNode,
)


class NodeExecutor:
    """Executes individual workflow nodes"""
    
    def __init__(self):
        self.agent_registry: Dict[str, Any] = {}
        self.tool_registry: Dict[str, Any] = {}
        self.service_registry: Dict[str, Any] = {}
    
    def register_agent(self, name: str, agent: Any):
        """Register an agent for workflow execution"""
        self.agent_registry[name] = agent
    
    def register_tool(self, name: str, tool: Any):
        """Register a tool for workflow execution"""
        self.tool_registry[name] = tool
    
    def register_service(self, name: str, service: Any):
        """Register a service for workflow execution"""
        self.service_registry[name] = service
    
    async def execute_node(
        self,
        node: WorkflowNode,
        context: Dict[str, Any]
    ) -> Any:
        """Execute a single node"""
        if node.type == NodeType.AGENT:
            return await self._execute_agent_node(node, context)
        elif node.type == NodeType.TOOL:
            return await self._execute_tool_node(node, context)
        elif node.type == NodeType.SERVICE:
            return await self._execute_service_node(node, context)
        elif node.type == NodeType.SEQUENCE:
            return await self._execute_sequence_node(node, context)
        elif node.type == NodeType.PARALLEL:
            return await self._execute_parallel_node(node, context)
        else:
            raise ValueError(f"Unsupported node type: {node.type}")
    
    async def _execute_agent_node(
        self,
        node: WorkflowNode,
        context: Dict[str, Any]
    ) -> Any:
        """Execute agent node"""
        if not node.target:
            raise ValueError(f"Agent node {node.id} missing target")
        
        agent = self.agent_registry.get(node.target)
        if not agent:
            raise ValueError(f"Agent '{node.target}' not registered")
        
        # Prepare parameters with context substitution
        params = self._substitute_context(node.params, context)
        
        # Execute agent (assume it has an async run method)
        if hasattr(agent, 'run'):
            if asyncio.iscoroutinefunction(agent.run):
                result = await agent.run(**params)
            else:
                result = agent.run(**params)
        else:
            raise ValueError(f"Agent {node.target} doesn't have a 'run' method")
        
        return result
    
    async def _execute_tool_node(
        self,
        node: WorkflowNode,
        context: Dict[str, Any]
    ) -> Any:
        """Execute tool node"""
        if not node.target:
            raise ValueError(f"Tool node {node.id} missing target")
        
        tool = self.tool_registry.get(node.target)
        if not tool:
            raise ValueError(f"Tool '{node.target}' not registered")
        
        params = self._substitute_context(node.params, context)
        
        # Execute tool
        if callable(tool):
            if asyncio.iscoroutinefunction(tool):
                result = await tool(**params)
            else:
                result = tool(**params)
        else:
            raise ValueError(f"Tool {node.target} is not callable")
        
        return result
    
    async def _execute_service_node(
        self,
        node: WorkflowNode,
        context: Dict[str, Any]
    ) -> Any:
        """Execute external service node"""
        if not node.target:
            raise ValueError(f"Service node {node.id} missing target")
        
        service = self.service_registry.get(node.target)
        if not service:
            raise ValueError(f"Service '{node.target}' not registered")
        
        params = self._substitute_context(node.params, context)
        
        # Execute service call
        if hasattr(service, 'call'):
            if asyncio.iscoroutinefunction(service.call):
                result = await service.call(**params)
            else:
                result = service.call(**params)
        else:
            raise ValueError(f"Service {node.target} doesn't have a 'call' method")
        
        return result
    
    async def _execute_sequence_node(
        self,
        node: WorkflowNode,
        context: Dict[str, Any]
    ) -> Any:
        """Execute nodes in sequence (placeholder for nested workflows)"""
        # For now, just return success
        return {"status": "completed", "type": "sequence"}
    
    async def _execute_parallel_node(
        self,
        node: WorkflowNode,
        context: Dict[str, Any]
    ) -> Any:
        """Execute nodes in parallel (placeholder for nested workflows)"""
        # For now, just return success
        return {"status": "completed", "type": "parallel"}
    
    def _substitute_context(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Substitute context variables in parameters"""
        result = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                # Context variable reference
                var_name = value[1:]
                result[key] = context.get(var_name, value)
            elif isinstance(value, dict):
                result[key] = self._substitute_context(value, context)
            elif isinstance(value, list):
                result[key] = [
                    self._substitute_context({"item": item}, context).get("item", item)
                    if isinstance(item, (dict, str)) and isinstance(item, str) and item.startswith("$")
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result


class WorkflowExecutor:
    """Main workflow execution engine"""
    
    def __init__(
        self,
        definition: WorkflowDefinition,
        callback_manager: Optional[CallbackManager] = None
    ):
        self.definition = definition
        self.dag = WorkflowDAG(definition)
        self.callback_manager = callback_manager or CallbackManager()
        self.node_executor = NodeExecutor()
        
        self.state: Optional[WorkflowExecutionState] = None
        self.is_paused = False
        self.is_cancelled = False
    
    def get_node_executor(self) -> NodeExecutor:
        """Get the node executor for registering agents/tools/services"""
        return self.node_executor
    
    async def execute(
        self,
        workflow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
        resume_state: Optional[WorkflowExecutionState] = None
    ) -> WorkflowExecutionState:
        """Execute the workflow"""
        # Initialize or resume state
        if resume_state:
            self.state = resume_state
            self.state.status = "running"
        else:
            self.state = WorkflowExecutionState(
                workflow_id=workflow_id,
                definition=self.definition,
                status="running",
                context=initial_context or self.definition.variables.copy(),
                start_time=time.time(),
                pending_nodes=[self.definition.start_node]
            )
        
        # Emit workflow start event
        self.callback_manager.emit(WorkflowEvent(
            event_type=EventType.WORKFLOW_START,
            workflow_id=workflow_id,
            timestamp=time.time(),
            data={"definition": self.definition.metadata.name}
        ))
        
        try:
            # Main execution loop
            while not self._is_complete() and not self.is_cancelled:
                if self.is_paused:
                    await asyncio.sleep(0.1)
                    continue
                
                # Get ready nodes
                completed = set(
                    nid for nid, result in self.state.node_results.items()
                    if result.status == NodeStatus.COMPLETED
                )
                running = set(self.state.current_nodes)
                ready = self.dag.get_ready_nodes(completed, running)
                
                if not ready and not running:
                    # No more nodes to execute
                    break
                
                if ready:
                    # Execute ready nodes in parallel
                    tasks = [
                        self._execute_node_with_retry(node_id)
                        for node_id in ready
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)
                else:
                    # Wait for running nodes
                    await asyncio.sleep(0.1)
            
            # Finalize state
            if self.is_cancelled:
                self.state.status = "cancelled"
            else:
                self.state.status = "completed" if self._is_successful() else "failed"
            
            self.state.end_time = time.time()
            
            # Emit completion event
            event_type = (
                EventType.WORKFLOW_COMPLETE if self.state.status == "completed"
                else EventType.WORKFLOW_FAILED
            )
            self.callback_manager.emit(WorkflowEvent(
                event_type=event_type,
                workflow_id=workflow_id,
                timestamp=time.time(),
                data={
                    "duration": self.state.end_time - self.state.start_time,
                    "status": self.state.status
                }
            ))
            
        except Exception as e:
            self.state.status = "failed"
            self.state.end_time = time.time()
            
            self.callback_manager.emit(WorkflowEvent(
                event_type=EventType.WORKFLOW_FAILED,
                workflow_id=workflow_id,
                timestamp=time.time(),
                error=e
            ))
            raise
        
        return self.state
    
    async def _execute_node_with_retry(self, node_id: str):
        """Execute a node with retry logic"""
        node = self.dag.get_node(node_id)
        retry_policy = node.retry_policy
        max_attempts = retry_policy.max_attempts if retry_policy else 1
        
        # Mark as running
        self.state.current_nodes.append(node_id)
        if node_id in self.state.pending_nodes:
            self.state.pending_nodes.remove(node_id)
        
        start_time = time.time()
        
        # Emit node start event
        self.callback_manager.emit(WorkflowEvent(
            event_type=EventType.NODE_START,
            workflow_id=self.state.workflow_id,
            node_id=node_id,
            timestamp=start_time
        ))
        
        for attempt in range(1, max_attempts + 1):
            try:
                # Check condition
                if node.condition and not self._evaluate_condition(node.condition):
                    # Skip node
                    result = NodeExecutionResult(
                        node_id=node_id,
                        status=NodeStatus.SKIPPED,
                        start_time=start_time,
                        end_time=time.time(),
                        attempts=attempt
                    )
                    self.state.node_results[node_id] = result
                    
                    self.callback_manager.emit(WorkflowEvent(
                        event_type=EventType.NODE_SKIPPED,
                        workflow_id=self.state.workflow_id,
                        node_id=node_id,
                        timestamp=time.time()
                    ))
                    break
                
                # Execute with timeout
                if node.timeout:
                    output = await asyncio.wait_for(
                        self._execute_node_with_loop(node),
                        timeout=node.timeout
                    )
                else:
                    output = await self._execute_node_with_loop(node)
                
                # Success
                end_time = time.time()
                result = NodeExecutionResult(
                    node_id=node_id,
                    status=NodeStatus.COMPLETED,
                    output=output,
                    start_time=start_time,
                    end_time=end_time,
                    attempts=attempt
                )
                self.state.node_results[node_id] = result
                
                # Update context with node output
                self.state.context[f"node_{node_id}_output"] = output
                
                self.callback_manager.emit(WorkflowEvent(
                    event_type=EventType.NODE_COMPLETE,
                    workflow_id=self.state.workflow_id,
                    node_id=node_id,
                    timestamp=end_time,
                    data={"duration": end_time - start_time, "output": output}
                ))
                break
                
            except Exception as e:
                if attempt < max_attempts:
                    # Retry with backoff
                    delay = self._calculate_backoff_delay(attempt, retry_policy)
                    
                    self.callback_manager.emit(WorkflowEvent(
                        event_type=EventType.NODE_RETRY,
                        workflow_id=self.state.workflow_id,
                        node_id=node_id,
                        timestamp=time.time(),
                        data={"attempt": attempt, "delay": delay},
                        error=e
                    ))
                    
                    await asyncio.sleep(delay)
                else:
                    # Final failure
                    result = NodeExecutionResult(
                        node_id=node_id,
                        status=NodeStatus.FAILED,
                        error=str(e),
                        start_time=start_time,
                        end_time=time.time(),
                        attempts=attempt
                    )
                    self.state.node_results[node_id] = result
                    
                    self.callback_manager.emit(WorkflowEvent(
                        event_type=EventType.NODE_FAILED,
                        workflow_id=self.state.workflow_id,
                        node_id=node_id,
                        timestamp=time.time(),
                        error=e
                    ))
                    
                    # Handle failure action
                    if node.on_failure == "stop":
                        self.is_cancelled = True
        
        # Remove from running
        if node_id in self.state.current_nodes:
            self.state.current_nodes.remove(node_id)
    
    async def _execute_node_with_loop(self, node: WorkflowNode) -> Any:
        """Execute node with loop support"""
        if not node.loop:
            # No loop, execute normally
            return await self.node_executor.execute_node(node, self.state.context)
        
        loop_config = node.loop
        results = []
        
        if loop_config.type == "foreach":
            # For-each loop
            items_var = loop_config.items
            items = self.state.context.get(items_var, [])
            
            for i, item in enumerate(items):
                if i >= loop_config.max_iterations:
                    break
                
                # Set loop variable
                loop_context = self.state.context.copy()
                loop_context[loop_config.item_var] = item
                loop_context['loop_index'] = i
                
                result = await self.node_executor.execute_node(node, loop_context)
                results.append(result)
        
        elif loop_config.type == "while":
            # While loop
            iteration = 0
            while iteration < loop_config.max_iterations:
                # Evaluate condition
                if not self._evaluate_expression(loop_config.condition):
                    break
                
                loop_context = self.state.context.copy()
                loop_context['loop_index'] = iteration
                
                result = await self.node_executor.execute_node(node, loop_context)
                results.append(result)
                iteration += 1
        
        return results
    
    def _evaluate_condition(self, condition) -> bool:
        """Evaluate a condition expression"""
        try:
            # Create safe evaluation context
            eval_context = {
                k: v for k, v in self.state.context.items()
                if k in condition.context_vars or not condition.context_vars
            }
            return bool(eval(condition.expression, {"__builtins__": {}}, eval_context))
        except Exception:
            return False
    
    def _evaluate_expression(self, expression: str) -> bool:
        """Evaluate a generic expression"""
        try:
            return bool(eval(expression, {"__builtins__": {}}, self.state.context))
        except Exception:
            return False
    
    def _calculate_backoff_delay(self, attempt: int, retry_policy) -> float:
        """Calculate exponential backoff delay"""
        if not retry_policy:
            return 1.0
        
        delay = retry_policy.initial_delay * (retry_policy.backoff_factor ** (attempt - 1))
        return min(delay, retry_policy.max_delay)
    
    def _is_complete(self) -> bool:
        """Check if workflow execution is complete"""
        if not self.state:
            return False
        
        # If end nodes specified, check if all are completed
        if self.definition.end_nodes:
            return all(
                end_node in self.state.node_results and
                self.state.node_results[end_node].status in [NodeStatus.COMPLETED, NodeStatus.SKIPPED]
                for end_node in self.definition.end_nodes
            )
        
        # Otherwise, check if all nodes are done
        all_nodes = set(node.id for node in self.definition.nodes)
        completed_or_skipped = set(
            nid for nid, result in self.state.node_results.items()
            if result.status in [NodeStatus.COMPLETED, NodeStatus.SKIPPED, NodeStatus.FAILED]
        )
        
        return all_nodes == completed_or_skipped
    
    def _is_successful(self) -> bool:
        """Check if workflow completed successfully"""
        if not self.state:
            return False
        
        # Check for any failed nodes
        for result in self.state.node_results.values():
            if result.status == NodeStatus.FAILED:
                return False
        
        return True
    
    def pause(self):
        """Pause workflow execution"""
        self.is_paused = True
        self.callback_manager.emit(WorkflowEvent(
            event_type=EventType.WORKFLOW_PAUSED,
            workflow_id=self.state.workflow_id,
            timestamp=time.time()
        ))
    
    def resume(self):
        """Resume workflow execution"""
        self.is_paused = False
        self.callback_manager.emit(WorkflowEvent(
            event_type=EventType.WORKFLOW_RESUMED,
            workflow_id=self.state.workflow_id,
            timestamp=time.time()
        ))
    
    def cancel(self):
        """Cancel workflow execution"""
        self.is_cancelled = True
