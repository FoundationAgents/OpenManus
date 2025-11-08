"""
CLI utilities for sandbox management.

This module provides command-line interface utilities for managing sandboxes,
including listing, inspecting, terminating sandboxes, and monitoring resources.
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.sandbox.core.manager import SandboxManager
from app.sandbox.core.guardian import get_guardian, VolumeACL, AccessMode
from app.sandbox.core.audit import get_audit_logger, OperationType, OperationStatus
from app.sandbox.core.monitor import ResourceMonitor
from app.config import SandboxSettings
from app.logger import logger


class SandboxCLI:
    """Command-line interface for sandbox management."""

    def __init__(self):
        """Initialize CLI with default components."""
        self.manager: SandboxManager = None
        self.guardian = get_guardian()
        self.audit_logger = get_audit_logger()
        self.monitor = ResourceMonitor(self.audit_logger)

    async def init_manager(self):
        """Initialize sandbox manager."""
        if not self.manager:
            self.manager = SandboxManager(
                guardian=self.guardian,
                monitor=self.monitor,
                audit_logger=self.audit_logger
            )

    async def list_sandboxes(self, agent_id: str = None, detailed: bool = False) -> None:
        """List all sandboxes or sandboxes for a specific agent.

        Args:
            agent_id: Filter by agent ID.
            detailed: Show detailed information.
        """
        await self.init_manager()
        
        if agent_id:
            sandbox_ids = await self.manager.get_agent_sandboxes(agent_id)
            print(f"Sandboxes for agent '{agent_id}':")
        else:
            sandbox_ids = list(self.manager._sandboxes.keys())
            print("All sandboxes:")

        if not sandbox_ids:
            print("  No sandboxes found.")
            return

        for sandbox_id in sandbox_ids:
            sandbox = self.manager._sandboxes.get(sandbox_id)
            if sandbox:
                status = sandbox.get_status()
                
                if detailed:
                    print(f"\n  Sandbox: {sandbox_id}")
                    print(f"    Agent ID: {status['agent_id']}")
                    print(f"    Agent Version: {status['agent_version'] or 'N/A'}")
                    print(f"    Created: {datetime.fromtimestamp(status['created_at'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    print(f"    Container ID: {status['container_id'] or 'N/A'}")
                    print(f"    Image: {status['config']['image']}")
                    print(f"    Memory Limit: {status['config']['memory_limit']}")
                    print(f"    CPU Limit: {status['config']['cpu_limit']}")
                    print(f"    Network: {status['config']['network_enabled']}")
                    
                    # Container status
                    if 'container_status' in status:
                        cs = status['container_status']
                        print(f"    State: {cs.get('state', 'Unknown')}")
                        if cs.get('error'):
                            print(f"    Error: {cs['error']}")
                    
                    # Resource usage
                    metrics = await sandbox.get_metrics()
                    if metrics and metrics.get('current_usage'):
                        usage = metrics['current_usage']
                        print(f"    CPU: {usage['cpu_percent']:.1f}%")
                        print(f"    Memory: {usage['memory_mb']} MB")
                        print(f"    Alerts: {metrics.get('alerts_count', 0)}")
                else:
                    # Simple format
                    created_str = datetime.fromtimestamp(status['created_at'], tz=timezone.utc).strftime('%H:%M:%S')
                    print(f"  {sandbox_id} - Agent: {status['agent_id']} - Created: {created_str}")

    async def inspect_sandbox(self, sandbox_id: str) -> None:
        """Inspect a specific sandbox in detail.

        Args:
            sandbox_id: Sandbox ID to inspect.
        """
        await self.init_manager()
        
        sandbox = self.manager._sandboxes.get(sandbox_id)
        if not sandbox:
            print(f"Sandbox '{sandbox_id}' not found.")
            return

        status = sandbox.get_status()
        metrics = await sandbox.get_metrics()

        print(f"Sandbox Details: {sandbox_id}")
        print("=" * 50)
        
        # Basic info
        print(f"Agent ID: {status['agent_id']}")
        print(f"Agent Version: {status['agent_version'] or 'N/A'}")
        print(f"Created: {datetime.fromtimestamp(status['created_at'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Last Activity: {datetime.fromtimestamp(status['last_activity'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Container ID: {status['container_id'] or 'N/A'}")
        
        # Configuration
        print("\nConfiguration:")
        config = status['config']
        print(f"  Image: {config['image']}")
        print(f"  Work Directory: {config['work_dir']}")
        print(f"  Memory Limit: {config['memory_limit']}")
        print(f"  CPU Limit: {config['cpu_limit']}")
        print(f"  Timeout: {config['timeout']}s")
        print(f"  Network: {config['network_enabled']}")
        
        # Resource limits
        print("\nResource Limits:")
        limits = status['resource_limits']
        print(f"  CPU: {limits['cpu_percent']}%")
        print(f"  Memory: {limits['memory_mb']} MB")
        print(f"  Disk: {limits['disk_mb']} MB")
        print(f"  Timeout: {limits['timeout_seconds']}s")
        
        # Container status
        if 'container_status' in status:
            print("\nContainer Status:")
            cs = status['container_status']
            print(f"  State: {cs.get('state', 'Unknown')}")
            print(f"  Started: {cs.get('started_at', 'N/A')}")
            print(f"  Exit Code: {cs.get('exit_code', 'N/A')}")
            if cs.get('error'):
                print(f"  Error: {cs['error']}")
        
        # Current metrics
        if metrics:
            print("\nCurrent Metrics:")
            print(f"  Uptime: {metrics.get('uptime_seconds', 0):.1f}s")
            print(f"  Alerts: {metrics.get('alerts_count', 0)}")
            
            if metrics.get('current_usage'):
                usage = metrics['current_usage']
                print(f"  CPU Usage: {usage['cpu_percent']:.1f}%")
                print(f"  Memory Usage: {usage['memory_mb']} MB")
                print(f"  Disk Usage: {usage['disk_mb']} MB")
                print(f"  Network Sent: {usage['network_bytes_sent']} bytes")
                print(f"  Network Recv: {usage['network_bytes_recv']} bytes")
        
        # Volume bindings
        if status['volume_bindings']:
            print("\nVolume Bindings:")
            for host_path, container_path in status['volume_bindings'].items():
                print(f"  {host_path} -> {container_path}")
        
        # Tags
        if status['tags']:
            print("\nTags:")
            for key, value in status['tags'].items():
                print(f"  {key}: {value}")

    async def terminate_sandbox(self, sandbox_id: str, force: bool = False) -> None:
        """Terminate a sandbox.

        Args:
            sandbox_id: Sandbox ID to terminate.
            force: Force termination without confirmation.
        """
        await self.init_manager()
        
        sandbox = self.manager._sandboxes.get(sandbox_id)
        if not sandbox:
            print(f"Sandbox '{sandbox_id}' not found.")
            return

        if not force:
            # Show sandbox info and ask for confirmation
            status = sandbox.get_status()
            print(f"Sandbox to terminate: {sandbox_id}")
            print(f"  Agent ID: {status['agent_id']}")
            print(f"  Created: {datetime.fromtimestamp(status['created_at'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            response = input("Are you sure you want to terminate this sandbox? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Termination cancelled.")
                return

        try:
            await self.manager.delete_sandbox(sandbox_id)
            print(f"Sandbox '{sandbox_id}' terminated successfully.")
        except Exception as e:
            print(f"Failed to terminate sandbox '{sandbox_id}': {e}")

    async def kill_agent_sandboxes(self, agent_id: str, force: bool = False) -> None:
        """Kill all sandboxes for an agent.

        Args:
            agent_id: Agent ID.
            force: Force termination without confirmation.
        """
        await self.init_manager()
        
        sandbox_ids = await self.manager.get_agent_sandboxes(agent_id)
        if not sandbox_ids:
            print(f"No sandboxes found for agent '{agent_id}'.")
            return

        if not force:
            print(f"Found {len(sandbox_ids)} sandboxes for agent '{agent_id}':")
            for sandbox_id in sandbox_ids:
                sandbox = self.manager._sandboxes.get(sandbox_id)
                if sandbox:
                    status = sandbox.get_status()
                    created_str = datetime.fromtimestamp(status['created_at'], tz=timezone.utc).strftime('%H:%M:%S')
                    print(f"  {sandbox_id} - Created: {created_str}")
            
            response = input(f"Are you sure you want to kill all {len(sandbox_ids)} sandboxes? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Kill cancelled.")
                return

        try:
            killed_count = await self.manager.kill_agent_sandboxes(agent_id)
            print(f"Successfully killed {killed_count} sandboxes for agent '{agent_id}'.")
        except Exception as e:
            print(f"Failed to kill sandboxes for agent '{agent_id}': {e}")

    async def show_metrics(self, agent_id: str = None) -> None:
        """Show resource metrics.

        Args:
            agent_id: Filter by agent ID.
        """
        await self.init_manager()
        
        if agent_id:
            metrics = await self.manager.get_agent_metrics(agent_id)
            print(f"Metrics for agent '{agent_id}':")
            self._print_agent_metrics(metrics)
        else:
            stats = await self.manager.get_comprehensive_stats()
            
            print("Manager Statistics:")
            print(f"  Total Sandboxes: {stats['total_sandboxes']}")
            print(f"  Active Operations: {stats['active_operations']}")
            print(f"  Total Agents: {stats['total_agents']}")
            print(f"  Max Sandboxes: {stats['max_sandboxes']}")
            
            if 'monitoring' in stats:
                mon = stats['monitoring']
                print(f"\nMonitoring:")
                print(f"  Is Running: {mon['is_running']}")
                print(f"  Monitoring Interval: {mon['monitoring_interval']}s")
                print(f"  Killswitch Handlers: {mon['killswitch_handlers']}")
            
            # Show per-agent metrics
            if 'agent_summaries' in stats:
                print("\nAgent Summaries:")
                for agent_id, summary in stats['agent_summaries'].items():
                    print(f"\n  Agent: {agent_id}")
                    print(f"    Total Operations: {summary['total_operations']}")
                    print(f"    Error Count: {summary['error_count']}")
                    if summary['operations_by_status']:
                        print(f"    Status Breakdown:")
                        for status, count in summary['operations_by_status'].items():
                            print(f"      {status}: {count}")

    def _print_agent_metrics(self, metrics: Dict[str, Any]) -> None:
        """Print agent metrics in a readable format."""
        print(f"  Total Sandboxes: {metrics['total_sandboxes']}")
        
        if 'aggregated_metrics' in metrics:
            agg = metrics['aggregated_metrics']
            print(f"  Active Sandboxes: {agg['active_sandboxes']}")
            print(f"  Average CPU: {agg['avg_cpu_percent']:.1f}%")
            print(f"  Average Memory: {agg['avg_memory_mb']:.1f} MB")
            print(f"  Total Memory: {agg['total_memory_mb']} MB")
        
        if metrics['sandbox_metrics']:
            print("\n  Individual Sandboxes:")
            for sm in metrics['sandbox_metrics']:
                print(f"    {sm['sandbox_id']}:")
                print(f"      Uptime: {sm.get('uptime_seconds', 0):.1f}s")
                print(f"      Alerts: {sm.get('alerts_count', 0)}")
                if sm.get('current_usage'):
                    usage = sm['current_usage']
                    print(f"      CPU: {usage['cpu_percent']:.1f}%")
                    print(f"      Memory: {usage['memory_mb']} MB")

    async def show_audit_logs(
        self,
        agent_id: str = None,
        sandbox_id: str = None,
        operation: str = None,
        limit: int = 50,
        json_output: bool = False
    ) -> None:
        """Show audit logs.

        Args:
            agent_id: Filter by agent ID.
            sandbox_id: Filter by sandbox ID.
            operation: Filter by operation type.
            limit: Maximum number of logs to show.
            json_output: Output in JSON format.
        """
        # Parse operation type
        op_type = None
        if operation:
            try:
                op_type = OperationType(operation)
            except ValueError:
                print(f"Invalid operation type: {operation}")
                print(f"Valid types: {[op.value for op in OperationType]}")
                return

        logs = await self.audit_logger.get_logs(
            agent_id=agent_id,
            sandbox_id=sandbox_id,
            operation_type=op_type,
            limit=limit
        )

        if json_output:
            log_data = []
            for log in logs:
                log_dict = {
                    "timestamp": log.timestamp.isoformat(),
                    "agent_id": log.agent_id,
                    "sandbox_id": log.sandbox_id,
                    "operation_type": log.operation_type.value,
                    "status": log.status.value,
                    "details": log.details,
                    "duration_ms": log.duration_ms,
                    "error_message": log.error_message
                }
                if log.resource_usage:
                    log_dict["resource_usage"] = {
                        "cpu_percent": log.resource_usage.cpu_percent,
                        "memory_mb": log.resource_usage.memory_mb,
                        "disk_mb": log.resource_usage.disk_mb
                    }
                log_data.append(log_dict)
            
            print(json.dumps(log_data, indent=2))
        else:
            print(f"Audit Logs (showing {len(logs)} entries):")
            print("-" * 100)
            
            for log in logs:
                timestamp = log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                status_symbol = {
                    OperationStatus.SUCCESS: "✓",
                    OperationStatus.FAILURE: "✗",
                    OperationStatus.TIMEOUT: "⏰",
                    OperationStatus.DENIED: "🚫",
                    OperationStatus.CANCELLED: "⏹"
                }.get(log.status, "?")
                
                print(f"{timestamp} [{status_symbol}] {log.operation_type.value}")
                print(f"  Agent: {log.agent_id} | Sandbox: {log.sandbox_id}")
                
                if log.details:
                    for key, value in log.details.items():
                        if key not in ['command']:  # Skip long command output
                            print(f"  {key}: {value}")
                
                if log.duration_ms:
                    print(f"  Duration: {log.duration_ms}ms")
                
                if log.error_message:
                    print(f"  Error: {log.error_message}")
                
                print()

    async def approve_agent(self, agent_id: str) -> None:
        """Approve an agent for sandbox operations.

        Args:
            agent_id: Agent ID to approve.
        """
        self.guardian.approve_agent(agent_id)
        print(f"Agent '{agent_id}' approved for sandbox operations.")

    async def revoke_agent(self, agent_id: str) -> None:
        """Revoke approval for an agent.

        Args:
            agent_id: Agent ID to revoke.
        """
        self.guardian.revoke_agent_approval(agent_id)
        print(f"Approval revoked for agent '{agent_id}'.")

    async def add_volume_acl(
        self,
        host_path: str,
        container_path: str,
        mode: str = "rw",
        allowed_patterns: List[str] = None,
        blocked_patterns: List[str] = None
    ) -> None:
        """Add a volume ACL.

        Args:
            host_path: Host path.
            container_path: Container path.
            mode: Access mode (ro/rw).
            allowed_patterns: List of allowed regex patterns.
            blocked_patterns: List of blocked regex patterns.
        """
        access_mode = AccessMode.READ_WRITE if mode == "rw" else AccessMode.READ_ONLY
        
        acl = VolumeACL(
            host_path=host_path,
            container_path=container_path,
            mode=access_mode,
            allowed_patterns=allowed_patterns or [],
            blocked_patterns=blocked_patterns or []
        )
        
        self.guardian.add_volume_acl(acl)
        print(f"Added volume ACL: {host_path} -> {container_path} ({mode})")

    async def show_guardian_status(self) -> None:
        """Show Guardian security status."""
        summary = self.guardian.get_security_summary()
        
        print("Guardian Security Status:")
        print(f"  Total Rules: {summary['total_rules']}")
        print(f"  Enabled Rules: {summary['enabled_rules']}")
        print(f"  Volume ACLs: {summary['volume_acls']}")
        print(f"  Approved Agents: {summary['approved_agents']}")
        
        print("\nRisk Level Distribution:")
        for level, count in summary['risk_levels'].items():
            print(f"  {level.capitalize()}: {count}")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Sandbox Management CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # List command
    list_parser = subparsers.add_parser('list', help='List sandboxes')
    list_parser.add_argument('--agent', help='Filter by agent ID')
    list_parser.add_argument('--detailed', '-d', action='store_true', help='Show detailed information')

    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect a sandbox')
    inspect_parser.add_argument('sandbox_id', help='Sandbox ID to inspect')

    # Terminate command
    terminate_parser = subparsers.add_parser('terminate', help='Terminate a sandbox')
    terminate_parser.add_argument('sandbox_id', help='Sandbox ID to terminate')
    terminate_parser.add_argument('--force', '-f', action='store_true', help='Force termination')

    # Kill agent command
    kill_parser = subparsers.add_parser('kill-agent', help='Kill all sandboxes for an agent')
    kill_parser.add_argument('agent_id', help='Agent ID')
    kill_parser.add_argument('--force', '-f', action='store_true', help='Force termination')

    # Metrics command
    metrics_parser = subparsers.add_parser('metrics', help='Show resource metrics')
    metrics_parser.add_argument('--agent', help='Filter by agent ID')

    # Logs command
    logs_parser = subparsers.add_parser('logs', help='Show audit logs')
    logs_parser.add_argument('--agent', help='Filter by agent ID')
    logs_parser.add_argument('--sandbox', help='Filter by sandbox ID')
    logs_parser.add_argument('--operation', help='Filter by operation type')
    logs_parser.add_argument('--limit', type=int, default=50, help='Maximum number of logs')
    logs_parser.add_argument('--json', action='store_true', help='Output in JSON format')

    # Guardian commands
    approve_parser = subparsers.add_parser('approve-agent', help='Approve an agent')
    approve_parser.add_argument('agent_id', help='Agent ID to approve')

    revoke_parser = subparsers.add_parser('revoke-agent', help='Revoke agent approval')
    revoke_parser.add_argument('agent_id', help='Agent ID to revoke')

    acl_parser = subparsers.add_parser('add-acl', help='Add volume ACL')
    acl_parser.add_argument('host_path', help='Host path')
    acl_parser.add_argument('container_path', help='Container path')
    acl_parser.add_argument('--mode', choices=['ro', 'rw'], default='rw', help='Access mode')
    acl_parser.add_argument('--allowed', nargs='*', help='Allowed patterns')
    acl_parser.add_argument('--blocked', nargs='*', help='Blocked patterns')

    guardian_parser = subparsers.add_parser('guardian-status', help='Show Guardian status')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = SandboxCLI()

    try:
        if args.command == 'list':
            await cli.list_sandboxes(agent_id=args.agent, detailed=args.detailed)
        elif args.command == 'inspect':
            await cli.inspect_sandbox(args.sandbox_id)
        elif args.command == 'terminate':
            await cli.terminate_sandbox(args.sandbox_id, force=args.force)
        elif args.command == 'kill-agent':
            await cli.kill_agent_sandboxes(args.agent_id, force=args.force)
        elif args.command == 'metrics':
            await cli.show_metrics(agent_id=args.agent)
        elif args.command == 'logs':
            await cli.show_audit_logs(
                agent_id=args.agent,
                sandbox_id=args.sandbox,
                operation=args.operation,
                limit=args.limit,
                json_output=args.json
            )
        elif args.command == 'approve-agent':
            await cli.approve_agent(args.agent_id)
        elif args.command == 'revoke-agent':
            await cli.revoke_agent(args.agent_id)
        elif args.command == 'add-acl':
            await cli.add_volume_acl(
                args.host_path,
                args.container_path,
                args.mode,
                args.allowed,
                args.blocked
            )
        elif args.command == 'guardian-status':
            await cli.show_guardian_status()
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\nOperation cancelled.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())