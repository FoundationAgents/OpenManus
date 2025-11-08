# Adaptive Sandbox Engine Implementation

## Overview

The Adaptive Sandbox Engine replaces static sandbox configuration with an intelligent, agent-driven system where agents request specific tools, paths, and environment variables. The system dynamically assembles sandboxes just-in-time with Guardian validation, capability inheritance, and runtime resource control.

**Key Principle**: Security through specificity - only grant what's explicitly requested and approved.

## Architecture

### Core Components

#### 1. CapabilityGrant (`app/sandbox/adaptive/capability_grant.py`)

Defines what capabilities an agent can use in a sandbox execution:

```python
grant = CapabilityGrant(
    agent_id="agent_1",
    allowed_tools={"python", "git", "npm"},
    allowed_paths={
        "/home/user/projects": PathAccessMode.READ_WRITE,
        "/opt/tools": PathAccessMode.READ_ONLY,
    },
    env_whitelist={"PATH", "HOME", "PYTHONPATH"},
    env_vars={"CUSTOM_VAR": "value"},
    network_enabled=False,
    cpu_percent=80.0,
    memory_mb=512,
    timeout_seconds=300,
)
```

**Key Classes**:
- `CapabilityGrant`: Pydantic model defining capabilities
- `GrantManager`: Manages grants lifecycle (create, revoke, checkpoint)
- `GrantDecision`: Guardian checkpoint decision for approvals/denials
- `PathAccessMode`: Enum for file access (READ_ONLY, READ_WRITE)
- `GrantStatus`: Enum for grant lifecycle (PENDING, APPROVED, REVOKED, EXPIRED)

**Features**:
- Tool/executable access control
- File path ACL with read-only/read-write modes
- Environment variable filtering via whitelist
- Network access configuration
- Resource limits (CPU %, memory, timeout)
- Isolation level constraints
- Expiration tracking
- Status lifecycle management

#### 2. SandboxBuilder (`app/sandbox/adaptive/builder.py`)

Constructs the complete sandbox environment from a grant and isolation level:

```python
builder = SandboxBuilder(
    agent_id="agent_1",
    grant=grant,
    isolation_level=IsolationLevel.RESTRICTED,
    host_environment=os.environ,
)

environment = builder.build()

# Returns SandboxEnvironment with:
# - environment_variables: Dict of env vars for sandbox
# - volume_mounts: Docker volume mappings
# - readonly_paths: Paths that must be read-only
# - read_write_paths: Paths that can be written
# - resource_limits: CPU, memory, timeout
# - process_constraints: Subprocess, network, device access
# - isolation_level: Effective isolation level
# - granted_capabilities: Summary of what was granted
```

**Key Features**:
- Environment variable filtering based on whitelist
- Volume mount construction with access modes
- Resource limit reconciliation (grant + isolation)
- Process constraint application
- Platform-specific environment setup (MSVC_PATH for Windows, CUDA_HOME for Linux)
- Capability suggestions for common errors

#### 3. IsolationLevel (`app/sandbox/adaptive/isolation_levels.py`)

Five configurable isolation levels with progressively stricter constraints:

```python
class IsolationLevel(Enum):
    TRUSTED = 0      # Full trust, inherit all, no restrictions (dev only)
    MONITORED = 1    # Filtered env, all ops logged, no restrictions
    RESTRICTED = 2   # Granted capabilities only, ACL enforced, network policies
    SANDBOXED = 3    # Minimal env, Docker/strict process isolation
    ISOLATED = 4     # Full VM isolation if anomaly detected
```

**Configuration per level**:
- Environment inheritance (full vs whitelist)
- File system access (enforce ACL, readonly root)
- Process constraints (subprocess creation, network, devices)
- Syscall filtering (seccomp rules)
- Resource limits (CPU %, memory MB, timeout)
- Containerization (Docker, job objects)
- Monitoring (audit logging, syscall tracing, network monitoring)
- Auto-escalation rules

**Example config for RESTRICTED**:
```python
config = IsolationConfig(
    level=IsolationLevel.RESTRICTED,
    inherit_environment=False,
    env_whitelist=["PATH", "HOME", "USER", "SHELL"],
    enforce_acl=True,
    readonly_filesystem=True,
    allow_subprocess_creation=True,
    allow_network_access=False,
    enable_seccomp=True,
    blocked_syscalls=["ptrace", "kexec_load", "mount", "umount", ...],
    enforce_cpu_limit=True,
    cpu_percent=80.0,
    enforce_memory_limit=True,
    memory_mb=512,
    timeout_seconds=600,
)
```

