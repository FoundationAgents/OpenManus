# End-to-End Testing Guide

Comprehensive guide for automated and manual testing of the integrated system.

## Overview

This testing framework validates workflows across:
- **UI interactions** with PyQt6
- **Agent workflows** with async orchestration
- **Security** with Guardian approvals
- **Memory/RAG** systems
- **Sandbox isolation**
- **Version management**
- **Backup/recovery**

## Quick Start

### Run All Tests

```bash
# Run all E2E tests
pytest tests/test_e2e_workflows.py -v

# Run all smoke tests
pytest tests/test_smoke_tests.py -v

# Run integration tests
pytest tests/test_integration_e2e.py -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test class
pytest tests/test_e2e_workflows.py::TestWorkflowWithGuardianApprovals -v

# Run specific test
pytest tests/test_e2e_workflows.py::TestWorkflowWithGuardianApprovals::test_workflow_requires_guardian_approval -v
```

### Run Tests with Markers

```bash
# Run only E2E tests
pytest -m e2e -v

# Run only smoke tests
pytest -m smoke -v

# Run only async tests
pytest -m asyncio -v

# Exclude UI tests (useful in headless environments)
pytest -m "not qt" -v
```

## Test Structure

### Conftest Fixtures

Located in `tests/conftest.py`, provides:

#### Database Fixtures
- `temp_db_path`: Temporary SQLite database path
- `temp_db`: Pre-initialized SQLite database
- `async_db`: Async SQLite connection

#### Service Mocks
- `mock_guardian`: Guardian security service
- `mock_sandbox`: Sandbox execution environment
- `mock_network_client`: Network client with caching
- `mock_memory_store`: Memory/RAG storage
- `mock_version_manager`: Version management
- `mock_backup_manager`: Backup and recovery
- `mock_agent_pool`: Agent pool management
- `mock_mcp_tools`: MCP tool access

#### External Services
- `mock_http_server`: Mock HTTP server
- `mock_websocket_server`: Mock WebSocket echo server
- `mock_faiss_store`: FAISS vector store

#### Utilities
- `sample_workflow`: Sample workflow definition
- `sample_code_snippet`: Code snippets in multiple languages
- `test_config`: Test configuration
- `temp_workspace`: Temporary workspace directory

### Test Files

#### `test_e2e_workflows.py` (Main E2E Tests)

Classes:
- `TestWorkflowWithGuardianApprovals`: Guardian integration
- `TestSandboxedCodeExecution`: Sandbox operations
- `TestVersionRollbackInIDE`: Version management
- `TestMemoryRetrievalAssistingAgent`: Memory/RAG
- `TestAgentReplacementAfterFailures`: Agent failover
- `TestEndToEndWorkflowIntegration`: Multi-component flows

#### `test_smoke_tests.py` (Quick Validation)

Classes:
- `TestMCPToolAccess`: MCP tool availability
- `TestNetworkClientOperations`: Network and caching
- `TestBackupRestoreCycle`: Backup operations
- `TestCriticalPathSmoke`: System readiness

#### `test_integration_e2e.py` (Cross-Module Tests)

Classes:
- `TestGuardianSecurityIntegration`: Guardian interactions
- `TestMemoryAgentIntegration`: Memory and agents
- `TestSandboxVersionIntegration`: Sandbox and versioning
- `TestNetworkCachingIntegration`: Network operations
- `TestBackupRecoveryIntegration`: Recovery scenarios
- `TestAgentFailoverIntegration`: Failover logic
- `TestComplexMultiComponentScenarios`: Complex workflows
- `TestDisasterRecoveryScenario`: Recovery after failures

## Manual Testing Checklists

### Guardian Security Testing

**High Priority**: Ensures malicious commands are blocked

1. **Setup**
   - [ ] Guardian service initialized
   - [ ] Approval policies configured
   - [ ] Audit logging enabled

2. **Safe Command Testing**
   - [ ] Safe commands auto-approved (e.g., `ls -la`)
   - [ ] Whitelisted commands execute immediately
   - [ ] No approval required for low-risk actions

3. **Dangerous Command Testing**
   - [ ] Deletion commands require approval
   - [ ] System commands require approval
   - [ ] Network modification commands blocked

