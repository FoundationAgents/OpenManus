"""
CLI commands for reliability management
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from app.logger import logger
from .crash_recovery import CrashRecoveryManager, CheckpointManager
from .auto_restart import AutoRestartService, ServiceManager
from .health_monitor import HealthMonitor
from .event_logger import EventLogger
from .data_integrity import DataIntegrityManager
from .db_optimization import DatabaseOptimizer
from .degradation import GracefulDegradationManager
from .updater import UpdateManager


class ReliabilityCLI:
    """CLI interface for reliability features"""

    def __init__(self):
        self.data_dir = Path("./data")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def health_status(self):
        """Display system health status"""
        print("\n" + "=" * 60)
        print("SYSTEM HEALTH STATUS")
        print("=" * 60)

        try:
            monitor = HealthMonitor(str(self.data_dir / "reliability.db"))
            report = monitor.format_health_report()
            print(report)

            # Also show detailed summary
            summary = monitor.get_health_summary()
            print("\nDetailed Status:")
            for component, details in summary.get("components", {}).items():
                print(f"  {component}: {details['status']}")

        except Exception as e:
            print(f"Error getting health status: {e}", file=sys.stderr)

    def diagnostics_bundle(self):
        """Create a diagnostics bundle"""
        print("\nCreating diagnostics bundle...")

        try:
            event_logger = EventLogger(str(self.data_dir / "reliability.db"))
            bundle = asyncio.run(event_logger.create_diagnostics_bundle())

            if bundle:
                print(f"✓ Diagnostics bundle created: {bundle.bundle_path}")
                print(f"  - Logs included: {bundle.logs_included}")
                print(f"  - Config included: {bundle.config_included}")
                print(f"  - System info included: {bundle.system_info_included}")
            else:
                print("✗ Failed to create diagnostics bundle", file=sys.stderr)

        except Exception as e:
            print(f"Error creating diagnostics bundle: {e}", file=sys.stderr)

    def show_logs(self, component: Optional[str] = None, level: Optional[str] = None, limit: int = 50):
        """Display event logs"""
        print(f"\nEvent Logs (limit: {limit})")
        print("=" * 60)

        try:
            event_logger = EventLogger(str(self.data_dir / "reliability.db"))
            events = asyncio.run(event_logger.get_events(
                component=component,
                level=level,
                limit=limit
            ))

            if not events:
                print("No events found")
                return

            for event in events:
                print(f"[{event.timestamp}] {event.level:8} {event.component:15} {event.event_type:15}")
                print(f"  Message: {event.message}")
                if event.details:
                    print(f"  Details: {json.dumps(event.details, indent=4)}")

        except Exception as e:
            print(f"Error retrieving logs: {e}", file=sys.stderr)

    def search_logs(self, query: str):
        """Search logs"""
        print(f"\nSearching logs for: {query}")
        print("=" * 60)

        try:
            event_logger = EventLogger(str(self.data_dir / "reliability.db"))
            results = asyncio.run(event_logger.search_logs(query, limit=20))

            if not results:
                print("No matching logs found")
                return

            for result in results:
                print(f"[{result['timestamp']}] {result['level']:8} {result['component']:15}")
                print(f"  {result['message']}")

        except Exception as e:
            print(f"Error searching logs: {e}", file=sys.stderr)

    def restart_status(self):
        """Display restart status"""
        print("\n" + "=" * 60)
        print("AUTO-RESTART STATUS")
        print("=" * 60)

        try:
            service = AutoRestartService(str(self.data_dir / "reliability.db"))
            status = service.get_restart_status()

            print(f"Restart count (last hour): {status['restart_count_1h']}/{status['max_restarts_per_hour']}")
            print(f"Can restart: {'Yes' if status['can_restart'] else 'No'}")
            print(f"Restart delay: {status['restart_delay']} seconds")

            if status['recent_restarts']:
                print("\nRecent restarts:")
                for restart in status['recent_restarts']:
                    print(f"  [{restart['timestamp']}] {restart['reason']} (exit: {restart['exit_code']})")

        except Exception as e:
            print(f"Error getting restart status: {e}", file=sys.stderr)

    def database_stats(self):
        """Display database statistics"""
        print("\n" + "=" * 60)
        print("DATABASE STATISTICS")
        print("=" * 60)

        try:
            optimizer = DatabaseOptimizer(str(self.data_dir / "reliability.db"))
            stats = optimizer.get_database_stats()

            for key, value in stats.items():
                print(f"{key:20} : {value}")

            # Check integrity
            integrity = optimizer.check_database_integrity()
            print(f"\nIntegrity check: {integrity['integrity'].upper()}")
            if integrity['integrity'] != 'ok':
                print(f"  Status: {integrity['status']}")

        except Exception as e:
            print(f"Error getting database stats: {e}", file=sys.stderr)

    def backup_list(self):
        """List backups"""
        print("\n" + "=" * 60)
        print("BACKUP HISTORY")
        print("=" * 60)

        try:
            manager = DataIntegrityManager(str(self.data_dir / "reliability.db"))
            backups = manager.get_backup_history(limit=20)

            if not backups:
                print("No backups found")
                return

            print(f"{'Type':<15} {'Size':<15} {'Timestamp':<25} {'Source'}")
            print("-" * 80)

            for backup in backups:
                size_mb = backup.size_bytes / (1024 * 1024)
                print(f"{backup.backup_type:<15} {size_mb:>10.2f} MB  {backup.timestamp:<25} {backup.source_path}")

        except Exception as e:
            print(f"Error listing backups: {e}", file=sys.stderr)

    def update_status(self):
        """Display update status"""
        print("\n" + "=" * 60)
        print("UPDATE STATUS")
        print("=" * 60)

        try:
            updater = UpdateManager()
            status = updater.get_update_status()

            print(f"Current version: {status['current_version']}")
            print(f"Available backups: {status['available_backups']}")

            if status['update_history']:
                print("\nUpdate history:")
                for update in status['update_history']:
                    print(f"  {update['from']} → {update['to']} ({update['status']})")
                    print(f"    [{update['timestamp']}]")

        except Exception as e:
            print(f"Error getting update status: {e}", file=sys.stderr)

    def checkpoint_info(self):
        """Display checkpoint information"""
        print("\n" + "=" * 60)
        print("CHECKPOINT INFORMATION")
        print("=" * 60)

        try:
            checkpoint_mgr = CheckpointManager(str(self.data_dir / "reliability.db"))
            latest = checkpoint_mgr.get_latest_checkpoint()

            if latest:
                print(f"Latest checkpoint: {latest.checkpoint_id}")
                print(f"Timestamp: {latest.timestamp}")
                print(f"Checksum: {latest.checksum[:16]}...")
                print(f"Metadata: {json.dumps(latest.metadata, indent=2)}")
            else:
                print("No checkpoints found")

        except Exception as e:
            print(f"Error getting checkpoint info: {e}", file=sys.stderr)

    def run_maintenance(self):
        """Run database maintenance"""
        print("\nRunning database maintenance...")

        try:
            optimizer = DatabaseOptimizer(str(self.data_dir / "reliability.db"))
            optimizer.optimize_for_reliability()
            optimizer.analyze_database()
            optimizer.optimize_indexes()

            print("✓ Database maintenance completed")

        except Exception as e:
            print(f"✗ Maintenance failed: {e}", file=sys.stderr)


def main():
    """Main CLI entry point"""
    cli = ReliabilityCLI()

    if len(sys.argv) < 2:
        print("OpenManus Reliability CLI")
        print("\nUsage: python -m app.reliability.cli <command> [options]")
        print("\nCommands:")
        print("  health              - Show system health status")
        print("  diagnostics         - Create diagnostics bundle")
        print("  logs [component]    - Show event logs")
        print("  search <query>      - Search logs")
        print("  restart-status      - Show auto-restart status")
        print("  db-stats            - Show database statistics")
        print("  backups             - List backups")
        print("  checkpoint-info     - Show checkpoint information")
        print("  update-status       - Show update status")
        print("  maintenance         - Run database maintenance")
        return

    command = sys.argv[1]

    if command == "health":
        cli.health_status()
    elif command == "diagnostics":
        cli.diagnostics_bundle()
    elif command == "logs":
        component = sys.argv[2] if len(sys.argv) > 2 else None
        cli.show_logs(component=component)
    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: search <query>")
            return
        cli.search_logs(sys.argv[2])
    elif command == "restart-status":
        cli.restart_status()
    elif command == "db-stats":
        cli.database_stats()
    elif command == "backups":
        cli.backup_list()
    elif command == "checkpoint-info":
        cli.checkpoint_info()
    elif command == "update-status":
        cli.update_status()
    elif command == "maintenance":
        cli.run_maintenance()
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
