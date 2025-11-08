# Testing & Validation Pipeline

A comprehensive automated testing framework ensuring all code is thoroughly tested before production deployment.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Testing & Validation Pipeline                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Dev Agent writes code                                           │
│  ↓                                                                │
│  Test Agent generates tests automatically                        │
│  ├─ Unit tests (via AST analysis)                               │
│  ├─ Integration tests (API contracts)                           │
│  ├─ E2E tests (workflow scenarios)                              │
│  ├─ Property-based tests                                        │
│  ├─ Performance tests                                           │
│  └─ Security tests                                              │
│  ↓                                                                │
│  Test Executor orchestrates test runs                           │
│  ├─ Smoke tests (5 min)                                         │
│  ├─ Unit tests (15 min)                                         │
│  ├─ Integration tests (30 min)                                  │
│  ├─ E2E tests (45 min)                                          │
│  ├─ Performance tests (60 min)                                  │
│  └─ Security tests (20 min)                                     │
│  ↓                                                                │
│  Analysis & Validation                                          │
│  ├─ Coverage Analysis (≥80% threshold)                          │
│  ├─ Performance Regression Detection                            │
│  ├─ Security Testing (SAST/DAST)                               │
│  ├─ Mutation Testing (test quality)                            │
│  ├─ Test Quality Scoring                                        │
│  ├─ Flaky Test Detection                                        │
│  └─ Documentation Testing                                       │
│  ↓                                                                │
│  QA Agent reviews tests                                         │
│  ↓                                                                │
│  Production Readiness Check                                     │
│  ├─ All tests passed ✓                                          │
│  ├─ Coverage >= threshold ✓                                     │
│  ├─ No performance regression ✓                                 │
│  ├─ No security issues ✓                                        │
│  └─ All quality gates passed ✓                                  │
│  ↓                                                                │
│  Deploy to production                                           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Test Executor (`app/qa/test_executor.py`)

Orchestrates test execution with:
- **Dependency management**: Topological sort for test ordering
- **Parallel execution**: Configurable worker threads
- **Timeout management**: Per-test and per-level timeouts
- **Failure capture**: Stdout, stderr, tracebacks
- **Retry logic**: Automatic retry for flaky tests

```python
executor = TestExecutor(config)
await executor.register_test("test_001", "test_example", TestLevel.UNIT, "tests/test_example.py")
result = await executor.run_tests(levels=[TestLevel.UNIT, TestLevel.INTEGRATION], parallel=True)
```

### 2. Coverage Analyzer (`app/qa/coverage_analyzer.py`)

Measures and enforces code coverage:
- **Line coverage**: Code line execution tracking
- **Branch coverage**: Decision path tracking
- **Function coverage**: Function execution tracking
- **Thresholds**: Overall (80%), new code (90%), critical paths (95%)
- **Dead code detection**: Identifies unreachable code
- **HTML reports**: Visual coverage reports

```python
analyzer = CoverageAnalyzer(config)
report = await analyzer.measure_coverage(test_directories=["tests/"], source_directories=["app/"])
if not report.is_within_thresholds():
    # Block deployment
    pass
```

### 3. Performance Regression Detector (`app/qa/perf_regression_detector.py`)

Tracks performance baselines and detects regressions:
- **Latency tracking**: Response time benchmarks
- **Memory profiling**: Memory usage tracking
- **Throughput measurement**: Operations per second
- **Regression detection**: Flags > 10% latency increase, > 20% memory, > 5% throughput
- **Profiling**: CPU, memory, I/O profiling
- **Flamegraphs**: Performance visualization

```python
detector = PerformanceRegressionDetector(config)
baseline = await detector.benchmark("operation", test_func, runs=5)
report = await detector.detect_regressions()
if detector.has_critical_regressions():
    # Block deployment
    pass
```

### 4. Security Tester (`app/qa/security_tester.py`)

Comprehensive security scanning:
- **SAST**: Static analysis for vulnerabilities
  - SQL injection detection
  - Command injection detection
  - Hardcoded credentials
  - Weak cryptography
  - XXE vulnerabilities
  - Path traversal risks
  - Insecure deserialization
- **DAST**: Dynamic testing (optional, expensive)
- **Dependency scanning**: CVE detection in dependencies
- **Block deployment**: On CRITICAL/HIGH vulnerabilities

```python
tester = SecurityTester(config)
report = await tester.scan_codebase(["app/"])
if not report.safe_to_deploy:
    # Block deployment
    pass
```

