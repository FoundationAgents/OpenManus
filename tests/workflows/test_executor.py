"""Tests for workflow executor"""
import asyncio
import pytest

from app.workflows.callbacks import CallbackManager, EventType, LoggingCallback
from app.workflows.executor import NodeExecutor, WorkflowExecutor
from app.workflows.models import (
    Condition,
    LoopConfig,
    NodeStatus,
    NodeType,
    RetryPolicy,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowNode,
)


class MockAgent:
    """Mock agent for testing"""
    
    def __init__(self, result="success"):
        self.result = result
        self.call_count = 0
    
    async def run(self, **kwargs):
        self.call_count += 1
        await asyncio.sleep(0.01)  # Simulate work
        return {"status": self.result, "kwargs": kwargs}


class MockTool:
    """Mock tool for testing"""
    
    def __init__(self, result="success"):
        self.result = result
        self.call_count = 0
    
    async def __call__(self, **kwargs):
        self.call_count += 1
        await asyncio.sleep(0.01)
        return {"status": self.result, "kwargs": kwargs}


@pytest.mark.asyncio
async def test_simple_workflow_execution():
    """Test execution of simple linear workflow"""
    nodes = [
        WorkflowNode(id="start", type=NodeType.AGENT, name="Start", target="agent1"),
        WorkflowNode(id="end", type=NodeType.AGENT, name="End", target="agent2", depends_on=["start"])
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="start"
    )
    
    callback_manager = CallbackManager()
    logging_callback = LoggingCallback(verbose=False)
    callback_manager.register(logging_callback)
    
    executor = WorkflowExecutor(definition, callback_manager)
    
    # Register mock agents
    agent1 = MockAgent("success")
    agent2 = MockAgent("success")
    executor.get_node_executor().register_agent("agent1", agent1)
    executor.get_node_executor().register_agent("agent2", agent2)
    
    # Execute
    state = await executor.execute("test_workflow")
    
    # Verify
    assert state.status == "completed"
    assert len(state.node_results) == 2
    assert state.node_results["start"].status == NodeStatus.COMPLETED
    assert state.node_results["end"].status == NodeStatus.COMPLETED
    assert agent1.call_count == 1
    assert agent2.call_count == 1


@pytest.mark.asyncio
async def test_parallel_execution():
    """Test parallel execution of independent nodes"""
    nodes = [
        WorkflowNode(id="start", type=NodeType.AGENT, name="Start", target="agent"),
        WorkflowNode(id="parallel1", type=NodeType.AGENT, name="P1", target="agent", depends_on=["start"]),
        WorkflowNode(id="parallel2", type=NodeType.AGENT, name="P2", target="agent", depends_on=["start"]),
        WorkflowNode(id="end", type=NodeType.AGENT, name="End", target="agent", depends_on=["parallel1", "parallel2"])
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="start"
    )
    
    executor = WorkflowExecutor(definition)
    agent = MockAgent()
    executor.get_node_executor().register_agent("agent", agent)
    
    state = await executor.execute("test_workflow")
    
    assert state.status == "completed"
    assert len(state.node_results) == 4
    assert agent.call_count == 4


@pytest.mark.asyncio
async def test_retry_on_failure():
    """Test retry logic on failure"""
    
    class FailingAgent:
        def __init__(self, fail_count=2):
            self.fail_count = fail_count
            self.call_count = 0
        
        async def run(self, **kwargs):
            self.call_count += 1
            if self.call_count <= self.fail_count:
                raise Exception("Simulated failure")
            return {"status": "success"}
    
    nodes = [
        WorkflowNode(
            id="retry_node",
            type=NodeType.AGENT,
            name="Retry Node",
            target="failing_agent",
            retry_policy=RetryPolicy(
                max_attempts=3,
                initial_delay=0.01,
                backoff_factor=1.0
            )
        )
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="retry_node"
    )
    
    logging_callback = LoggingCallback(verbose=False)
    callback_manager = CallbackManager()
    callback_manager.register(logging_callback)
    
    executor = WorkflowExecutor(definition, callback_manager)
    failing_agent = FailingAgent(fail_count=2)
    executor.get_node_executor().register_agent("failing_agent", failing_agent)
    
    state = await executor.execute("test_workflow")
    
    # Should succeed after 3 attempts
    assert state.status == "completed"
    assert state.node_results["retry_node"].status == NodeStatus.COMPLETED
    assert state.node_results["retry_node"].attempts == 3
    assert failing_agent.call_count == 3
    
    # Check retry events
    retry_events = logging_callback.get_events(EventType.NODE_RETRY)
    assert len(retry_events) == 2  # Failed twice before success


