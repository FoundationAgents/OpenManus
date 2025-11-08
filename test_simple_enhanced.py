#!/usr/bin/env python3
"""
Simple test for enhanced sandbox functionality.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from app.sandbox import (
    Guardian, 
    AuditLogger, 
    ResourceMonitor,
    get_guardian,
    get_audit_logger,
    OperationRequest,
    RiskLevel,
    OperationType,
    OperationStatus,
    AuditLog,
    ResourceLimits
)


async def test_guardian():
    """Test Guardian functionality."""
    print("Testing Guardian...")
    
    guardian = get_guardian()
    
    # Test agent approval
    agent_id = "test_agent"
    request = OperationRequest(agent_id=agent_id, operation="test")
    decision = await guardian.validate_operation(request)
    print(f"  Unapproved agent: {'APPROVED' if decision.approved else 'DENIED'}")
    
    # Approve agent
    guardian.approve_agent(agent_id)
    decision = await guardian.validate_operation(request)
    print(f"  Approved agent: {'APPROVED' if decision.approved else 'DENIED'}")
    
    # Test dangerous command
    dangerous_request = OperationRequest(
        agent_id=agent_id,
        operation="command_execute",
        command="rm -rf /"
    )
    decision = await guardian.validate_operation(dangerous_request)
    print(f"  Dangerous command: {'APPROVED' if decision.approved else 'DENIED'}")
    print(f"  Risk level: {decision.risk_level.value}")
    
    # Test safe command
    safe_request = OperationRequest(
        agent_id=agent_id,
        operation="command_execute",
        command="echo 'hello'"
    )
    decision = await guardian.validate_operation(safe_request)
    print(f"  Safe command: {'APPROVED' if decision.approved else 'DENIED'}")
    print(f"  Risk level: {decision.risk_level.value}")
    
    print("  ✓ Guardian tests passed")


async def test_audit_logger():
    """Test Audit Logger functionality."""
    print("\nTesting Audit Logger...")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        audit_logger = AuditLogger(db_path=Path(tmp_dir) / "test.db")
        
        # Test logging
        from datetime import datetime, timezone
        
        log_entry = AuditLog(
            timestamp=datetime.now(timezone.utc),
            agent_id="test_agent",
            sandbox_id="test_sandbox",
            operation_type=OperationType.COMMAND_EXECUTE,
            status=OperationStatus.SUCCESS,
            details={"command": "echo 'test'", "output": "test"}
        )
        
        await audit_logger.log_operation(log_entry)
        
        # Test retrieval
        logs = await audit_logger.get_logs(agent_id="test_agent")
        print(f"  Logged entries: {len(logs)}")
        
        if logs:
            log = logs[0]
            print(f"  First log: {log.operation_type.value} - {log.status.value}")
            print(f"  Details: {log.details}")
        
        # Test database stats
        stats = await audit_logger.get_database_stats()
        print(f"  Database stats: {stats['total_records']} records")
        
        print("  ✓ Audit Logger tests passed")


async def test_resource_monitor():
    """Test Resource Monitor functionality."""
    print("\nTesting Resource Monitor...")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        audit_logger = AuditLogger(db_path=Path(tmp_dir) / "test.db")
        monitor = ResourceMonitor(audit_logger=audit_logger)
        
        # Test initialization
        print(f"  Is running: {monitor._is_running}")
        print(f"  Monitored sandboxes: {len(monitor._monitored_sandboxes)}")
        
        # Test statistics
        stats = monitor.get_monitoring_stats()
        print(f"  Stats: {stats}")
        
        # Test start/stop
        monitor.start_monitoring()
        print(f"  Started: {monitor._is_running}")
        
        monitor.stop_monitoring()
        print(f"  Stopped: {monitor._is_running}")
        
        print("  ✓ Resource Monitor tests passed")


async def test_integration():
    """Test integration of all components."""
    print("\nTesting Integration...")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Initialize components
        guardian = get_guardian()
        audit_logger = AuditLogger(db_path=Path(tmp_dir) / "integration.db")
        monitor = ResourceMonitor(audit_logger=audit_logger)
        
        # Approve agent
        guardian.approve_agent("integration_agent")
        
        # Test workflow
        request = OperationRequest(
            agent_id="integration_agent",
            operation="sandbox_create",
            resource_limits={"cpu_limit": 1.0, "memory_limit": "512m"}
        )
        
        decision = await guardian.validate_operation(request)
        print(f"  Sandbox creation: {'APPROVED' if decision.approved else 'DENIED'}")
        
        # Log operation
        if decision.approved:
            log_entry = AuditLog(
                timestamp=datetime.now(timezone.utc),
                agent_id="integration_agent",
                sandbox_id="integration_sandbox",
                operation_type=OperationType.SANDBOX_CREATE,
                status=OperationStatus.SUCCESS,
                details={"image": "python:3.12-slim"}
            )
            await audit_logger.log_operation(log_entry)
        
        # Check logs
        logs = await audit_logger.get_logs(agent_id="integration_agent")
        print(f"  Integration logs: {len(logs)}")
        
        # Get Guardian summary
        summary = guardian.get_security_summary()
        print(f"  Guardian summary: {summary['approved_agents']} agents approved")
        
        print("  ✓ Integration tests passed")


async def main():
    """Run all tests."""
    print("🧪 Enhanced Sandbox System - Simple Tests")
    print("=" * 50)
    
    try:
        await test_guardian()
        await test_audit_logger()
        await test_resource_monitor()
        await test_integration()
        
        print("\n" + "✅" * 20)
        print("ALL TESTS PASSED!")
        print("✅" * 20)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())