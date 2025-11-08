# Dynamic Permission & Capability System

## Overview

The Dynamic Permission & Capability System provides intelligent, risk-based capability granting for agents. Rather than static sandbox configurations, agents dynamically request specific capabilities, and the Guardian system evaluates the risk asynchronously. Users can override decisions, and the system maintains comprehensive audit trails with TTL-based caching and real-time revocation support.

## Architecture

### Core Components

1. **CapabilityRequest**: Agent requests specific capabilities
   - Tools needed (e.g., compiler, debugger, CUDA)
   - Environment variables
   - File system paths
   - Network access requirements
   - Resource limits and timeout
   - Command intent and task description for context

2. **DynamicPermissionManager**: Central decision engine
   - Evaluates risk asynchronously
   - Manages TTL-based caching
   - Handles revocation
   - Maintains audit trails
   - Manages grant persistence

3. **Guardian Risk Assessment**: Multi-layered evaluation
   - Tool-agent type compatibility
   - Historical trust scores
   - Suspicious pattern detection
   - Command intent analysis
   - Resource consumption validation
   - Path access security

4. **Decision Types**:
   - **AUTO_GRANT**: Low-risk requests auto-approved, cached for TTL
   - **REQUIRE_CONFIRMATION**: Medium-risk requests, prompt user with risk summary
   - **AUTO_DENY**: High/critical-risk requests, rejected with audit logging

### Database Schema

#### permissions_grants table
Stores issued capability grants with expiry and revocation tracking:

