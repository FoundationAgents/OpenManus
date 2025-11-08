"""Example of using the Workflow Manager"""
import asyncio
from pathlib import Path

from app.workflows import (
    WorkflowManager,
    LoggingCallback,
    MetricsCallback,
    EventType,
)


class SimpleAgent:
    """Example agent for demonstration"""
    
    def __init__(self, name):
        self.name = name
    
    async def run(self, **kwargs):
        """Execute agent task"""
        print(f"[{self.name}] Running with params: {kwargs}")
        await asyncio.sleep(0.1)  # Simulate work
        return {
            "agent": self.name,
            "status": "success",
            "result": f"Processed by {self.name}"
        }


class SimpleTool:
    """Example tool for demonstration"""
    
    def __init__(self, name):
        self.name = name
    
    async def __call__(self, **kwargs):
        """Execute tool"""
        print(f"[{self.name}] Tool executing with params: {kwargs}")
        await asyncio.sleep(0.05)
        return {
            "tool": self.name,
            "status": "success",
            "data": kwargs
        }


async def run_simple_workflow():
    """Run a simple sequential workflow"""
    print("=" * 60)
    print("Running Simple Sequential Workflow")
    print("=" * 60)
    
    # Create workflow manager
    manager = WorkflowManager()
    
    # Add callbacks
    logging_callback = LoggingCallback(verbose=True)
    metrics_callback = MetricsCallback()
    
    manager.add_callback(logging_callback)
    manager.add_callback(metrics_callback)
    
    # Load workflow
    workflow_file = Path(__file__).parent / "simple_workflow.yaml"
    workflow_id = manager.load_workflow(workflow_file)
    
    print(f"\nLoaded workflow: {workflow_id}")
    
    # Get workflow definition
    workflow = manager.get_workflow(workflow_id)
    print(f"Workflow: {workflow.metadata.name} v{workflow.metadata.version}")
    print(f"Nodes: {len(workflow.nodes)}")
    
    # Visualize DAG
    dag = manager.get_workflow_dag(workflow_id)
    print("\n" + dag.visualize())
    
    # Create and start execution task
    exec_task = asyncio.create_task(
        manager.execute_workflow(workflow_id)
    )
    
    # Wait a moment then register agents
    await asyncio.sleep(0.01)
    
    # Register agents for the workflow
    # Note: In real usage, you'd register these before execution
    agent1 = SimpleAgent("Agent1")
    agent2 = SimpleAgent("Agent2")
    agent3 = SimpleAgent("Agent3")
    
    # For this example, we need to access the executor
    # In production, register before calling execute_workflow
    
    # Wait for completion
    try:
        state = await exec_task
        
        print("\n" + "=" * 60)
        print("Execution Complete!")
        print("=" * 60)
        print(f"Status: {state.status}")
        print(f"Duration: {state.end_time - state.start_time:.2f}s")
        
        print("\nNode Results:")
        for node_id, result in state.node_results.items():
            print(f"  {node_id}: {result.status.value}")
            if result.output:
                print(f"    Output: {result.output}")
        
        print("\nMetrics:")
        metrics = metrics_callback.get_metrics()
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()


async def run_complex_workflow():
    """Run the complex example workflow"""
    print("\n" + "=" * 60)
    print("Running Complex Data Processing Pipeline")
    print("=" * 60)
    
    # Create workflow manager
    manager = WorkflowManager()
    
    # Add logging callback
    logging_callback = LoggingCallback(verbose=True)
    manager.add_callback(logging_callback)
    
    # Load workflow
    workflow_file = Path(__file__).parent / "example_workflow.yaml"
    
    try:
        workflow_id = manager.load_workflow(workflow_file)
        print(f"\nLoaded workflow: {workflow_id}")
        
        # Get workflow info
        workflow = manager.get_workflow(workflow_id)
        print(f"Workflow: {workflow.metadata.name}")
        print(f"Description: {workflow.metadata.description}")
        print(f"Nodes: {len(workflow.nodes)}")
        print(f"Tags: {', '.join(workflow.metadata.tags)}")
        
        # Visualize DAG
        dag = manager.get_workflow_dag(workflow_id)
        print("\n" + dag.visualize())
        
        # Show execution levels
        levels = dag.get_execution_order()
        print("\nExecution Levels (parallel execution within levels):")
        for i, level in enumerate(levels):
            print(f"  Level {i}: {', '.join(level)}")
        
        print("\nNote: This workflow requires registered agents, tools, and services.")
        print("Register them before execution using:")
        print("  manager.register_agent(workflow_id, 'agent_name', agent)")
        print("  manager.register_tool(workflow_id, 'tool_name', tool)")
        print("  manager.register_service(workflow_id, 'service_name', service)")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


async def demonstrate_state_management():
    """Demonstrate state management features"""
    print("\n" + "=" * 60)
    print("Demonstrating State Management")
    print("=" * 60)
    
    manager = WorkflowManager()
    
    # Load a workflow
    workflow_file = Path(__file__).parent / "simple_workflow.yaml"
    workflow_id = manager.load_workflow(workflow_file, workflow_id="demo_state")
    
    print(f"\nWorkflow ID: {workflow_id}")
    
    # List versions
    versions = manager.list_versions(workflow_id)
    print(f"\nVersions: {len(versions)}")
    for version_num, timestamp, message in versions:
        print(f"  v{version_num}: {message}")
    
    # Export workflow
    export_path = Path("exported_workflow.yaml")
    manager.export_workflow(workflow_id, export_path, format="yaml")
    print(f"\nExported to: {export_path}")
    
    # Cleanup
    if export_path.exists():
        export_path.unlink()
    
    print("\nState management features:")
    print("  - Automatic checkpointing during execution")
    print("  - Version control of workflow definitions")
    print("  - Backup and restore capabilities")
    print("  - Resume after interruption")


async def demonstrate_callbacks():
    """Demonstrate callback system"""
    print("\n" + "=" * 60)
    print("Demonstrating Callback System")
    print("=" * 60)
    
    manager = WorkflowManager()
    
    # Custom callback
    event_log = []
    
    def custom_callback(event):
        event_log.append({
            'type': event.event_type.value,
            'node': event.node_id,
            'timestamp': event.timestamp
        })
        print(f"Event: {event.event_type.value}" + 
              (f" - {event.node_id}" if event.node_id else ""))
    
    # Register callback
    manager.add_callback(custom_callback)
    
    # Register for specific events only
    def node_complete_callback(event):
        if event.node_id:
            print(f"✓ Node {event.node_id} completed")
    
    manager.add_callback(node_complete_callback, EventType.NODE_COMPLETE)
    
    print("\nCallbacks registered:")
    print("  - Custom callback for all events")
    print("  - Specific callback for NODE_COMPLETE events")
    
    print(f"\nTotal callbacks: {manager.callback_manager.get_callback_count()}")


def main():
    """Main entry point"""
    print("Workflow Manager Examples")
    print("=" * 60)
    
    # Run examples
    asyncio.run(demonstrate_state_management())
    asyncio.run(demonstrate_callbacks())
    
    # Uncomment to run workflow execution examples
    # Note: These require proper agent registration
    # asyncio.run(run_simple_workflow())
    # asyncio.run(run_complex_workflow())
    
    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