#### 4. AdaptiveRuntimeMonitor (`app/sandbox/adaptive/runtime_monitor.py`)

Monitors resource usage during execution and triggers isolation escalation on anomalies:

```python
monitor = AdaptiveRuntimeMonitor(
    sandbox_id="sandbox_1",
    initial_isolation_level=IsolationLevel.MONITORED,
)

# Record metrics periodically
metrics = ResourceMetrics(
    timestamp=time.time(),
    cpu_percent=45.0,
    memory_mb=256,
    open_files=50,
    network_connections=2,
    subprocess_count=3,
    disk_io_ops=1000,
)
monitor.record_metrics(metrics)

# Check for escalation
should_escalate, next_level = monitor.should_escalate_isolation()
if should_escalate:
    monitor.escalate_isolation(next_level)
```

**Anomalies Detected**:
- `CPU_SPIKE`: CPU usage > threshold
- `MEMORY_SPIKE`: Memory usage > threshold
- `EXCESSIVE_FILE_OPS`: File operations spike
- `SUSPICIOUS_NETWORK`: Unexpected network connections
- `SUBPROCESS_EXPLOSION`: Subprocess count spike
- `TIMEOUT_RISK`: Command approaching timeout

**Escalation Logic**:
- Tracks violations per anomaly type
- Escalates when multiple anomalies (≥3) or high severity (>0.7)
- Auto-escalates to next isolation level per config
- Logs all anomalies and violations

#### 5. AdaptiveSandbox (`app/sandbox/adaptive/adaptive_sandbox.py`)

Main orchestrator that brings it all together:

```python
sandbox = AdaptiveSandbox(
    agent_id="agent_1",
    grant=grant,
    guardian=guardian_instance,
    isolation_level=IsolationLevel.MONITORED,
)

# Initialize with Guardian checkpoint
success = await sandbox.initialize()

# Run commands
output, exit_code, error = await sandbox.run_command("python script.py")

# Get metrics and decisions
env_summary = sandbox.get_environment_summary()
history = sandbox.get_execution_history()
monitoring = sandbox.get_monitoring_summary()

# Suggest fixes for errors
suggestions = sandbox.suggest_environment_fix("python: command not found")
```

**Workflow**:
1. Guardian validates grant before sandbox creation (checkpoint)
2. SandboxBuilder constructs environment based on grant + isolation level
3. AdaptiveRuntimeMonitor initialized to watch execution
4. Guardian validates each command execution
5. Monitor tracks resource usage and anomalies
6. Isolation escalates automatically if anomalies detected
7. Full audit trail maintained in execution history

### Guardian Integration

Guardian provides checkpoint validation at three key points:

1. **Sandbox Creation**: Validates grant capabilities before assembly
   ```python
   decision = await guardian.validate_operation(
       OperationRequest(
           agent_id="agent_1",
           operation="adaptive_sandbox_create",
           metadata={
               "capabilities": {"tools": [...], "paths": [...]}
           }
       )
   )
   if not decision.approved:
       raise SandboxError(f"Guardian denied: {decision.reason}")
   ```

2. **Command Execution**: Validates each command in context
   ```python
   decision = await guardian.validate_operation(
       OperationRequest(
           agent_id="agent_1",
           operation="adaptive_command_execute",
           command=cmd,
           metadata={"isolation_level": "RESTRICTED"}
       )
   )
   ```

3. **Grant Revocation**: Records revocations with timestamps
   ```python
   grant_manager.revoke_grant(grant_id)
   grant_manager.record_checkpoint(agent_id, decision)
   ```

## Isolation Level Escalation

Isolation levels can automatically escalate during execution when anomalies are detected:

```
TRUSTED ─escalate_on_anomaly──> MONITORED ─escalate──> RESTRICTED ─escalate──> SANDBOXED ─escalate──> ISOLATED
```

**Escalation Triggers**:
- Multiple anomalies (≥3 in recent history)
- High average anomaly severity (>0.7)
- Guardian risk assessment changes
- Explicit user request
- Resource limit violations

**Example Escalation Flow**:
```
1. Sandbox created at RESTRICTED level
2. Monitor detects excessive CPU + file operations
3. severity score > 0.7, count >= 3
4. Auto-escalate to SANDBOXED
5. Docker/strict process isolation applied
6. All subprocesses blocked, minimal environment
7. If anomalies continue, escalate to ISOLATED (VM)
```

## Usage Example

### Complete Workflow

