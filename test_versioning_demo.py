#!/usr/bin/env python3
"""
Demo script to test versioning system functionality.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.storage.versioning import get_versioning_engine
from app.storage.service import get_versioning_service
from app.config import config


def demo_versioning():
    """Demonstrate versioning system functionality."""
    print("=== Versioning System Demo ===\n")
    
    # Create temporary directory for demo
    temp_dir = Path(tempfile.mkdtemp(prefix="versioning_demo_"))
    print(f"Using temporary directory: {temp_dir}")
    
    try:
        # Initialize versioning engine with temp storage
        db_path = temp_dir / "versions.db"
        storage_path = temp_dir / "storage"
        
        engine = get_versioning_engine()
        service = get_versioning_service()
        
        print("\n1. Creating file versions...")
        
        # Create some test files and versions
        test_files = {
            "main.py": "print('Hello, World!')",
            "utils.py": "def helper():\n    return 'helper'",
            "README.md": "# Test Project\n\nThis is a test project."
        }
        
        version_ids = []
        for file_path, content in test_files.items():
            version_id = service.on_file_save(
                file_path, content, agent="demo", reason="Initial version"
            )
            if version_id:
                version_ids.append(version_id)
                print(f"  ✓ Created version for {file_path}: {version_id}")
            else:
                print(f"  ✗ Failed to create version for {file_path}")
        
        print(f"\n2. Created {len(version_ids)} versions")
        
        # Test version history
        print("\n3. Version history for main.py:")
        history = service.get_version_history("main.py")
        for version in history:
            print(f"  - {version.version_id} ({version.timestamp.strftime('%Y-%m-%d %H:%M:%S')}) by {version.agent}")
        
        # Test file modification
        print("\n4. Modifying main.py...")
        new_content = "print('Hello, Modified World!')\nprint('Second line')"
        version_id = service.on_file_edit(
            "main.py", test_files["main.py"], new_content, agent="demo", reason="Added second line"
        )
        if version_id:
            print(f"  ✓ Created new version: {version_id}")
        
        # Test diff generation
        print("\n5. Generating diff...")
        if len(history) > 0:
            diff = service.get_file_diff(history[0].version_id, version_id)
            print("  Diff between first and latest version:")
            print("  " + "\n  ".join(diff.split("\n")[:10]))
        
        # Test snapshot creation
        print("\n6. Creating snapshot...")
        snapshot_id = service.create_snapshot(
            "demo_snapshot",
            list(test_files.keys()),
            description="Demo snapshot with all test files",
            agent="demo"
        )
        if snapshot_id:
            print(f"  ✓ Created snapshot: {snapshot_id}")
        
        # Test storage statistics
        print("\n7. Storage statistics:")
        stats = engine.get_storage_stats()
        print(f"  Total versions: {stats['version_count']}")
        print(f"  Unique content blobs: {stats['blob_count']}")
        print(f"  Total size: {stats['total_size_bytes']} bytes")
        print(f"  Disk usage: {stats['disk_usage_bytes']} bytes")
        print(f"  Deduplication ratio: {stats['deduplication_ratio']:.2f}")
        print(f"  Snapshots: {stats['snapshot_count']}")
        
        print("\n8. Testing rollback...")
        if len(history) > 0:
            success = service.rollback_file(
                "main.py", history[0].version_id, agent="system", reason="Demo rollback"
            )
            if success:
                print("  ✓ Rollback successful")
                
                # Check rollback created a new version
                new_history = service.get_version_history("main.py")
                print(f"  New version history length: {len(new_history)}")
            else:
                print("  ✗ Rollback failed")
        
        print("\n=== Demo completed successfully! ===")
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
            print(f"\nCleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"Error cleaning up: {e}")


if __name__ == "__main__":
    demo_versioning()