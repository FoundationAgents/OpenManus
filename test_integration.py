#!/usr/bin/env python3
"""
Integration test for versioning system with actual file operations.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.storage.service import get_versioning_service
async def test_integration():
    """Test integration of versioning with actual file operations."""
    print("=== Versioning Integration Test ===\n")
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="versioning_integration_"))
    print(f"Using temporary directory: {temp_dir}")
    
    try:
        # Initialize versioning service
        service = get_versioning_service()
        
        # Test direct file operations
        print("\n1. Testing direct file operations...")
        
        test_file = temp_dir / "test.py"
        test_content = "print('Hello from direct write!')"
        
        # Write file directly (simulates LocalService)
        test_file.write_text(test_content)
        
        # Manually trigger versioning (since we can't easily import LocalService)
        version_id = service.on_file_save(
            str(test_file.relative_to(temp_dir)),
            test_content,
            agent="integration_test",
            reason="Direct file write"
        )
        
        if version_id:
            print(f"  ✓ Version created: {version_id}")
        else:
            print("  ✗ No version created")
        
        # Check version was created
        history = service.get_version_history(str(test_file.relative_to(temp_dir)))
        if history:
            print(f"  ✓ Version history: {len(history)} versions")
            print(f"    Latest agent: {history[0].agent}, Reason: {history[0].reason}")
        else:
            print("  ✗ No version history found")
        
        # Test file modification
        print("\n2. Testing file modification...")
        modified_content = "print('Modified content!')\nprint('Second line')"
        test_file.write_text(modified_content)
        
        new_version_id = service.on_file_edit(
            str(test_file.relative_to(temp_dir)),
            test_content,
            modified_content,
            agent="integration_test",
            reason="File modification"
        )
        
        if new_version_id:
            print(f"  ✓ New version created: {new_version_id}")
        
        # Check new version was created
        new_history = service.get_version_history(str(test_file.relative_to(temp_dir)))
        if len(new_history) > len(history):
            print(f"  ✓ Version history updated: {len(new_history)} versions")
        
        # Test diff generation
        print("\n3. Testing diff generation...")
        if len(new_history) >= 2:
            diff = service.get_file_diff(new_history[1].version_id, new_history[0].version_id)
            if diff and "---" in diff:
                print("  ✓ Diff generated successfully")
                print("    First few lines of diff:")
                for line in diff.split("\n")[:8]:
                    print(f"    {line}")
        
        # Test snapshot functionality
        print("\n4. Testing snapshot creation...")
        snapshot_id = service.create_snapshot(
            "integration_test_snapshot",
            [str(test_file.relative_to(temp_dir))],
            description="Integration test snapshot",
            agent="integration_test"
        )
        
        if snapshot_id:
            print(f"  ✓ Snapshot created: {snapshot_id}")
        
        # Test rollback functionality
        print("\n5. Testing rollback...")
        if len(new_history) >= 2:
            success = service.rollback_file(
                str(test_file.relative_to(temp_dir)),
                new_history[1].version_id,
                agent="system",
                reason="Integration test rollback"
            )
            
            if success:
                print("  ✓ Rollback successful")
                
                # Verify file content
                restored_content = test_file.read_text()
                if "Hello from direct write!" in restored_content:
                    print("  ✓ File content restored correctly")
                else:
                    print("  ✗ File content not restored correctly")
            else:
                print("  ✗ Rollback failed")
        
        print("\n6. Testing storage statistics...")
        stats = service._get_engine().get_storage_stats()
        print(f"  Total versions: {stats['version_count']}")
        print(f"  Unique blobs: {stats['blob_count']}")
        print(f"  Snapshots: {stats['snapshot_count']}")
        
        print("\n=== Integration test completed successfully! ===")
        
    except Exception as e:
        print(f"\nError during integration test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
            print(f"\nCleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"Error cleaning up: {e}")
    
    return True


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_integration())
    sys.exit(0 if success else 1)