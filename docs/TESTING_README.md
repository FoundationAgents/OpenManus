# End-to-End Testing Framework

Comprehensive automated and manual testing framework for system validation.

## Quick Start

### Setup

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Or for development (includes linting and type checking)
pip install -e . && pip install -r requirements-test.txt
```

### Run Tests

```bash
# All tests with coverage
pytest tests/ -v --cov=app

# E2E tests only
pytest tests/test_e2e_workflows.py -v

# Smoke tests only
pytest tests/test_smoke_tests.py -v

# Integration tests only
pytest tests/test_integration_e2e.py -v

# Specific test class
pytest tests/test_e2e_workflows.py::TestWorkflowWithGuardianApprovals -v

# Specific test
pytest tests/test_e2e_workflows.py::TestWorkflowWithGuardianApprovals::test_workflow_requires_guardian_approval -v
```

### Test Markers

```bash
# Run tests by marker
pytest -m e2e -v           # E2E tests
pytest -m smoke -v         # Smoke tests
pytest -m integration -v   # Integration tests
pytest -m asyncio -v       # Async tests
pytest -m qt -v            # Qt UI tests

# Exclude UI tests (for headless environments)
pytest -m "not qt" -v
```

## Test Structure

### Test Files

| File | Purpose | Count | Markers |
|------|---------|-------|---------|
| `test_e2e_workflows.py` | Main E2E workflows | 40+ | `@pytest.mark.e2e` |
| `test_smoke_tests.py` | Quick validation | 25+ | `@pytest.mark.smoke` |
| `test_integration_e2e.py` | Cross-module tests | 30+ | `@pytest.mark.integration` |
| `conftest.py` | Shared fixtures | - | - |

### Test Classes

#### E2E Workflows
- **TestWorkflowWithGuardianApprovals**: Guardian security integration
- **TestSandboxedCodeExecution**: Sandbox isolation and execution
- **TestVersionRollbackInIDE**: Version management and rollback
- **TestMemoryRetrievalAssistingAgent**: Memory/RAG system
- **TestAgentReplacementAfterFailures**: Agent failover
- **TestEndToEndWorkflowIntegration**: Multi-component flows

#### Smoke Tests
- **TestMCPToolAccess**: MCP tool availability
- **TestNetworkClientOperations**: Network and caching
- **TestBackupRestoreCycle**: Backup operations
- **TestCriticalPathSmoke**: System readiness

#### Integration Tests
- **TestGuardianSecurityIntegration**: Guardian with other components
- **TestMemoryAgentIntegration**: Memory and agents
- **TestSandboxVersionIntegration**: Sandbox and versioning
- **TestNetworkCachingIntegration**: Network operations
- **TestBackupRecoveryIntegration**: Recovery scenarios
- **TestAgentFailoverIntegration**: Failover logic
- **TestComplexMultiComponentScenarios**: Complex workflows
- **TestDisasterRecoveryScenario**: Recovery after failures

## Fixtures

### Database
- `temp_db_path`: Temporary SQLite path
- `temp_db`: Pre-initialized SQLite database
- `async_db`: Async SQLite connection

### Services
- `mock_guardian`: Guardian security service
- `mock_sandbox`: Sandbox environment
- `mock_network_client`: Network client with caching
- `mock_memory_store`: Memory/RAG storage
- `mock_version_manager`: Version management
- `mock_backup_manager`: Backup system
- `mock_agent`: Single agent mock
- `mock_agent_pool`: Agent pool management
- `mock_mcp_tools`: MCP tools
- `mock_workflow_executor`: Workflow execution

### External Services
- `mock_http_server`: Mock HTTP server (returns on port)
- `mock_websocket_server`: Mock WebSocket server

### Data
- `sample_workflow`: Sample workflow definition
- `sample_code_snippet`: Code samples in multiple languages
- `test_config`: Test configuration
- `temp_workspace`: Temporary workspace directory

## Coverage

### Target Coverage

- Overall: > 80%
- Critical paths: > 90%
- Guardian/Security: > 95%
- UI components: > 85%

### Generate Coverage Report

```bash
# Terminal report
pytest tests/ --cov=app --cov-report=term-missing

# HTML report
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html

# XML report (for CI)
pytest tests/ --cov=app --cov-report=xml
```

## Continuous Integration

### GitHub Actions

Workflows in `.github/workflows/`:

1. **e2e-testing.yml** (Main E2E CI):
   - E2E tests (Python 3.11, 3.12)
   - Smoke tests
   - Integration tests
   - Coverage reporting
   - UI tests with xvfb
   - Security validation
   - Performance benchmarks
   - Backup/recovery tests

2. **ci-cd.yml** (Main CI/CD):
   - Unit tests
   - Linting and formatting
   - Type checking
   - Security scanning
   - Docker build

### Local CI Simulation

```bash
# Use tox for multi-environment testing
tox