### 5. Mutation Tester (`app/qa/mutation_tester.py`)

Advanced test quality verification:
- **Mutation generation**: Creates intentional bugs
- **Mutation testing**: Runs test suite against mutants
- **Coverage gaps**: Identifies untested code paths
- **Mutation score**: Percentage of killed mutants
- **Test quality**: If mutants survive, tests are insufficient

```python
tester = MutationTester(config)
mutants = await tester.generate_mutants("app/module.py", max_mutants=50)
result = await tester.run_mutation_tests(test_command="pytest tests/ -q")
# Result shows mutation_score, coverage_gaps
```

### 6. Test Quality Scorer (`app/qa/test_quality_scorer.py`)

Rates individual test quality (0-100):
- **Clear assertions**: Does test have explicit assertions?
- **Setup/teardown**: Proper test structure?
- **Isolation**: No external dependencies?
- **Determinism**: No non-deterministic operations?
- **Edge cases**: Tests boundary conditions?
- **Performance**: Runs in < 1 second?
- **Maintainability**: Code clarity and structure

```python
scorer = TestQualityScorer({"min_test_quality_score": 70})
results = await scorer.score_test_file("tests/test_example.py")
low_quality_tests = scorer.get_failed_quality_tests()
```

### 7. Flaky Test Detector (`app/qa/flaky_test_detector.py`)

Identifies intermittent test failures:
- **Multiple runs**: Execute each test N times (default: 3)
- **Flakiness detection**: Inconsistent pass/fail patterns
- **Cause estimation**:
  - Timing issues (insufficient sleep/waits)
  - Random values (unseed generators)
  - External service dependencies
  - Race conditions
  - Order dependencies
  - Environment issues
- **Recommendations**: Fix suggestions based on cause

```python
detector = FlakyTestDetector({"num_runs": 3})
report = await detector.detect_flaky_tests(num_runs=3)
for flaky in detector.get_flakiest_tests():
    print(f"Fix: {flaky.recommendation}")
```

### 8. Documentation Tester (`app/qa/doc_tester.py`)

Validates code samples in documentation:
- **Extract samples**: Finds code blocks in Markdown
- **Execute samples**: Runs code to verify it works
- **API mismatch detection**: Finds outdated documentation
- **Update suggestions**: Recommends documentation changes

```python
tester = DocumentationTester(config)
samples = await tester.scan_documentation(["docs/"])
report = await tester.test_samples(samples)
if report.failed_samples > 0:
    suggestions = await tester.generate_docs_update_suggestions(report)
```

### 9. Test Reporter (`app/qa/test_reporter.py`)

Generates comprehensive reports:
- **Multiple formats**: HTML, JSON, JUnit
- **Test results**: Pass/fail breakdown
- **Coverage metrics**: Line/branch/function coverage
- **Performance trends**: Comparison with baseline
- **Security findings**: Vulnerability list
- **Mutation results**: Test quality metrics
- **Git integration**: Links to commits

```python
reporter = TestReporter(config)
report = await reporter.generate_report(
    test_results=test_results,
    coverage_report=coverage_report,
    security_report=security_report,
)
# Generates HTML, JSON, and JUnit reports
```

### 10. Test Agent (`app/agent/specialists/test_agent.py`)

Specialist agent that automatically generates tests:
- **AST analysis**: Analyzes code structure
- **Function signatures**: Generates test cases for all parameters
- **Edge cases**: Creates tests for boundary conditions
- **Fixtures**: Generates complex test fixtures
- **Parametrized tests**: Multiple scenarios per test
- **LLM enhancement**: Uses LLM to understand business logic

```python
test_agent = TestAgent("test_agent_001", blackboard)
result = await test_agent.execute_role_specific_task(
    DevelopmentTask(
        requirements={
            "code_files": ["app/module.py"],
            "test_types": ["unit", "integration"],
        }
    )
)
```

## Configuration

Configuration file: `config/testing.toml`

```toml
[testing]
enabled = true
auto_generate_tests = true
run_all_levels = true

[testing.coverage]
enforce = true
threshold_overall = 80       # Minimum overall coverage %
threshold_new_code = 90      # New code must be higher
threshold_critical = 95      # Critical paths must be higher

[testing.performance]
benchmark = true
threshold_latency_regression = 10      # % increase is failure
threshold_memory_regression = 20       # % increase is failure
threshold_throughput_regression = 5    # % decrease is failure

[testing.security]
sast_enabled = true
dast_enabled = false
dependency_scan = true
block_on_critical = true

[testing.quality]
mutation_testing = true
flaky_test_detection = true
doc_testing = true
min_test_quality_score = 70

[testing.execution]
timeout_per_test = 30
parallel_workers = 4
retry_flaky = true
retry_count = 2
```

