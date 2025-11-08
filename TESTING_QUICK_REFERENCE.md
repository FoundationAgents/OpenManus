# Testing Quick Reference Card

## One-Minute Setup

```bash
# Install dependencies
pip install -r requirements-test.txt

# Run all tests
pytest tests/ -v

# Run E2E tests
pytest tests/test_e2e_workflows.py -v
```

## Common Commands

| Command | Purpose |
|---------|---------|
| `pytest tests/ -v` | Run all tests with verbose output |
| `pytest tests/ -m e2e -v` | Run only E2E tests |
| `pytest tests/ -m smoke -v` | Run only smoke tests |
| `pytest tests/ --cov=app -v` | Run with coverage report |
| `pytest tests/ -x` | Stop on first failure |
| `pytest tests/ -k workflow` | Run tests matching "workflow" |
| `./run_e2e_tests.sh` | Run full test suite |

## Test Markers

```python
@pytest.mark.e2e          # End-to-end tests
@pytest.mark.smoke        # Quick validation
@pytest.mark.integration  # Cross-module tests
@pytest.mark.asyncio      # Async tests
@pytest.mark.qt           # UI tests
```

## Key Fixtures

```python
# Use in tests:
def test_something(mock_guardian, temp_db, sample_workflow):
    # mock_guardian: Guardian service mock
    # temp_db: Temporary database
    # sample_workflow: Sample workflow definition
```

## Debugging Tests

```bash
# Verbose output
pytest tests/test_file.py -vv

# Show print statements
pytest tests/test_file.py -s

# Stop on first failure
pytest tests/test_file.py -x

# Debug mode (pdb)
pytest tests/test_file.py --pdb

# Last failed tests first
pytest --ff
```

## Coverage Reports

```bash
# Generate HTML report
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html

# Show missing lines
pytest tests/ --cov=app --cov-report=term-missing
```

## Writing New Tests

```python
import pytest

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_new_feature(mock_agent, temp_db):
    """Test that new feature works."""
    # Setup
    workflow = sample_workflow
    
    # Execute
    result = await mock_agent.execute_task(workflow)
    
    # Assert
    assert result["status"] == "success"
```

## Test File Locations

| File | Purpose | Tests |
|------|---------|-------|
| `test_e2e_workflows.py` | Main E2E workflows | 32 |
| `test_smoke_tests.py` | Quick validation | 24 |
| `test_integration_e2e.py` | Cross-module tests | 21 |

## CI/CD Pipeline

- **Trigger**: Push/PR to main
- **Status**: Check GitHub Actions
- **Artifacts**: Test results in Actions tab
- **Coverage**: View in Codecov

## Documentation

| Document | Purpose |
|----------|---------|
| `TESTING_E2E_GUIDE.md` | Comprehensive guide (1000+ lines) |
| `TESTING_README.md` | Quick reference |
| `E2E_TESTING_ACCEPTANCE_CRITERIA.md` | Acceptance verification |

## Common Issues & Solutions

**Tests timeout?**
- Increase timeout: `pytest tests/ --timeout=600`
- Check mock implementations
- Use `asyncio.sleep(0.01)` in fixtures

**Import errors?**
- Install dependencies: `pip install -r requirements-test.txt`
- Set PYTHONPATH: `export PYTHONPATH="$PWD:$PYTHONPATH"`

**PyQt6 headless issues?**
- Set env: `export QT_QPA_PLATFORM=offscreen`
- Already set in GitHub Actions

**Database errors?**
- Use `temp_db` fixture for isolation
- Verify SQL syntax in setup
- Check foreign key constraints

**Fixture not found?**
- Verify in `conftest.py`
- Check fixture name spelling
- Ensure `conftest.py` in tests directory

## Test Execution Flow

```
1. conftest.py loads (shared fixtures)
2. test_file.py collects tests
3. Each test function executes
4. Fixtures set up (setup)
5. Test runs
6. Fixtures tear down (cleanup)
7. Results reported
```

## Coverage Thresholds

- **Overall**: 80%+ ✅
- **Guardian**: 95%+ ✅
- **Sandbox**: 90%+ ✅
- **Memory**: 80%+ ✅

## Performance Targets

- Smoke tests: < 5 seconds
- Full E2E: < 30 seconds
- All tests: < 60 seconds

## Continuous Integration

**Pipeline jobs:**
1. E2E tests (Python 3.11, 3.12)
2. UI tests (xvfb headless)
3. Security validation
4. Performance benchmarks
5. Backup/recovery tests
6. Results summary

**Triggers:** Push, PR, scheduled (daily 2 AM UTC)

## Tips & Tricks

```bash
# Run in parallel (faster)
pytest tests/ -n auto

# Run only tests modified in this commit
pytest --lf  # last failed
pytest --ff  # failed first

# Generate HTML report
pytest tests/ --html=report.html

# Watch for changes and re-run
pytest-watch tests/
```

## Getting Help

1. Check **TESTING_E2E_GUIDE.md** for detailed documentation
2. Look at fixture examples in **conftest.py**
3. Review test implementations in **test_*.py** files
4. Check CI/CD logs in GitHub Actions
5. Ask team about specific test patterns

## Key Takeaways

✅ **71 tests** across critical workflows
✅ **20+ fixtures** for easy test setup
✅ **Automated CI/CD** with regression detection
✅ **80%+ coverage** target
✅ **Comprehensive documentation** included

---

**Quick Links:**
- [Full Testing Guide](TESTING_E2E_GUIDE.md)
- [README](TESTING_README.md)
- [Acceptance Criteria](E2E_TESTING_ACCEPTANCE_CRITERIA.md)
- [Implementation Summary](E2E_TESTING_IMPLEMENTATION_SUMMARY.md)

**Ready to test?** → `pytest tests/ -v` 🚀