# Test specific environment
tox -e py312
tox -e lint
tox -e type
tox -e coverage
```

## Manual Testing

### Guardian Security Testing

1. **Verify Guardian blocks dangerous commands**
   ```python
   # In pytest
   pytest tests/test_guardian_validation.py -v
   ```

2. **Test approval workflow**
   - Submit command for approval
   - Check approval notification
   - Grant/deny approval
   - Verify execution/blocking

3. **Audit trail verification**
   - Check all actions logged
   - Verify timestamps
   - Review decision reasons

### UI Testing

1. **Application startup**
   ```bash
   pytest tests/ -m qt -v
   ```

2. **Manual UI interaction**
   - Start application: `python main_gui.py`
   - Test editor functionality
   - Test workflow execution
   - Test settings

### Sandbox Testing

1. **Code execution**
   ```bash
   pytest tests/test_e2e_workflows.py::TestSandboxedCodeExecution -v
   ```

2. **Isolation verification**
   - Attempt filesystem access
   - Attempt network access
   - Attempt process killing

### Memory/RAG Testing

1. **Data storage and retrieval**
   ```bash
   pytest tests/test_e2e_workflows.py::TestMemoryRetrievalAssistingAgent -v
   ```

2. **Search functionality**
   - Store multiple items
   - Search with various queries
   - Verify ranking

### Backup/Recovery Testing

1. **Backup creation**
   ```bash
   pytest tests/test_smoke_tests.py::TestBackupRestoreCycle -v
   ```

2. **Recovery verification**
   - Create backup
   - Delete data
   - Restore from backup
   - Verify data integrity

## Performance Benchmarks

### Expected Performance

| Operation | Target | Acceptable |
|-----------|--------|-----------|
| System init | < 5s | < 7s |
| Workflow exec | < 2s | < 3s |
| Code execution | < 1s | < 2s |
| Memory retrieval | < 0.5s | < 1s |
| Backup creation | < 5s | < 10s |
| Agent failover | < 2s | < 3s |

### Run Performance Tests

```bash
# Using pytest-benchmark
pytest tests/ -v --benchmark-only

# Using tox
tox -e benchmark
```

## Troubleshooting

### Common Issues

#### PyQt6 Headless Testing

```bash
# Set offscreen platform
export QT_QPA_PLATFORM=offscreen

# Or in GitHub Actions (already set in workflow)
env:
  QT_QPA_PLATFORM: offscreen
```

#### Async Test Errors

```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Configure asyncio mode in pytest.ini
[pytest]
asyncio_mode = auto
```

#### Database Errors

```bash
# Use temp_db fixture for isolation
# Clean up temp files
rm -rf /tmp/pytest-*
```

#### Timeout Issues

```bash
# Increase timeout
pytest tests/ --timeout=600

# Or configure in pytest.ini
[pytest]
timeout = 600
```

#### Import Errors

```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="$PWD:$PYTHONPATH"

# Or install in development mode
pip install -e .
```

## Best Practices

### Writing Tests

1. **Use descriptive names**
   ```python
   def test_workflow_blocks_on_guardian_denial():
       # Clear name describes what's being tested
   ```

2. **Use fixtures for setup/teardown**
   ```python
   def test_something(mock_guardian, temp_db):
       # Fixtures handle setup and cleanup
   ```

3. **Group related tests in classes**
   ```python
   class TestGuardianIntegration:
       def test_approve(self): ...
       def test_deny(self): ...
   ```

4. **Use appropriate markers**
   ```python
   @pytest.mark.e2e
   @pytest.mark.asyncio
   async def test_workflow():
   ```

5. **Add docstrings**
   ```python
   def test_something():
       """Test that something works correctly."""
   ```

### Test Organization

```
tests/
├── __init__.py
├── conftest.py                  # Shared fixtures
├── test_e2e_workflows.py        # Main E2E tests
├── test_smoke_tests.py          # Quick validation
├── test_integration_e2e.py      # Cross-module tests
├── test_guardian.py             # Guardian-specific
├── test_backup_manager.py       # Backup-specific
└── ...other test files...
```

## Contributing

When adding new tests:

1. Follow existing patterns
2. Use provided fixtures
3. Add appropriate markers
4. Include docstrings
5. Aim for > 80% coverage
6. Run tests locally before submitting
7. Update this README if adding new categories

## Performance Optimization

### Parallel Testing

```bash
# Use pytest-xdist for parallel execution
pytest tests/ -n auto
pytest tests/ -n 4
```

### Fixture Scope Optimization

```python
# Use appropriate scope to minimize setup
@pytest.fixture(scope="module")  # Reuse across module
def expensive_fixture():
    ...

@pytest.fixture(scope="function")  # Fresh for each test
def database():
    ...
```

### Test Filtering

```bash
# Skip slow tests
pytest tests/ -m "not slow" -v

# Run only fast tests
pytest tests/ -m "smoke" -v
```

## Debugging

### Verbose Output

```bash
pytest tests/ -vv          # Very verbose
pytest tests/ -vv -s       # Include print statements
pytest tests/ -vv --tb=long # Long traceback
```

### Stop on First Failure

```bash
pytest tests/ -x           # Stop on first failure
pytest tests/ -x --ff      # Run failed tests first
```

### Interactive Debugging

```bash
# Use pdb
pytest tests/ --pdb

# Use pdb++ (install: pip install pdbpp)
pytest tests/ --pdbcls=IPython.terminal.debugger:TerminalPdb
```

## Documentation

- [E2E Testing Guide](TESTING_E2E_GUIDE.md): Detailed testing guide
- [pytest documentation](https://docs.pytest.org)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io)
- [pytest-qt](https://pytest-qt.readthedocs.io)

## Contact

For questions about testing:
1. Check existing test examples
2. Refer to TESTING_E2E_GUIDE.md
3. Review conftest.py fixtures
4. Check CI/CD workflows for examples