4. **Approval Workflow**
   - [ ] Approval request created with details
   - [ ] Notification sent for approval needed
   - [ ] Approval can be granted with reason
   - [ ] Rejection prevents execution
   - [ ] Audit trail records all decisions

5. **Edge Cases**
   - [ ] Timeout after 24 hours revokes request
   - [ ] Reusing denied request fails
   - [ ] Multiple approval levels work correctly

### UI Interaction Testing

**High Priority**: Tests PyQt6 GUI functionality

1. **Application Startup**
   - [ ] Main window loads without errors
   - [ ] All UI components render
   - [ ] Menu bar functional
   - [ ] Status bar displays system status

2. **Code Editor**
   - [ ] Syntax highlighting works
   - [ ] Code completion functions
   - [ ] Keyboard shortcuts work (Ctrl+S, Ctrl+Z)
   - [ ] Line numbers display correctly
   - [ ] Code folding works

3. **Workflow Execution**
   - [ ] Workflow can be started from UI
   - [ ] Progress displayed during execution
   - [ ] Results shown in output panel
   - [ ] Execution can be paused/resumed
   - [ ] Execution can be cancelled

4. **Version Management**
   - [ ] Version history displayed
   - [ ] Rollback works and updates editor
   - [ ] Diff view shows changes
   - [ ] Version annotations displayed

5. **Settings and Preferences**
   - [ ] Theme can be changed
   - [ ] Font size adjustable
   - [ ] Preferences persist across sessions
   - [ ] Reset to defaults works

### Sandbox Isolation Testing

**High Priority**: Validates execution isolation

1. **Code Execution**
   - [ ] Python scripts execute correctly
   - [ ] JavaScript code runs (if Node available)
   - [ ] Output captured properly
   - [ ] Exit codes correct

2. **Resource Limits**
   - [ ] Timeout enforced (infinite loops)
   - [ ] Memory limits enforced
   - [ ] CPU limits enforced
   - [ ] Disk write limits enforced

3. **Isolation Verification**
   - [ ] Code cannot access host filesystem
   - [ ] Code cannot make unrestricted network calls
   - [ ] Code cannot kill other processes
   - [ ] Code cannot access host environment variables

4. **Error Handling**
   - [ ] Syntax errors reported clearly
   - [ ] Runtime errors reported with line numbers
   - [ ] Timeout errors reported
   - [ ] Resource exhaustion handled gracefully

### Memory/RAG System Testing

**Medium Priority**: Tests knowledge persistence

1. **Storage**
   - [ ] Data stored successfully
   - [ ] Large datasets handled
   - [ ] Duplicates handled correctly
   - [ ] Data compression works (if enabled)

2. **Retrieval**
   - [ ] Exact key lookup works
   - [ ] Semantic search functions
   - [ ] Similarity ranking correct
   - [ ] Pagination works

3. **Agent Assistance**
   - [ ] Agent can access relevant memories
   - [ ] Agent uses memories in decisions
   - [ ] Memory improves accuracy over time
   - [ ] Agent can learn new patterns

### Backup and Recovery Testing

**Medium Priority**: Ensures data safety

1. **Backup Creation**
   - [ ] Backups created on schedule
   - [ ] Manual backup trigger works
   - [ ] Backup size reasonable
   - [ ] Backup encryption verified

2. **Backup Verification**
   - [ ] Backup integrity checked
   - [ ] Backup data valid
   - [ ] Backup can be listed
   - [ ] Backup metadata correct

3. **Recovery**
   - [ ] Restore from recent backup
   - [ ] Restore from old backup
   - [ ] Data restored correctly
   - [ ] No data corruption

4. **Disaster Recovery**
   - [ ] Multiple backups available
   - [ ] Cross-region backups (if applicable)
   - [ ] Recovery time acceptable
   - [ ] Recovery successful under load

### Agent Failover Testing

**Medium Priority**: Validates agent reliability

1. **Health Monitoring**
   - [ ] Unhealthy agents detected quickly
   - [ ] Health status visible in UI
   - [ ] Metrics accurate
   - [ ] Alerts triggered appropriately

2. **Failover Mechanism**
   - [ ] Failed agent removed from pool
   - [ ] Tasks reassigned to healthy agent
   - [ ] Failover completes without data loss
   - [ ] New agent takes over seamlessly