```python
from app.sandbox.adaptive import (
    CapabilityGrant,
    AdaptiveSandbox,
    IsolationLevel,
    PathAccessMode,
)
from app.sandbox.core.guardian import Guardian

# 1. Create grant for agent
grant = CapabilityGrant(
    agent_id="build_agent",
    allowed_tools={"python", "git", "pip", "gcc"},
    allowed_paths={
        "/home/user/workspace": PathAccessMode.READ_WRITE,
        "/opt/libs": PathAccessMode.READ_ONLY,
    },
    env_whitelist={"PATH", "HOME", "PYTHONPATH", "LD_LIBRARY_PATH"},
    network_enabled=False,  # No network
    cpu_percent=80.0,
    memory_mb=1024,
    timeout_seconds=1800,  # 30 minutes
    min_isolation_level=IsolationLevel.RESTRICTED.value,
    max_isolation_level=IsolationLevel.SANDBOXED.value,
)

# 2. Initialize sandbox with Guardian
guardian = Guardian()
guardian.approve_agent("build_agent")

sandbox = AdaptiveSandbox(
    agent_id="build_agent",
    grant=grant,
    guardian=guardian,
    isolation_level=IsolationLevel.RESTRICTED,
)

# 3. Initialize (Guardian checkpoint)
success = await sandbox.initialize()
if not success:
    print("Guardian denied sandbox creation")
    return

# 4. Execute commands
result = await sandbox.run_command("python -m pip install -r requirements.txt")
if result[2]:  # error
    suggestions = sandbox.suggest_environment_fix(result[2])
    print(f"Failed: {result[2]}")
    print(f"Suggestions: {suggestions}")
else:
    print(f"Success: {result[0]}")

# 5. Get execution details
history = sandbox.get_execution_history()
monitoring = sandbox.get_monitoring_summary()

for execution in history:
    print(f"Cmd: {execution['command']}")
    print(f"Status: {execution['status']}")
    print(f"Duration: {execution['duration_seconds']}s")

if monitoring:
    print(f"Isolation Level: {monitoring['current_isolation_level']}")
    print(f"Anomalies: {len(monitoring['recent_anomalies'])}")

# 6. Cleanup
await sandbox.cleanup()
```

### Error Handling with Capability Suggestions

```python
output, exit_code, error = await sandbox.run_command("npm install")

if error:
    suggestions = sandbox.suggest_environment_fix(error)
    
    # suggestions might be:
    # ["Missing tool - check allowed_tools: npm"]
    
    # Grant npm and retry
    grant.allowed_tools.add("npm")
    output, exit_code, error = await sandbox.run_command("npm install")
```

## Configuration

### Via Code

All configuration is programmatic:

```python
grant = CapabilityGrant(
    agent_id="agent_1",
    allowed_tools={"python", "git"},
    # ... other settings
)

config = get_isolation_config(IsolationLevel.RESTRICTED)
```

### Environment Variables (optional)

Can override defaults via environment:

```bash
# Resource limits
export SANDBOX_CPU_PERCENT=50
export SANDBOX_MEMORY_MB=256
export SANDBOX_TIMEOUT_SECONDS=600

# Capabilities
export SANDBOX_ALLOWED_TOOLS="python,git,npm"
export SANDBOX_NETWORK_ENABLED="false"
```

## Platform-Specific Behaviors

### Windows

- Uses job objects for process resource limiting
- Sets MSVC_PATH, VS_INSTALLATION environment variables
- Windows-specific syscalls in seccomp rules
- cmd.exe / PowerShell support

### Linux

- Uses cgroups for resource limiting
- Docker containerization for SANDBOXED/ISOLATED levels
- Linux-specific syscalls in seccomp rules (ptrace, mount, etc.)
- Shell-based execution (bash/sh)

## UI Integration

### AdaptiveSandboxMonitorPanel

Display sandbox execution context to users:

```python
# In UI code
monitor_panel = AdaptiveSandboxMonitorPanel()

# Display sandbox environment
monitor_panel.display_sandbox_environment(sandbox.get_environment_summary())

# Record Guardian decision
monitor_panel.display_guardian_decision({
    "operation": "command_execute",
    "approved": True,
    "risk_level": "low",
    "reason": "Command within allowed tools and paths",
})

# Record isolation escalation
monitor_panel.record_isolation_escalation(
    old_level="MONITORED",
    new_level="RESTRICTED",
    reason="Detected excessive file operations (2000/s > 1000/s threshold)",
)
```

**Display Features**:
- Current isolation level with description
- Granted capabilities (tools, paths, network)
- Environment variables in use
- Resource limits vs current usage
- Runtime anomalies with severity scores
- Guardian decision history
- Execution history with status/duration
- Color-coded status indicators

## Testing

Comprehensive test suite in `tests/test_adaptive_sandbox.py`:

```bash
pytest tests/test_adaptive_sandbox.py -v
```

