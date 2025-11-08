#!/usr/bin/env python3
"""
Enhanced Sandbox Demo

This script demonstrates the enhanced sandbox functionality including:
- Per-agent sandbox isolation
- Guardian validation and security rules
- Resource monitoring and killswitch
- Audit logging
- CLI utilities
"""

import asyncio
import time
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.sandbox import (
    SandboxManager, 
    Guardian, 
    ResourceMonitor, 
    AuditLogger,
    ResourceLimits,
    get_guardian,
    get_audit_logger
)
from app.config import SandboxSettings
from app.sandbox.cli import SandboxCLI


async def demo_basic_functionality():
    """Demonstrate basic enhanced sandbox functionality."""
    print("=" * 60)
    print("ENHANCED SANDBOX DEMO - Basic Functionality")
    print("=" * 60)
    
    # Initialize components
    guardian = get_guardian()
    audit_logger = get_audit_logger()
    monitor = ResourceMonitor(audit_logger)
    
    # Create manager
    manager = SandboxManager(
        max_sandboxes=10,
        guardian=guardian,
        monitor=monitor,
        audit_logger=audit_logger
    )
    
    try:
        # Demo 1: Create sandbox for different agents
        print("\n1. Creating sandboxes for different agents...")
        
        agents = ["developer", "tester", "security_analyst"]
        sandbox_ids = []
        
        for agent_id in agents:
            try:
                # Auto-approve agent
                guardian.approve_agent(agent_id)
                
                # Create sandbox with agent-specific limits
                limits = ResourceLimits(
                    cpu_percent=60.0 if agent_id == "developer" else 40.0,
                    memory_mb=1024 if agent_id == "developer" else 512,
                    timeout_seconds=300
                )
                
                sandbox_id = await manager.create_sandbox(
                    config=SandboxSettings(image="python:3.12-slim"),
                    agent_id=agent_id,
                    agent_version="1.0.0",
                    resource_limits=limits,
                    tags={"environment": "demo", "team": agent_id}
                )
                
                sandbox_ids.append(sandbox_id)
                print(f"  ✓ Created sandbox {sandbox_id} for agent {agent_id}")
                
            except Exception as e:
                print(f"  ✗ Failed to create sandbox for {agent_id}: {e}")
        
        # Demo 2: Show manager statistics
        print("\n2. Manager statistics:")
        stats = manager.get_stats()
        print(f"  Total sandboxes: {stats['total_sandboxes']}")
        print(f"  Total agents: {stats['total_agents']}")
        print(f"  Agent sandbox counts: {stats['agent_sandbox_counts']}")
        
        # Demo 3: Guardian security validation
        print("\n3. Guardian security validation...")
        
        # Test dangerous command (should be blocked)
        dangerous_commands = [
            ("rm -rf /", "developer"),
            ("shutdown -h now", "tester"),
            ("sudo su", "security_analyst")
        ]
        
        for cmd, agent_id in dangerous_commands:
            try:
                sandbox = manager._sandboxes.get(sandbox_ids[0])  # Use first sandbox
                if sandbox:
                    await sandbox.run_command(cmd)
                    print(f"  ✗ Command '{cmd}' was allowed (should be blocked!)")
            except Exception as e:
                print(f"  ✓ Command '{cmd}' blocked: {str(e)[:50]}...")
        
        # Demo 4: Safe command execution
        print("\n4. Safe command execution...")
        safe_commands = [
            "python -c 'print(\"Hello from sandbox!\")'",
            "ls -la",
            "echo 'Testing safe operations'"
        ]
        
        for cmd in safe_commands:
            try:
                # Mock execution for demo
                print(f"  ✓ Safe command '{cmd}' would be allowed")
            except Exception as e:
                print(f"  ✗ Safe command failed: {e}")
        
        # Demo 5: Resource monitoring
        print("\n5. Resource monitoring...")
        
        for i, sandbox_id in enumerate(sandbox_ids[:2]):  # Monitor first 2
            metrics = await manager.get_sandbox_metrics(sandbox_id)
            if metrics:
                print(f"  Sandbox {sandbox_id}:")
                print(f"    Uptime: {metrics.get('uptime_seconds', 0):.1f}s")
                print(f"    Alerts: {metrics.get('alerts_count', 0)}")
                if metrics.get('current_usage'):
                    usage = metrics['current_usage']
                    print(f"    CPU: {usage.get('cpu_percent', 0):.1f}%")
                    print(f"    Memory: {usage.get('memory_mb', 0)} MB")
        
        # Demo 6: Agent metrics aggregation
        print("\n6. Agent metrics aggregation...")
        
        for agent_id in agents[:2]:  # Show first 2 agents
            agent_metrics = await manager.get_agent_metrics(agent_id)
            print(f"  Agent {agent_id}:")
            print(f"    Total sandboxes: {agent_metrics['total_sandboxes']}")
            if 'aggregated_metrics' in agent_metrics:
                agg = agent_metrics['aggregated_metrics']
                print(f"    Average CPU: {agg.get('avg_cpu_percent', 0):.1f}%")
                print(f"    Average Memory: {agg.get('avg_memory_mb', 0):.1f} MB")
        
        # Demo 7: Audit logging
        print("\n7. Audit logging...")
        
        # Query recent logs
        logs = await audit_logger.get_logs(limit=5)
        print(f"  Recent audit logs ({len(logs)} entries):")
        for log in logs:
            timestamp = log.timestamp.strftime('%H:%M:%S')
            print(f"    {timestamp} [{log.status.value}] {log.operation_type.value} - Agent: {log.agent_id}")
        
        # Demo 8: Agent summaries
        print("\n8. Agent activity summaries...")
        
        for agent_id in agents[:2]:
            summary = await audit_logger.get_agent_summary(agent_id, days=1)
            print(f"  Agent {agent_id} (last 24h):")
            print(f"    Total operations: {summary['total_operations']}")
            print(f"    Error count: {summary['error_count']}")
            if summary['operations_by_status']:
                print(f"    Status breakdown: {summary['operations_by_status']}")
        
        # Demo 9: Guardian security status
        print("\n9. Guardian security status...")
        
        guardian_summary = guardian.get_security_summary()
        print(f"  Total security rules: {guardian_summary['total_rules']}")
        print(f"  Enabled rules: {guardian_summary['enabled_rules']}")
        print(f"  Approved agents: {guardian_summary['approved_agents']}")
        print(f"  Risk level distribution: {guardian_summary['risk_levels']}")
        
        # Demo 10: Cleanup
        print("\n10. Cleanup...")
        
        for sandbox_id in sandbox_ids:
            await manager.delete_sandbox(sandbox_id)
            print(f"  ✓ Deleted sandbox {sandbox_id}")
        
        print("\n" + "=" * 60)
        print("BASIC FUNCTIONALITY DEMO COMPLETED")
        print("=" * 60)
        
    finally:
        await manager.cleanup()


