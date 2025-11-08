# QA Agent & Code Quality Analysis System

## Overview

The QA System is an **independent QA Agent pool** that validates all code written by development agents, detecting and automatically fixing quality issues to ensure production-ready code without human review.

## Key Features

### 🤖 QA Agent Specialization
- **Independent reasoning**: Reviews code written by OTHER agents (not self-reviewing)
- **Autonomous execution**: Runs AFTER dev agent completes task but BEFORE merging to main branch
- **Configurable QA levels**:
  - **Level 1 (BASIC)**: Syntax, imports, basic linting
  - **Level 2 (STANDARD)**: + Code smells, naming conventions, error handling
  - **Level 3 (STRICT)**: + Performance, security, architectural patterns
  - **Level 4 (PARANOID)**: + Style nitpicks, documentation, test coverage

### 🔍 Code Quality Analyzer
Comprehensive detection pipeline for:

**Stub/Placeholder Detection:**
- Patterns: `pass`, `...`, `TODO`, `FIXME`, `NotImplemented`, `raise NotImplementedError`
- Context analysis: intentional (interface) vs forgotten
- Severity scoring based on code path coverage

**Халтура (Hack/Workaround) Detection:**
- Pattern matching: `# HACK:`, `# FIXME:`, `while True: break`
- Timeout/retry patterns poorly written
- Magic numbers without explanation
- Redundant/duplicate code blocks
- Dead code paths
- Severity: HIGH (blocks production)

**Anti-patterns & Code Smells:**
- Overly complex functions (cyclomatic complexity)
- Deep nesting (> 4 levels)
- God objects / overly large classes
- Missing error handling
- Resource leaks (file handles, database connections)
- Type safety issues
- Security issues (SQL injection, command injection, hardcoded secrets)

**Incomplete Implementation:**
- Functions with `return None` without documentation
- Edge case handling missing
- Configuration validation missing
- Input sanitization missing
- Insufficient logging

**Planning Quality Issues:**
- Architectural mismatches
- Wrong data structure choices (O(n²) when O(n) possible)
- Missing dependency injection
- Tight coupling
- Not following established patterns

### 🔧 Automatic Remediation Engine
Auto-fixable issues:
- Import organization (sort, remove unused)
- Formatting (indentation, line length, trailing spaces)
- Variable naming (snake_case, meaningful names)
- Add type hints where obvious
- Add docstrings template
- Extract magic numbers to constants
- Add assert/validate checks for inputs
- Wrap uncaught exceptions in try/except
- Add logging at key decision points

Manual review required:
- Logic errors (requires reasoning about intent)
- Architectural changes
- Performance optimizations (might change behavior)
- Complex security fixes

### ✅ Planning Validator
Validates workflow/task decomposition:

**Validation checks:**
- Task granularity: not too large (> 4h) or too small (< 15min)
- Dependency correctness: no circular dependencies
- Effort estimation accuracy
- Risk assessment: high-risk items have mitigation plans
- Resource allocation: no single person bottleneck
- Acceptance criteria: SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
- Test strategy: how will success be verified?
- Completeness: all edge cases identified
- Feasibility: no impossible constraints

### 🚀 Production Readiness Check
Final gate before merge to production:

**Checklist:**
- ✓ All tests passing (unit, integration, e2e)
- ✓ Code coverage >= threshold (configurable, default 80%)
- ✓ No security issues detected (SAST scan)
- ✓ No performance regressions
- ✓ No undocumented public APIs
- ✓ Database migrations tested
- ✓ Deployment procedure documented
- ✓ Rollback procedure documented
- ✓ Monitoring/alerting configured
- ✓ No hardcoded credentials or secrets
- ✓ All dependencies pinned to versions
- ✓ Backwards compatibility verified
- ✓ Documentation updated
- ✓ Changelog entry added
- ✓ Version bump correct
- ✓ Performance meets SLAs

### 🧠 QA Knowledge Base
Builds knowledge graph of:
- Common anti-patterns in this codebase
- Historical issues (what breaks production frequently)
- Best practices for this tech stack
- Performance optimization patterns
- Security vulnerability patterns
- Testing strategies for different code types

**Learning capability:**
- Each time QA catches something, adds to knowledge base
- Feeds into LLM context for QA agent (improves over time)
- Query by: "how do we handle database transactions?" → returns patterns from successful code + anti-patterns

### 📊 Metrics & Reporting
Tracks:
- Code quality score (0-100)
- Issues per 1000 LOC
- False positive rate
- Auto-fix success rate
- Prod incidents caused by agent code
- QA agent accuracy over time

**Reports:**
- Daily QA report (issues found, fixed, accuracy)
- Weekly team report (quality trends)
- Per-agent comparison (which agents write higher quality)
- Per-project quality matrix

## Architecture

### Workflow with QA Gate

```
Dev Agent Task:
├─ Develop feature
├─ Write tests
├─ Commit to dev branch
└─ Request code review (trigger QA)

QA Agent Task (runs automatically):
├─ Analyze all code changes
├─ Run checklist
├─ Auto-fix if possible
├─ Create QA report
├─ If issues found:
│  ├─ HIGH/CRITICAL: Block merge, create remediation task
│  ├─ MEDIUM: Approve with recommendations
│  └─ LOW: Approve, log for future
├─ Create QA approval commit
└─ Merge to main branch

Production Readiness Check:
├─ Verify all acceptance criteria
├─ Run full test suite
├─ Performance benchmarks
├─ Deploy to staging
├─ Smoke tests
└─ Approve for production
```