**Test Categories**:
- CapabilityGrant: Creation, validation, expiration, tool/path access
- SandboxBuilder: Environment building for each isolation level, suggestions
- AdaptiveRuntimeMonitor: Metric recording, anomaly detection, escalation
- AdaptiveSandbox: Initialization, command execution, Guardian integration
- IsolationLevels: Configuration, escalation chains, constraint validation

**Key Test Cases**:
- Grant tool/path permissions enforcement
- Environment variable filtering per isolation level
- Resource limit reconciliation
- Anomaly detection (CPU spike, memory spike, subprocess explosion, etc.)
- Isolation level escalation under simulated load
- Guardian checkpoint validation
- Capability suggestions for failed commands

## Logging

Full execution context logged:

```
INFO: Created adaptive sandbox adaptive_a1b2c3d4 for agent build_agent at isolation level RESTRICTED
DEBUG: Running Guardian checkpoint for sandbox adaptive_a1b2c3d4
INFO: Guardian approved sandbox: Operation approved (low risk)
INFO: Initialized sandbox adaptive_a1b2c3d4
INFO: Executing command in sandbox adaptive_a1b2c3d4 (execution=exec123): python -m pip install -r requirements.txt
DEBUG: Guardian approved command execution: Operation approved (low risk)
INFO: Command execution completed (execution=exec123): exit_code=0, output_length=2547
WARNING: Detected anomaly: cpu_spike - CPU usage 92.5% exceeds threshold 80.0%
WARNING: Recommending isolation escalation from MONITORED to RESTRICTED (violations: 3, severity: 0.75)
INFO: Escalating isolation level from MONITORED to RESTRICTED
```

## Performance Considerations

- **Metric Recording**: O(1) per sample, stored in circular buffer
- **Anomaly Detection**: O(n) where n = anomaly types (constant)
- **Escalation Decision**: O(m) where m = recent anomalies (≤10)
- **Environment Building**: O(k) where k = environment variables
- **Guardian Checkpoint**: Async, depends on validation rules

## Security Considerations

1. **Principle of Least Privilege**: Grants specify only what's needed
2. **Whitelisting**: Default deny, only allowed tools/paths work
3. **Environment Isolation**: Host environment filtered, not inherited
4. **Resource Enforcement**: Hard limits via cgroups/job objects
5. **Audit Trail**: All decisions and anomalies logged
6. **Escalation**: Automatic protection if anomalies detected
7. **Guardian Integration**: All operations validated before execution

## Future Enhancements

1. **Persistent Grants**: Store grants in database with versioning
2. **Grant Templates**: Pre-configured grant templates per agent role
3. **Anomaly ML**: Machine learning for anomaly detection patterns
4. **Distributed Monitoring**: Metrics aggregation across multiple sandboxes
5. **API Rate Limiting**: Per-tool rate limits on API calls
6. **Capability Requests**: UI for agents to request new capabilities
7. **Policy Framework**: YAML-based policy definitions
8. **Integration**: Connect to compliance frameworks (audit, compliance)

## Troubleshooting

### Command Fails with "Permission Denied"

**Causes**:
- Path not in allowed_paths or in blocked_paths
- File accessed in read-write when granted read-only
- Isolation level too strict

**Solution**:
```python
# Check what's allowed
grant.get_allowed_access_for_path("/path/to/file")

# Add path if needed
grant.allowed_paths["/path/to/file"] = PathAccessMode.READ_WRITE

# Or lower isolation level
sandbox.isolation_level = IsolationLevel.MONITORED
```

### Command Not Found

**Causes**:
- Tool not in allowed_tools

**Solution**:
```python
# Use suggestion
suggestions = sandbox.suggest_environment_fix(error)

# Add tool
grant.allowed_tools.add("tool_name")
```

### Excessive Anomalies / Escalation

**Causes**:
- Grant limits too strict relative to command needs
- Background processes consuming resources
- Actual malicious/problematic code

**Solution**:
```python
# Monitor anomalies
monitoring = sandbox.get_monitoring_summary()
for anomaly in monitoring['recent_anomalies']:
    print(f"{anomaly['type']}: {anomaly['reason']}")

# Adjust limits if legitimate
grant.cpu_percent = 100.0
grant.memory_mb = 2048
```

## References

- **Guardian**: `app/sandbox/core/guardian.py`
- **Sandbox Manager**: `app/sandbox/core/manager.py`
- **Resource Monitor**: `app/sandbox/core/monitor.py`
- **UI Panel**: `app/ui/panels/adaptive_sandbox_monitor.py`
- **Tests**: `tests/test_adaptive_sandbox.py`
