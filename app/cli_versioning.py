"""
CLI interface for versioning system operations.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from app.config import config
from app.storage.versioning import get_versioning_engine
from app.storage.service import get_versioning_service
from app.logger import logger


def format_version_metadata(version):
    """Format version metadata for display."""
    return f"""
Version ID: {version.version_id}
File: {version.file_path}
Timestamp: {version.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Agent: {version.agent}
Reason: {version.reason}
Size: {version.size} bytes
Hash: {version.content_hash}
Snapshot: {version.snapshot_id or 'No'}
"""


def format_snapshot_metadata(snapshot):
    """Format snapshot metadata for display."""
    return f"""
Snapshot ID: {snapshot.snapshot_id}
Name: {snapshot.name}
Description: {snapshot.description}
Timestamp: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Agent: {snapshot.agent}
Files: {len(snapshot.file_versions)}
Metadata: {json.dumps(snapshot.metadata, indent=2)}
"""


def cmd_history(args):
    """Show version history for a file."""
    engine = get_versioning_engine()
    history = engine.get_version_history(args.file, args.limit, args.offset)
    
    if not history:
        print(f"No version history found for {args.file}")
        return
    
    print(f"Version history for {args.file}:")
    print("=" * 50)
    
    for version in history:
        print(format_version_metadata(version))
        print("-" * 50)


def cmd_diff(args):
    """Show diff between versions."""
    engine = get_versioning_engine()
    
    try:
        diff = engine.generate_diff(args.from_version, args.to_version)
        if diff:
            print(diff)
        else:
            print("No differences found.")
    except Exception as e:
        print(f"Error generating diff: {e}")
        sys.exit(1)


def cmd_rollback(args):
    """Rollback a file to a specific version."""
    service = get_versioning_service()
    
    success = service.rollback_file(
        args.file,
        args.version,
        agent=args.agent,
        reason=args.reason
    )
    
    if success:
        print(f"Successfully rolled back {args.file} to version {args.version}")
    else:
        print(f"Failed to rollback {args.file} to version {args.version}")
        sys.exit(1)


def cmd_snapshot_create(args):
    """Create a snapshot."""
    service = get_versioning_service()
    
    snapshot_id = service.create_snapshot(
        args.name,
        args.files,
        description=args.description,
        agent=args.agent,
        metadata=json.loads(args.metadata) if args.metadata else None
    )
    
    if snapshot_id:
        print(f"Created snapshot {snapshot_id}")
    else:
        print("Failed to create snapshot")
        sys.exit(1)


def cmd_snapshot_list(args):
    """List snapshots."""
    engine = get_versioning_engine()
    snapshots = engine.list_snapshots(args.limit, args.offset)
    
    if not snapshots:
        print("No snapshots found")
        return
    
    print("Snapshots:")
    print("=" * 50)
    
    for snapshot in snapshots:
        print(format_snapshot_metadata(snapshot))
        print("-" * 50)


def cmd_snapshot_restore(args):
    """Restore a snapshot."""
    engine = get_versioning_engine()
    
    success = engine.restore_snapshot(
        args.snapshot_id,
        agent=args.agent,
        reason=args.reason
    )
    
    if success:
        print(f"Successfully restored snapshot {args.snapshot_id}")
    else:
        print(f"Failed to restore snapshot {args.snapshot_id}")
        sys.exit(1)


def cmd_content(args):
    """Get content of a specific version."""
    engine = get_versioning_engine()
    content = engine.get_version_content(args.version)
    
    if content is not None:
        print(content)
    else:
        print(f"Version {args.version} not found")
        sys.exit(1)


def cmd_stats(args):
    """Show storage statistics."""
    engine = get_versioning_engine()
    stats = engine.get_storage_stats()
    
    print("Versioning Storage Statistics:")
    print("=" * 30)
    print(f"Total versions: {stats['version_count']}")
    print(f"Unique content blobs: {stats['blob_count']}")
    print(f"Total size: {stats['total_size_bytes']} bytes")
    print(f"Disk usage: {stats['disk_usage_bytes']} bytes")
    print(f"Deduplication ratio: {stats['deduplication_ratio']:.2f}")
    print(f"Snapshots: {stats['snapshot_count']}")
    print(f"Database path: {stats['database_path']}")
    print(f"Storage path: {stats['storage_path']}")


def cmd_cleanup(args):
    """Clean up old versions."""
    engine = get_versioning_engine()
    
    deleted_count = engine.cleanup_old_versions(args.days, args.agent)
    print(f"Cleaned up {deleted_count} old versions (older than {args.days} days)")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Versioning system CLI interface",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show version history for a file')
    history_parser.add_argument('file', help='File path')
    history_parser.add_argument('--limit', type=int, default=50, help='Limit number of versions')
    history_parser.add_argument('--offset', type=int, default=0, help='Offset for pagination')
    history_parser.set_defaults(func=cmd_history)
    
    # Diff command
    diff_parser = subparsers.add_parser('diff', help='Show diff between versions')
    diff_parser.add_argument('from_version', help='Source version ID')
    diff_parser.add_argument('--to-version', help='Target version ID (default: latest)')
    diff_parser.set_defaults(func=cmd_diff)
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback file to a version')
    rollback_parser.add_argument('file', help='File path')
    rollback_parser.add_argument('version', help='Version ID to rollback to')
    rollback_parser.add_argument('--agent', default='cli', help='Agent performing rollback')
    rollback_parser.add_argument('--reason', default='CLI rollback', help='Reason for rollback')
    rollback_parser.set_defaults(func=cmd_rollback)
    
    # Snapshot create command
    snapshot_create_parser = subparsers.add_parser('snapshot-create', help='Create a snapshot')
    snapshot_create_parser.add_argument('name', help='Snapshot name')
    snapshot_create_parser.add_argument('files', nargs='+', help='Files to include in snapshot')
    snapshot_create_parser.add_argument('--description', default='', help='Snapshot description')
    snapshot_create_parser.add_argument('--agent', default='cli', help='Agent creating snapshot')
    snapshot_create_parser.add_argument('--metadata', help='JSON metadata for snapshot')
    snapshot_create_parser.set_defaults(func=cmd_snapshot_create)
    
    # Snapshot list command
    snapshot_list_parser = subparsers.add_parser('snapshot-list', help='List snapshots')
    snapshot_list_parser.add_argument('--limit', type=int, default=50, help='Limit number of snapshots')
    snapshot_list_parser.add_argument('--offset', type=int, default=0, help='Offset for pagination')
    snapshot_list_parser.set_defaults(func=cmd_snapshot_list)
    
    # Snapshot restore command
    snapshot_restore_parser = subparsers.add_parser('snapshot-restore', help='Restore a snapshot')
    snapshot_restore_parser.add_argument('snapshot_id', help='Snapshot ID to restore')
    snapshot_restore_parser.add_argument('--agent', default='cli', help='Agent performing restore')
    snapshot_restore_parser.add_argument('--reason', default='CLI snapshot restore', help='Reason for restore')
    snapshot_restore_parser.set_defaults(func=cmd_snapshot_restore)
    
    # Content command
    content_parser = subparsers.add_parser('content', help='Get content of a version')
    content_parser.add_argument('version', help='Version ID')
    content_parser.set_defaults(func=cmd_content)
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show storage statistics')
    stats_parser.set_defaults(func=cmd_stats)
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old versions')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Delete versions older than this many days')
    cleanup_parser.add_argument('--agent', help='Only delete versions by this agent')
    cleanup_parser.set_defaults(func=cmd_cleanup)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()