# Production Hardening & Reliability Module

Comprehensive reliability and recovery system for production deployment on home/small office PCs.

## Features

### 1. Crash Recovery (`crash_recovery.py`)
- **Automatic State Checkpointing**: Saves system state every 30 seconds
- **Recovery on Crash**: Automatically restores state after crashes
- **ACID Semantics**: Ensures last transaction is rolled back
- **Checkpoint Management**: Maintains history of checkpoints for recovery

```python
from app.reliability.crash_recovery import CrashRecoveryManager

recovery_manager = CrashRecoveryManager()
await recovery_manager.start()
await recovery_manager.create_checkpoint(state={"data": "value"})
recovered_state = await recovery_manager.recover_from_crash()
```

### 2. Auto-Restart (`auto_restart.py`)
- **Automatic Process Restart**: Restarts within 5 seconds on failure
- **Restart Limiting**: Max 3 restarts per hour to prevent restart loops
- **Restart Tracking**: Logs all restarts with timestamps and reasons
- **Windows Service Integration**: Runs as background service

```python
from app.reliability.auto_restart import AutoRestartService

service = AutoRestartService()
service.record_restart("process_failure", exit_code=1)
status = service.get_restart_status()
```

### 3. Health Monitoring (`health_monitor.py`)
- **LLM Responsiveness**: Checks if LLM responds within timeout
- **Database Health**: Verifies SQLite read/write capability
- **Disk Space**: Warns if < 1GB free, critical if < 512MB
- **Memory Pressure**: Tracks OOM risk and available memory
- **Component Status**: Monitors sandboxes and agent pools

```python
from app.reliability.health_monitor import HealthMonitor

monitor = HealthMonitor()
health_status = await monitor.check_all_health()
summary = monitor.get_health_summary()
print(monitor.format_health_report())
```

### 4. Graceful Degradation (`degradation.py`)
- **Component Fallbacks**: Uses knowledge base/cache when LLM unavailable
- **Reduced Functionality**: Scales down gracefully under resource constraints
- **Offline Mode**: Continues working without network connectivity
- **Component Recovery**: Automatically attempts recovery of failed components

```python
from app.reliability.degradation import GracefulDegradationManager

degradation = GracefulDegradationManager()
await degradation.handle_component_failure("llm", error)
capabilities = degradation.get_degraded_capabilities()
```

### 5. Data Integrity (`data_integrity.py`)
- **Write-Ahead Logging (WAL)**: Enabled automatically for durability
- **Checksums**: SHA256 checksums on all persisted data
- **Regular Integrity Checks**: Hourly verification of data consistency
- **Automatic Backup**: Daily full + hourly incremental backups
- **Backup Strategy**: 7 days full, 24 hours incremental, 4 weeks archive

```python
from app.reliability.data_integrity import DataIntegrityManager

integrity = DataIntegrityManager()
await integrity.create_backup("file_path", backup_type="full")
is_valid, msg = await integrity.check_integrity("file_path")
await integrity.cleanup_old_backups(backup_type="full", keep_count=7)
```

### 6. Event Logging (`event_logger.py`)
- **Structured Logging**: JSON format for easy parsing
- **Log Rotation**: Daily rotation with 90-day retention
- **Full Audit Trail**: All operations logged with timestamps
- **Diagnostics Bundle**: Creates zip with logs, config, system info

```python
from app.reliability.event_logger import EventLogger

logger = EventLogger()
await logger.log_event("INFO", "component", "event_type", "message", {"details": "value"})
events = await logger.get_events(component="llm", level="ERROR", hours=24)
bundle = await logger.create_diagnostics_bundle()
```

### 7. Database Optimization (`db_optimization.py`)
- **WAL Mode**: Write-Ahead Logging enabled
- **PRAGMA Tuning**: Optimized for reliability + performance
- **Transaction Management**: Explicit boundaries with rollback support
- **Retry Logic**: Automatic retry on SQLITE_BUSY with exponential backoff

```python
from app.reliability.db_optimization import DatabaseOptimizer

optimizer = DatabaseOptimizer("db_path")
optimizer.optimize_for_reliability()
optimizer.vacuum_database()
optimizer.analyze_database()
stats = optimizer.get_database_stats()
```

### 8. Update Management (`updater.py`)
- **Auto-Updates**: Checks daily for updates
- **Background Download**: No disruption to user
- **Graceful Restart**: Saves state before restart
- **Rollback Support**: Easy rollback to previous version

```python
from app.reliability.updater import UpdateManager

updater = UpdateManager()
version = await updater.check_for_updates()
if version:
    backup = await updater.backup_current_version()
    await updater.install_update(version)
```