## Workflow Integration

### Development Workflow

1. **Dev Agent writes code** → commits to `feat/` branch
2. **Trigger Test Agent** → generate tests
3. **Test Executor runs tests** in parallel:
   - Smoke tests (5 min)
   - Unit tests (15 min)
   - Integration tests (30 min)
   - E2E tests (45 min)
4. **Coverage Analysis** → enforce ≥80%
5. **Performance Check** → detect regressions
6. **Security Scan** → find vulnerabilities
7. **Test Quality** → score individual tests
8. **Flaky Detection** → identify intermittent failures
9. **QA Agent reviews** → final validation
10. **Production Readiness** → all gates pass
11. **Deploy** → merge to main

### Continuous Integration

The pipeline integrates with CI/CD:
- GitHub Actions triggers test pipeline
- Reports published as artifacts
- Coverage trends tracked
- Deployment blocked if tests fail

### Local Development

Run tests locally with:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific level
python -m pytest tests/ -m "unit" -v

# Generate coverage
pytest --cov=app --cov-report=html

# Check for flaky tests
pytest tests/ --count=3  # Run each test 3 times

# Generate test report
python -m pytest tests/ --html=report.html
```

## Performance Impact

Execution times by test level:
- **Smoke**: 5 minutes (basic functionality)
- **Unit**: 15 minutes (component-level)
- **Integration**: 30 minutes (cross-component)
- **E2E**: 45 minutes (full workflow)
- **Performance**: 60 minutes (benchmarks)
- **Security**: 20 minutes (scanning)

Total: ~2.75 hours for full validation

Parallel execution with 4 workers reduces to ~1 hour.

## Key Features

✅ **Automatic Test Generation**: Generate tests from code structure
✅ **Orchestrated Execution**: Dependency ordering, parallelization
✅ **Coverage Enforcement**: Block deployment on low coverage
✅ **Performance Tracking**: Detect regressions automatically
✅ **Security Scanning**: Find vulnerabilities before production
✅ **Test Quality Scoring**: Rate individual test quality
✅ **Flaky Detection**: Identify intermittent failures
✅ **Documentation Validation**: Verify code samples work
✅ **Comprehensive Reports**: HTML, JSON, JUnit formats
✅ **Trend Tracking**: Historical metrics and comparisons
✅ **Human-Free**: All automated, no manual review needed

## Acceptance Criteria (All Met ✓)

- ✓ Test Agent generates unit/integration/E2E tests automatically
- ✓ Test Executor runs all levels with orchestration
- ✓ Coverage tracked and enforced (≥80% required)
- ✓ Performance benchmarks prevent regressions
- ✓ Security scans detect vulnerabilities
- ✓ Mutation testing ensures test quality
- ✓ Flaky test detection prevents intermittent failures
- ✓ Documentation tests verify API samples
- ✓ Test quality scoring enforces good practices
- ✓ All tests must pass before production deployment
- ✓ UI shows comprehensive test status and metrics
- ✓ Reports persisted and trended
- ✓ Tests can be re-run, debugged, and improved
- ✓ Deployment blocks if any test fails

## Philosophy

**Tests are First-Class Citizens:**
- Tests generated alongside code
- Test quality actively monitored
- Poor tests fail gate same as bad code
- Tests themselves tested (mutation testing)

**Comprehensive Safety Net:**
- Unit tests (correctness)
- Integration tests (component interaction)
- E2E tests (workflow)
- Performance tests (no regression)
- Security tests (no vulnerabilities)
- Coverage (code paths exercised)
- Test quality (tests actually test)
- Flaky detection (reliable tests)

**Goal: Production Readiness Through Testing**
- If all tests pass → code is production-ready
- No human test review needed
- Automated test generation saves time
- Test metrics prevent quality decay

## Future Enhancements

- ML-based test generation optimization
- Custom rule DSL for domain-specific tests
- Advanced SAST tool integration (Bandit, Semgrep)
- Real-time code review plugins
- IDE integration and live test execution
- Cross-repo learning and pattern sharing
- Benchmark regression detection with statistical analysis
- Performance profiling dashboards
- CVE database integration for dependency scanning
- Custom test templates for common patterns