@pytest.mark.asyncio
async def test_conditional_execution():
    """Test conditional node execution"""
    nodes = [
        WorkflowNode(
            id="check",
            type=NodeType.AGENT,
            name="Check",
            target="agent"
        ),
        WorkflowNode(
            id="conditional",
            type=NodeType.AGENT,
            name="Conditional",
            target="agent",
            depends_on=["check"],
            condition=Condition(expression="False")  # Always false
        )
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="check"
    )
    
    executor = WorkflowExecutor(definition)
    agent = MockAgent()
    executor.get_node_executor().register_agent("agent", agent)
    
    state = await executor.execute("test_workflow")
    
    assert state.status == "completed"
    assert state.node_results["check"].status == NodeStatus.COMPLETED
    assert state.node_results["conditional"].status == NodeStatus.SKIPPED


@pytest.mark.asyncio
async def test_loop_execution():
    """Test loop execution"""
    nodes = [
        WorkflowNode(
            id="loop_node",
            type=NodeType.AGENT,
            name="Loop Node",
            target="agent",
            loop=LoopConfig(
                type="foreach",
                items="items",
                max_iterations=10
            )
        )
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="loop_node",
        variables={"items": [1, 2, 3]}
    )
    
    executor = WorkflowExecutor(definition)
    agent = MockAgent()
    executor.get_node_executor().register_agent("agent", agent)
    
    state = await executor.execute("test_workflow")
    
    assert state.status == "completed"
    assert agent.call_count == 3  # One call per item
    
    # Result should be a list
    result = state.node_results["loop_node"].output
    assert isinstance(result, list)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_timeout():
    """Test node timeout"""
    
    class SlowAgent:
        async def run(self, **kwargs):
            await asyncio.sleep(1.0)  # Sleep longer than timeout
            return {"status": "success"}
    
    nodes = [
        WorkflowNode(
            id="slow",
            type=NodeType.AGENT,
            name="Slow",
            target="slow_agent",
            timeout=0.1  # Short timeout
        )
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="slow"
    )
    
    executor = WorkflowExecutor(definition)
    executor.get_node_executor().register_agent("slow_agent", SlowAgent())
    
    state = await executor.execute("test_workflow")
    
    assert state.status == "failed"
    assert state.node_results["slow"].status == NodeStatus.FAILED


@pytest.mark.asyncio
async def test_workflow_pause_resume():
    """Test pausing and resuming workflow"""
    
    class PauseTestAgent:
        def __init__(self):
            self.call_count = 0
        
        async def run(self, **kwargs):
            self.call_count += 1
            await asyncio.sleep(0.1)
            return {"status": "success"}
    
    nodes = [
        WorkflowNode(id="node1", type=NodeType.AGENT, name="N1", target="agent"),
        WorkflowNode(id="node2", type=NodeType.AGENT, name="N2", target="agent", depends_on=["node1"]),
        WorkflowNode(id="node3", type=NodeType.AGENT, name="N3", target="agent", depends_on=["node2"])
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="node1"
    )
    
    executor = WorkflowExecutor(definition)
    agent = PauseTestAgent()
    executor.get_node_executor().register_agent("agent", agent)
    
    # Start execution
    exec_task = asyncio.create_task(executor.execute("test_workflow"))
    
    # Pause after short delay
    await asyncio.sleep(0.05)
    executor.pause()
    
    # Wait a bit while paused
    await asyncio.sleep(0.1)
    
    # Resume
    executor.resume()
    
    # Wait for completion
    state = await exec_task
    
    # Should still complete successfully
    assert state.status == "completed"


@pytest.mark.asyncio
async def test_workflow_cancel():
    """Test cancelling workflow"""
    
    class LongRunningAgent:
        async def run(self, **kwargs):
            await asyncio.sleep(10.0)
            return {"status": "success"}
    
    nodes = [
        WorkflowNode(id="long", type=NodeType.AGENT, name="Long", target="agent")
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="long"
    )
    
    executor = WorkflowExecutor(definition)
    executor.get_node_executor().register_agent("agent", LongRunningAgent())
    
    # Start execution
    exec_task = asyncio.create_task(executor.execute("test_workflow"))
    
    # Cancel immediately
    await asyncio.sleep(0.01)
    executor.cancel()
    
    # Wait for task
    state = await exec_task
    
    assert state.status == "cancelled"


@pytest.mark.asyncio
async def test_context_variable_substitution():
    """Test context variable substitution in params"""
    
    class ParamTestAgent:
        async def run(self, **kwargs):
            return {"received_params": kwargs}
    
    nodes = [
        WorkflowNode(
            id="test",
            type=NodeType.AGENT,
            name="Test",
            target="agent",
            params={"value": "$test_var"}
        )
    ]
    
    definition = WorkflowDefinition(
        metadata=WorkflowMetadata(name="Test"),
        nodes=nodes,
        start_node="test",
        variables={"test_var": "substituted_value"}
    )
    
    executor = WorkflowExecutor(definition)
    executor.get_node_executor().register_agent("agent", ParamTestAgent())
    
    state = await executor.execute("test_workflow")
    
    result = state.node_results["test"].output
    assert result["received_params"]["value"] == "substituted_value"
