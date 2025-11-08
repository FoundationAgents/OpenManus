# Versioning Engine

A comprehensive file versioning system for tracking changes with SQLite backend and content-addressable storage.

## Features

- **Automatic Version Creation**: Tracks file changes from editor saves, tool operations, and LocalService writes
- **Content Deduplication**: Uses SHA-256 hashing to avoid storing duplicate content
- **Snapshot Support**: Create and restore workflow states with multiple files
- **Rollback Operations**: Restore files to previous versions with Guardian security checks
- **Diff Generation**: Line-level diffs between versions using unified diff format
- **Retention Policies**: Configurable cleanup of old versions
- **Pattern-based Filtering**: Track only specified file types and exclude patterns

## Architecture

### Core Components

1. **VersioningEngine** (`app/storage/versioning.py`)
   - SQLite database for metadata
   - Content-addressable storage for file blobs
   - Thread-safe operations with RLock

2. **VersioningService** (`app/storage/service.py`)
   - Service layer for file operation hooks
   - Integration points for editor, tools, and LocalService

3. **Configuration** (`app/config.py`)
   - VersioningSettings class with comprehensive options
   - TOML configuration support

### Database Schema

```sql
-- File content blobs (deduplicated storage)
CREATE TABLE file_blobs (
    content_hash TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Version metadata
CREATE TABLE versions (
    version_id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    agent TEXT NOT NULL,
    reason TEXT,
    is_snapshot BOOLEAN DEFAULT FALSE,
    snapshot_id TEXT,
    FOREIGN KEY (content_hash) REFERENCES file_blobs(content_hash)
);

-- Workflow snapshots
CREATE TABLE snapshots (
    snapshot_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    timestamp TIMESTAMP NOT NULL,
    agent TEXT NOT NULL,
    metadata TEXT  -- JSON metadata
);

-- Snapshot file relationships
CREATE TABLE snapshot_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(snapshot_id),
    FOREIGN KEY (version_id) REFERENCES versions(version_id),
    UNIQUE(snapshot_id, version_id)
);
```

## Configuration

Add to your `config/config.toml`:

```toml
[versioning]
enable_versioning = true               # Enable file versioning
database_path = "workspace/.versions/versions.db"  # SQLite database path
storage_path = "workspace/.versions/storage"        # Content storage directory
auto_version = true                   # Automatically create versions on file saves
retention_days = 30                   # Default retention period for versions in days
max_storage_mb = 1024                  # Maximum storage size in MB
cleanup_interval_hours = 24            # Cleanup interval in hours
track_file_patterns = ["*.py", "*.js", "*.ts", "*.go", "*.rs", "*.sql", "*.sh", "*.md"]
exclude_patterns = [".git/*", "node_modules/*", "__pycache__/*", ".pytest_cache/*"]
enable_snapshots = true                 # Enable snapshot functionality
max_snapshots = 100                    # Maximum number of snapshots to keep
enable_guardian_checks = true           # Enable Guardian checks on rollback operations
```

## Integration Points

### Editor Integration

The versioning system automatically hooks into:
- **CodeEditor** (`app/ui/editor/code_editor.py`) - On file saves
- **StrReplaceEditor** (`app/tool/str_replace_editor.py`) - On file operations
- **LocalService** (`app/local_service.py`) - On file writes

### Usage Examples

#### Programmatic API

```python
from app.storage.service import get_versioning_service

# Get versioning service
service = get_versioning_service()

# Create a version (automatic on file operations)
version_id = service.on_file_save(
    "myfile.py", 
    "content here", 
    agent="user", 
    reason="Manual save"
)

# Get version history
history = service.get_version_history("myfile.py")

# Generate diff
diff = service.get_file_diff(version_id1, version_id2)

# Create snapshot
snapshot_id = service.create_snapshot(
    "my_snapshot",
    ["file1.py", "file2.py"],
    description="Important checkpoint"
)

# Rollback file
success = service.rollback_file(
    "myfile.py", 
    version_id, 
    agent="user", 
    reason="Fix bug"
)
```

#### CLI Interface

```bash
# View version history
python -m app.cli_versioning history main.py

# Show diff between versions
python -m app.cli_versioning diff <version_id> --to-version <version_id>

# Rollback to a version
python -m app.cli_versioning rollback main.py <version_id>

# Create snapshot
python -m app.cli_versioning snapshot-create "checkpoint" file1.py file2.py

# List snapshots
python -m app.cli_versioning snapshot-list

# Restore snapshot
python -m app.cli_versioning snapshot-restore <snapshot_id>

# Get version content
python -m app.cli_versioning content <version_id>

# Show storage statistics
python -m app.cli_versioning stats

# Clean up old versions
python -m app.cli_versioning cleanup --days 30
```

## Security Features

### Guardian Checks

When `enable_guardian_checks` is true, rollback operations require:
- Authorized agents (system, admin, developer)
- Valid rollback reason
- Version within retention period

### Content Integrity

- SHA-256 hashing ensures content integrity
- Content-addressable storage prevents corruption
- Deduplication reduces storage overhead

## Storage Management

### Deduplication

Identical content across files is stored once:
- Multiple files with same content share one blob
- Version metadata tracks which blob each version uses
- Significant space savings for common code patterns

### Retention Policy

- Automatic cleanup of versions older than retention period
- Configurable per-agent cleanup
- Storage size limits with configurable thresholds

## Testing

Run the comprehensive test suite:

```bash
# Run all versioning tests
python -m pytest tests/test_versioning.py -v

# Run demo
python test_versioning_demo.py
```

## Performance Considerations

- **SQLite**: Efficient for small to medium repositories
- **Content Hashing**: O(n) for file content, O(1) lookups
- **Deduplication**: Reduces I/O and storage requirements
- **Thread Safety**: RLock ensures concurrent access safety

## Limitations

- Text files only (binary files not supported)
- File size limited by available memory for hashing
- SQLite scaling limits for very large repositories
- No built-in compression (filesystem-level only)

## Future Enhancements

- Binary file support with base64 encoding
- Compression for stored content
- Distributed storage backends
- Git integration for existing repositories
- Web UI for version management
- Conflict resolution for concurrent edits

## Troubleshooting

### Common Issues

1. **Versions not created**: Check file patterns in configuration
2. **Storage errors**: Verify directory permissions
3. **Database locked**: Ensure single process access
4. **Rollback denied**: Check Guardian agent permissions

### Debug Logging

Enable debug logging:

```python
import logging
logging.getLogger('app.storage').setLevel(logging.DEBUG)
```

This will show detailed versioning operations and decisions.