3. **Agent Restart**
   - [ ] Failed agent can be restarted
   - [ ] Restarted agent rejoins pool
   - [ ] Performance metrics reset
   - [ ] Previous state recovered if available

4. **Load Balancing**
   - [ ] Tasks distributed fairly
   - [ ] No single agent overloaded
   - [ ] Idle time minimized
   - [ ] Throughput optimal

## Performance Benchmarks

Target performance metrics:

```
Operation                  Target Time    Acceptable Range
────────────────────────────────────────────────────────
System Initialization      < 5.0s         < 7.0s
Workflow Execution         < 2.0s         < 3.0s
Code Execution (sandbox)   < 1.0s         < 2.0s
Memory Retrieval          < 0.5s         < 1.0s
Backup Creation           < 5.0s         < 10.0s
Agent Failover            < 2.0s         < 3.0s
```

## Continuous Integration

CI/CD pipeline runs:

1. **Unit Tests**: Full test suite with coverage > 80%
2. **Linting**: Code style validation (black, isort, flake8)
3. **Type Checking**: mypy static analysis
4. **Security Scan**: Vulnerability detection (trivy)
5. **Performance**: Benchmark comparison
6. **Coverage**: Code coverage reporting

### GitHub Actions Workflow

Located in `.github/workflows/ci-cd.yml`

Runs on:
- Every push to main branch
- Every pull request
- Scheduled daily

Steps:
1. Install dependencies
2. Run linting and formatting checks
3. Run type checking
4. Execute test suite with coverage
5. Run integration tests
6. Security scanning
7. Performance benchmarks
8. Upload coverage reports

## Sample Test Datasets

### Knowledge Graph Sample Data

```python
sample_kg_data = {
    "entities": [
        {"id": "entity_1", "label": "Python", "type": "ProgrammingLanguage"},
        {"id": "entity_2", "label": "Database", "type": "Technology"},
    ],
    "relations": [
        {"source": "entity_1", "target": "entity_2", "type": "uses"}
    ]
}
```

### Workflow Sample Data

```python
sample_workflow = {
    "id": "wf_001",
    "stages": [
        {
            "id": "stage_1",
            "tasks": [
                {"id": "task_1", "action": "analyze", "requires_approval": False}
            ]
        },
        {
            "id": "stage_2",
            "tasks": [
                {"id": "task_2", "action": "execute", "requires_approval": True}
            ]
        }
    ]
}
```

### Code Sample Data

```python
sample_code = {
    "python": """
def analyze_data(data):
    result = {}
    for item in data:
        result[item] = len(item)
    return result
""",
    "bash": """
#!/bin/bash
echo "Processing files..."
ls -la
"""
}
```

## Troubleshooting

### Common Issues

#### Tests Timeout
- Check mock service implementations
- Verify async context managers
- Increase timeout for slow systems

#### Database Errors
- Ensure temp_db fixture is used
- Check for table conflicts
- Verify SQL syntax

#### Missing Dependencies
- Run `pip install -r requirements.txt`
- Install test dependencies: `pytest pytest-asyncio pytest-qt pytest-cov`
- For UI tests: ensure PyQt6 installed

#### Memory Issues
- Limit number of parallel tests: `pytest -n 2`
- Clear FAISS index: `faiss_index_path.cleanup()`
- Reduce dataset sizes

## Best Practices

1. **Isolation**: Each test should be independent
2. **Fixtures**: Use fixtures for setup/teardown
3. **Assertions**: Use meaningful assertion messages
4. **Naming**: Test names should describe what they test
5. **Markers**: Use appropriate markers for test categorization
6. **Documentation**: Add docstrings to complex tests
7. **Cleanup**: Always cleanup resources
8. **Mocking**: Mock external services
9. **Async**: Use @pytest.mark.asyncio for async code
10. **Coverage**: Aim for > 80% code coverage

## Contributing

When adding new tests:

1. Follow existing test structure
2. Use provided fixtures from conftest
3. Add appropriate markers
4. Include docstrings
5. Run tests locally before submitting
6. Ensure all tests pass in CI
7. Update this guide if adding new test categories