async def demo_cli_utilities():
    """Demonstrate CLI utilities."""
    print("\n" + "=" * 60)
    print("ENHANCED SANDBOX DEMO - CLI Utilities")
    print("=" * 60)
    
    cli = SandboxCLI()
    
    try:
        # Initialize manager
        await cli.init_manager()
        
        # Demo CLI commands
        print("\n1. CLI Agent Management...")
        await cli.approve_agent("cli_demo_agent")
        print("  ✓ Approved agent 'cli_demo_agent'")
        
        print("\n2. CLI Guardian Status...")
        await cli.show_guardian_status()
        
        print("\n3. CLI Volume ACL...")
        await cli.add_volume_acl(
            "/safe/demo",
            "/demo/safe",
            mode="rw",
            allowed_patterns=[".*\\.py$", ".*\\.txt$"],
            blocked_patterns=[".*\\.sh$"]
        )
        print("  ✓ Added volume ACL")
        
        print("\n4. CLI Metrics...")
        await cli.show_metrics()
        
        print("\n5. CLI Audit Logs...")
        await cli.show_audit_logs(limit=3)
        
    except Exception as e:
        print(f"CLI demo error: {e}")


async def demo_security_scenarios():
    """Demonstrate security scenarios."""
    print("\n" + "=" * 60)
    print("ENHANCED SANDBOX DEMO - Security Scenarios")
    print("=" * 60)
    
    guardian = get_guardian()
    audit_logger = get_audit_logger()
    
    # Scenario 1: Unauthorized agent
    print("\n1. Unauthorized agent attempt...")
    from app.sandbox.core.guardian import OperationRequest
    
    request = OperationRequest(
        agent_id="unauthorized_agent",
        operation="sandbox_create",
        resource_limits={"cpu_limit": 1.0, "memory_limit": "512m"}
    )
    
    decision = await guardian.validate_operation(request)
    print(f"  Result: {'APPROVED' if decision.approved else 'DENIED'}")
    print(f"  Reason: {decision.reason}")
    print(f"  Risk Level: {decision.risk_level.value}")
    
    # Scenario 2: Dangerous commands
    print("\n2. Dangerous command validation...")
    
    dangerous_scenarios = [
        ("rm -rf /etc", "System file deletion"),
        ("format /dev/sda1", "Disk formatting"),
        ("nmap -sS 192.168.1.0/24", "Network scanning"),
        ("sudo su -", "Privilege escalation")
    ]
    
    for cmd, description in dangerous_scenarios:
        request = OperationRequest(
            agent_id="authorized_agent",
            operation="command_execute",
            command=cmd
        )
        
        # Approve agent first
        guardian.approve_agent("authorized_agent")
        
        decision = await guardian.validate_operation(request)
        status = "✓ DENIED" if not decision.approved else "✗ ALLOWED"
        print(f"  {status} - {description}: {decision.reason[:60]}...")
    
    # Scenario 3: Resource limit validation
    print("\n3. Resource limit validation...")
    
    resource_scenarios = [
        ({"cpu_limit": 8.0, "memory_limit": "8g"}, "High resource request"),
        ({"timeout": 7200}, "Long timeout request"),
        ({"cpu_limit": 0.1, "memory_limit": "64m"}, "Low resource request")
    ]
    
    for limits, description in resource_scenarios:
        request = OperationRequest(
            agent_id="authorized_agent",
            operation="sandbox_create",
            resource_limits=limits
        )
        
        decision = await guardian.validate_operation(request)
        status = "✓ APPROVED" if decision.approved else "⚠ CONDITIONS"
        print(f"  {status} - {description}: {decision.reason[:60]}...")
        if decision.conditions:
            print(f"    Conditions: {', '.join(decision.conditions)}")