## Usage

### Python API

```python
from app.agent.specialists import QAAgent, QALevel
from app.workflows.qa_integration import QAGate, QAWorkflowIntegration

# Initialize QA gate
qa_gate = QAGate(qa_level="standard", auto_fix=True)

# Review code
result = await qa_gate.review_code(
    code_files=["path/to/file.py"],
    author_agent="dev-agent-1",
    task_id="task-123"
)

# Check approval status
if result["approval_status"] == "BLOCKED":
    print(f"Blockers: {result['blockers']}")
elif result["approval_status"] == "APPROVED":
    print("Code approved for merge!")

# Validate planning
plan = {
    "tasks": [
        {
            "id": "task-1",
            "description": "Implement feature X",
            "estimated_hours": 3,
            "dependencies": [],
            "acceptance_criteria": ["Feature works", "Tests pass"],
            "test_strategy": "Unit + integration tests"
        }
    ]
}

validation = await qa_gate.validate_planning(plan)

# Check production readiness
readiness = await qa_gate.check_production_readiness(code_files)

if readiness["ready"]:
    print("Production ready!")
else:
    print(f"Blockers: {readiness['blockers']}")
```

### Configuration

Edit `config/qa.toml`:

```toml
[qa]
enabled = true
mode = "standard"  # basic | standard | strict | paranoid
auto_fix_enabled = true
auto_fix_safe_only = true

[qa.thresholds]
max_cyclomatic_complexity = 10
max_nesting_depth = 4
min_code_coverage = 80
max_function_lines = 50
max_file_lines = 500

[qa.blockers]
critical_issues = true
security_issues = true
high_issues = true
```

### CLI Usage

```bash
# Run QA check
python -m app.qa.check --files path/to/file.py

# Generate reports
python -m app.qa.report --daily
python -m app.qa.report --weekly

# Query knowledge base
python -m app.qa.knowledge --query "sql injection"
```

### UI Panel

The QA Monitor Panel shows:
- **Current QA scans**: Progress bars for active scans
- **Issue dashboard**: Breakdown by severity (CRITICAL/HIGH/MEDIUM/LOW)
- **Auto-fixes applied**: Count and types
- **Prod readiness checklist**: ✓/✗ per item
- **QA approval status**: APPROVED/BLOCKED/PENDING
- **Historical QA metrics**: Issues caught per day, fix rate
- **Knowledge base status**: Patterns known

Access via: Main UI → Panels → QA Monitor

## Testing

Run comprehensive test suite:

```bash
pytest tests/qa/test_qa_system.py -v
```

Tests cover:
- Stub detection (various patterns)
- Hack/workaround detection
- Auto-fix correctness (code still runs after fix)
- Planning validation logic
- Prod readiness checks
- QA knowledge base learning
- Full workflow with QA gate

## Key Philosophy

### QA Agent is NOT part of dev team
- Independent scoring and evaluation
- No conflicts of interest
- Fresh perspective on code
- Autonomous decision-making (can override dev agent if needed)
- Learns from all code, teaches best practices

### Goal: Production-Ready Code on First Try
- No human review needed
- QA gate is the final filter
- Issues caught early (before prod)
- Automatic remediation when safe
- Manual escalation for complex fixes

## Integration Points

### Guardian Integration
- QA changes reviewed by Guardian (especially logic-changing fixes)
- Prod readiness approval requires Guardian sign-off
- Audit trail: who (QA agent) changed what (code) why (issue ID)
- Rollback capability if QA introduced regression

### Versioning & Rollback
- QA changes create their own version entry
- Atomic commits: code + tests + documentation versioned together
- Rollback chain: can rollback dev agent code, then QA fixes separately

### Workflow Manager
- Automatic integration with workflow execution
- QA gate runs between dev completion and merge
- Blocks merge if critical issues found
- Creates remediation tasks automatically

## Files Structure

```
app/
├── agent/specialists/
│   └── qa_agent.py              # QA Agent specialization
├── qa/
│   ├── __init__.py              # Package exports
│   ├── code_analyzer.py         # Code quality analyzer
│   ├── code_remediator.py       # Automatic remediation
│   ├── planning_validator.py    # Planning validation
│   ├── prod_readiness.py        # Production readiness
│   ├── qa_knowledge_graph.py    # Knowledge base
│   └── qa_metrics.py            # Metrics & reporting
├── workflows/
│   └── qa_integration.py        # Workflow integration
└── ui/panels/
    └── qa_monitor.py            # UI monitoring panel

config/
└── qa.toml                      # QA configuration

tests/qa/
└── test_qa_system.py            # Comprehensive tests
```

## Performance

- **Review time**: < 10s for typical file (< 500 lines)
- **Auto-fix time**: < 1s per fix
- **Knowledge base query**: < 100ms
- **Production readiness check**: < 5min (includes test runs)

## Future Enhancements

- [ ] Machine learning-based issue detection
- [ ] Custom rule definitions via DSL
- [ ] Integration with external SAST tools (SonarQube, etc.)
- [ ] Real-time code review (as you type)
- [ ] IDE plugin for live QA feedback
- [ ] Cross-repository pattern learning
- [ ] Automated benchmark regression detection
- [ ] Performance profiling integration
- [ ] Security CVE database integration

## Contributing

When adding new QA checks:

1. Add pattern to `CodeAnalyzer`
2. Add auto-fix to `CodeRemediator` if applicable
3. Add tests to `test_qa_system.py`
4. Update knowledge base with pattern
5. Document in this README

## License

Same as main project license.