### 9. Watchdog Service (`watchdog.py`)
- **External Monitoring**: Separate process watches main process
- **Hang Detection**: Detects hangs (no response > 30s)
- **Automatic Restart**: Force restarts if needed
- **Windows Task Scheduler**: Integration for regular checks

```python
from app.reliability.watchdog import WatchdogService

watchdog = WatchdogService(main_process_pid)
await watchdog.start()
status = watchdog.get_watchdog_status()
```

## CLI Commands

```bash
# Show system health status
python -m app.reliability.cli health

# Create diagnostics bundle for support
python -m app.reliability.cli diagnostics

# View event logs
python -m app.reliability.cli logs [component]
python -m app.reliability.cli search "error message"

# View auto-restart status
python -m app.reliability.cli restart-status

# Show database statistics
python -m app.reliability.cli db-stats

# List backups
python -m app.reliability.cli backups

# Show checkpoint information
python -m app.reliability.cli checkpoint-info

# Show update status
python -m app.reliability.cli update-status

# Run database maintenance
python -m app.reliability.cli maintenance
```

## System Integration

The reliability module is automatically initialized when the system starts:

```python
from app.system_startup import SystemApplication

app = SystemApplication()
app.run()  # Initializes all reliability components
```

## Database Structure

All reliability data is stored in `./data/reliability.db`:

- **checkpoints**: State snapshots for crash recovery
- **restart_records**: Auto-restart event history
- **health_history**: Component health check results
- **events**: Structured event log
- **integrity_checks**: File integrity verification records
- **backup_records**: Backup operation tracking
- **updates**: Update history

## Performance Tuning

The system automatically applies these SQLite optimizations:

- `PRAGMA journal_mode=WAL`: Write-Ahead Logging for durability
- `PRAGMA synchronous=NORMAL`: Fast but safe writes
- `PRAGMA cache_size=10000`: Larger cache for better performance
- `PRAGMA temp_store=MEMORY`: In-memory temp storage
- `PRAGMA busy_timeout=5000`: 5-second timeout on locked database
- Regular `VACUUM` and `ANALYZE` for optimization

## Testing

Comprehensive test suite included:

```bash
pytest tests/reliability/ -v
```

Tests cover:
- Crash recovery scenarios
- Health monitoring accuracy
- Data integrity verification
- Auto-restart functionality
- Graceful degradation
- Event logging
- Database optimization

## Production Deployment

For production deployment:

1. **Enable all reliability features** - Enabled by default
2. **Configure backups** - Set backup retention policy
3. **Monitor health** - Use health CLI command regularly
4. **Review logs** - Check for anomalies
5. **Create diagnostics bundle** - Before reporting issues
6. **Set up watchdog** - Run as Windows service

## Architecture

```
┌─────────────────────────────────────────┐
│     System Startup (system_startup.py)  │
└────────────┬────────────────────────────┘
             │
             ├─→ Database Optimizer
             │   (enable WAL, PRAGMA tuning)
             │
             ├─→ Crash Recovery Manager
             │   (checkpoint loop)
             │
             ├─→ Health Monitor
             │   (background checks)
             │
             ├─→ Event Logger
             │   (structured logging)
             │
             └─→ Graceful Degradation Manager
                 (fallback strategies)
                 
CLI Interface (reliability/cli.py)
├─ Health Status
├─ Diagnostics Bundle
├─ Event Logs
├─ Restart Status
├─ Database Stats
├─ Backups List
├─ Checkpoint Info
├─ Update Status
└─ Maintenance Tasks
```

## Best Practices

1. **Regular Backups**: System automatically backs up daily - keep multiple copies
2. **Monitor Health**: Run health checks regularly, investigate warnings
3. **Review Logs**: Check event logs for anomalies
4. **Database Maintenance**: System auto-optimizes, but review stats
5. **Update Regularly**: Apply updates when available
6. **Test Recovery**: Periodically test crash recovery procedures
7. **Create Diagnostics**: Save diagnostics bundle monthly for baseline

## Troubleshooting

### High Memory Usage
- Check health status: `python -m app.reliability.cli health`
- Review logs: `python -m app.reliability.cli logs`
- Create diagnostics: `python -m app.reliability.cli diagnostics`

### Database Errors
- Run maintenance: `python -m app.reliability.cli maintenance`
- Check integrity: Use CLI to verify database
- Restore from backup if needed

### Frequent Restarts
- Check restart status: `python -m app.reliability.cli restart-status`
- Review logs for underlying cause
- May indicate resource shortage

## Contributing

When adding new components, integrate with reliability module:

1. Register component with degradation manager
2. Add health check to health monitor
3. Log events through event logger
4. Add CLI command for status

## License

See LICENSE file in project root