async def demo_monitoring_killswitch():
    """Demonstrate monitoring and killswitch functionality."""
    print("\n" + "=" * 60)
    print("ENHANCED SANDBOX DEMO - Monitoring & Killswitch")
    print("=" * 60)
    
    audit_logger = get_audit_logger()
    monitor = ResourceMonitor(audit_logger)
    
    # Demo monitoring setup
    print("\n1. Resource monitoring setup...")
    monitor.start_monitoring()
    
    print("  ✓ Resource monitoring started")
    print(f"  Monitoring interval: {monitor._monitoring_interval}s")
    
    # Demo killswitch handlers
    print("\n2. Custom killswitch handlers...")
    
    alerts_received = []
    
    def custom_killswitch_handler(sandbox_id, alert):
        alerts_received.append((sandbox_id, alert))
        print(f"  🚨 Killswitch triggered for {sandbox_id}: {alert.message}")
    
    monitor.add_killswitch_handler(custom_killswitch_handler)
    print("  ✓ Custom killswitch handler registered")
    
    # Demo monitoring statistics
    print("\n3. Monitoring statistics...")
    stats = monitor.get_monitoring_stats()
    print(f"  Is running: {stats['is_running']}")
    print(f"  Monitored sandboxes: {stats['monitored_sandboxes']}")
    print(f"  Killswitch handlers: {stats['killswitch_handlers']}")
    
    # Stop monitoring
    monitor.stop_monitoring()
    print("\n  ✓ Resource monitoring stopped")


async def main():
    """Run all demos."""
    print("🚀 Enhanced Sandbox System Demo")
    print("This demo showcases the new sandbox capabilities including:")
    print("- Per-agent sandbox isolation")
    print("- Guardian validation and security rules")
    print("- Resource monitoring and killswitch")
    print("- Comprehensive audit logging")
    print("- CLI management utilities")
    
    try:
        # Run all demos
        await demo_basic_functionality()
        await demo_cli_utilities()
        await demo_security_scenarios()
        await demo_monitoring_killswitch()
        
        print("\n" + "🎉" * 20)
        print("ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("🎉" * 20)
        
        print("\nNext steps:")
        print("1. Try the CLI: python -m app.sandbox.cli --help")
        print("2. Review configuration: config/sandbox_enhanced.toml")
        print("3. Run tests: python -m pytest tests/sandbox/test_enhanced_sandbox.py -v")
        print("4. Check audit logs: workspace/sandbox_audit.db")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())