```sql
CREATE TABLE permissions_grants (
    id INTEGER PRIMARY KEY,
    grant_id TEXT UNIQUE NOT NULL,
    request_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    granted_tools TEXT,          -- JSON array
    network_allowed BOOLEAN,
    ttl_seconds INTEGER,
    expires_at TEXT,             -- ISO format
    revoked_at TEXT,
    revoked_reason TEXT,
    revocation_token TEXT,
    audit_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### permissions_audit table
Comprehensive audit trail of all permission events:

```sql
CREATE TABLE permissions_audit (
    id INTEGER PRIMARY KEY,
    audit_id TEXT UNIQUE NOT NULL,
    action TEXT NOT NULL,        -- request, grant, deny, revoke, confirm
    agent_id TEXT NOT NULL,
    request_id TEXT,
    metadata TEXT,               -- JSON with context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Decision Logic

### Risk Assessment Factors

1. **Tool Compatibility Matrix**
   - Matches tool names to agent types
   - GameDevAgent: compiler, debugger, cuda, opengl
   - NetworkAgent: network_socket, http_client, dns
   - SWEAgent: compiler, debugger, shell, docker, database
   - SecurityAgent: ida_pro, radare2, kernel_debug
   - GenericAgent: most tools except specialized ones

2. **Historical Context**
   - Queries audit trail for agent success rates
   - Calculates trust score: 0.0-1.0
   - New agents default to 0.5 (neutral)
   - Caches trust scores in memory (per session)

3. **Capability Combinations**
   - Detects suspicious patterns:
     - `{delete, system32_access, powershell}` → HIGH RISK
     - `{network, shell, system_access}` → HIGH RISK
     - `{root_access, network, kernel_debug}` → CRITICAL
     - `{db_access, shell, file_delete}` → HIGH RISK

4. **Command Intent Analysis**
   - Keyword matching: rm -rf, format, dd, mkfs, destroy, delete, drop
   - Escalating risk scores based on dangerous keywords
   - Context clues: "delete", "format", "remove"

5. **Path Risk Detection**
   - Blocks access to sensitive paths: /etc/shadow, /root, Windows\System32
   - Warns on system configuration directories
   - Tracks requested paths in audit log

6. **Resource Validation**
   - Default limits by agent type
   - GameDevAgent: 4GB RAM, 75% CPU, 5min timeout
   - NetworkAgent: 100Mbps bandwidth, 1min timeout
   - SWEAgent: 2GB RAM, 50% CPU, 10min timeout
   - GenericAgent: 1GB RAM, 30% CPU, 5min timeout
   - Rejects unreasonable requests (>16GB memory)

### Risk Score Calculation

```
Final Risk = Σ(compatibility issues + trust penalties + pattern risks + 
             intent signals + path risks + resource issues)

LOW        (0.0-0.2)   → AUTO_GRANT
MEDIUM     (0.2-0.5)   → REQUIRE_CONFIRMATION
HIGH       (0.5-0.7)   → AUTO_DENY
CRITICAL   (0.7-1.0)   → AUTO_DENY
```

## Usage Examples

### Basic Capability Request

```python
from app.security.permissions import (
    CapabilityRequest,
    ResourceLimits,
    get_permission_manager,
)

manager = get_permission_manager()

request = CapabilityRequest(
    agent_id="dev_agent_1",
    agent_type="SWEAgent",
    tools=["compiler", "debugger"],
    env_vars={"PATH": "/usr/bin", "CC": "gcc"},
    paths=["/home/user/project/src"],
    network=False,
    command="gcc -c src/main.c",
    task_description="Compile C source code",
    resource_limits=ResourceLimits(
        max_memory_mb=512,
        max_cpu_percent=50,
        timeout_seconds=300,
    ),
)

decision = await manager.request_capability(request)

if decision.decision_type == DecisionType.AUTO_GRANT:
    grant = decision.grant
    print(f"Granted tools: {grant.granted_tools}")
    print(f"Expires at: {grant.expires_at}")
    print(f"Revocation token: {grant.revocation_token}")
```

### Handling Confirmation Requests

```python
if decision.decision_type == DecisionType.REQUIRE_CONFIRMATION:
    details = decision.confirmation_required
    print(f"Agent: {details['agent_id']}")
    print(f"Requested tools: {details['requested_tools']}")
    print(f"Risk reasons: {details['risk_reasons']}")
    
    # User approves/denies via UI
    user_approved = await user_confirmation_dialog(details)
    
    if user_approved:
        # Create grant from confirmation
        grant = await manager.confirm_request(details)
    else:
        # Log denial and notify agent
        await manager.deny_confirmation(details)
```

### Grant Revocation

```python
# Revoke a grant
success = await manager.revoke_grant(
    grant_id=grant.grant_id,
    revocation_token=grant.revocation_token,
    reason="Session terminated"
)

if success:
    print("Grant revoked successfully")
```

### Query Active Grants

```python
# Get all active grants for an agent
active_grants = await manager.get_active_grants(agent_id="dev_agent_1")

for grant in active_grants:
    print(f"Grant {grant.grant_id}:")
    print(f"  Tools: {grant.granted_tools}")
    print(f"  Network: {grant.network_allowed}")
    print(f"  Expires: {grant.expires_at}")
```

### Audit Trail

```python
# Query audit log
audit_logs = await manager.get_audit_log(
    agent_id="dev_agent_1",
    action="grant",  # Optional filter
    limit=50,
)

for entry in audit_logs:
    print(f"{entry['created_at']}: {entry['action']}")
    print(f"  Metadata: {entry['metadata']}")
```

## Caching Layer

### How Caching Works

1. **In-Memory Cache**: Fast access via request ID
2. **TTL-Based Expiry**: Each grant has configurable TTL (default 1 hour)
3. **Expiry Check**: Before returning cached grant, verify not expired
4. **Cache Invalidation**: On revocation, remove from cache
5. **Database Persistence**: All grants written to database regardless of cache

### Cache Benefits

- Avoids redundant risk assessment for identical requests
- Improves response time for repeated patterns
- Maintains consistency with database (fallback source of truth)

## Integration Points

### Agent Base Class Integration

```python
# In agent execution
request = CapabilityRequest(
    agent_id=self.name,
    agent_type=self.__class__.__name__,
    tools=self.required_tools,
    paths=self.file_access_paths,
    network=self.requires_network,
    command=self.current_command,
    task_description=self.task,
)

decision = await manager.request_capability(request)

if decision.decision_type == DecisionType.AUTO_GRANT:
    # Execute with granted capabilities
    self.capabilities = decision.grant
elif decision.decision_type == DecisionType.AUTO_DENY:
    # Abort execution
    raise CapabilityDenied(decision.deny.denied_reason)
else:  # REQUIRE_CONFIRMATION
    # UI prompts user
    await self.wait_for_user_confirmation()
```

### UI Agent Monitor Integration

```python
# Show current grants
agent_grants = await manager.get_active_grants(agent_id)
ui.update_grants_panel(agent_grants)

# One-click revocation
async def on_revoke_clicked(grant_id):
    success = await manager.revoke_grant(grant_id, token)
    if success:
        ui.show_notification("Grant revoked")
        ui.refresh_grants_panel()

# Show pending confirmations
pending = await manager.get_pending_confirmations()
ui.show_confirmation_dialog(pending)
```

## Security Considerations

### Token-Based Revocation

- Each grant has a unique `revocation_token`
- Required for revocation to prevent unauthorized cancellation
- Tokens not exposed to agents, only to UI/users

### Audit Logging

- All actions logged with timestamps and context
- Metadata includes decision rationale and risk assessment
- Enable security investigation and compliance auditing

### Risk Assessment Integrity

- Multi-factor evaluation prevents false positives/negatives
- Pattern matching catches complex attack scenarios
- Historical context prevents gaming the system
- Resource validation prevents resource exhaustion attacks

## Default Resource Limits by Agent Type

| Agent Type | Memory | CPU | Timeout | Bandwidth |
|---|---|---|---|---|
| GameDevAgent | 4096 MB | 75% | 300s | - |
| NetworkAgent | - | - | 60s | 100 Mbps |
| SWEAgent | 2048 MB | 50% | 600s | - |
| SecurityAgent | 2048 MB | 60% | 120s | - |
| GenericAgent | 1024 MB | 30% | 300s | - |

## Testing

### Test Coverage

- Tool compatibility matrix validation
- Risk assessment across multiple scenarios
- Cache hit/expiry behavior
- Revocation with token validation
- Audit trail logging
- Resource limit enforcement
- Trust score calculation
- Suspicious pattern detection

### Running Tests

```bash
python -m pytest tests/test_permissions.py -v

# Run specific test class
python -m pytest tests/test_permissions.py::TestToolCompatibility -v

# Run with coverage
python -m pytest tests/test_permissions.py --cov=app.security --cov-report=html
```

## Configuration

The permission system can be configured via environment variables:

```bash
# Default grant TTL in seconds
PERMISSION_GRANT_TTL=3600

# Enable debug logging
PERMISSION_DEBUG=true

# Max audit log retention (days)
PERMISSION_AUDIT_RETENTION_DAYS=90
```

## Future Enhancements

1. **ML-Based Risk Scoring**: Train model on audit logs to refine risk assessment
2. **Capability Delegation**: Allow agents to delegate capabilities to sub-agents
3. **Dynamic Policy Enforcement**: Policies that adjust based on system state
4. **Capability Expiry Policies**: Auto-revoke if CPU hits threshold (e.g., 90%)
5. **Capability Marketplace**: Share pre-configured capability sets
6. **Performance Analytics**: Track capability usage patterns
7. **Integration with LSP**: Real-time capability discovery for IDE integration

## Troubleshooting

### Grant Denied Unexpectedly

1. Check audit log for denial reason
2. Review agent trust score history
3. Verify tool compatibility matrix
4. Check for suspicious pattern matches

### Cache Issues

1. Verify TTL values in config
2. Check database for revocation status
3. Review in-memory cache state

### Performance

1. Monitor audit log size (add retention policy)
2. Index frequently queried fields
3. Consider separate audit log database

## Related Documentation

- [Guardian Security System](./app/network/guardian.py)
- [Database Schema](./app/database/migration_manager.py)
- [Agent Base Class](./app/agent/base.py)
- [Audit System](./app/database/database_service.py)
