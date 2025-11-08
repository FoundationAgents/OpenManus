"""
Test suite for End-to-End integration testing.

Modules:
- conftest.py: Shared fixtures and configuration
- test_e2e_workflows.py: Main E2E workflow tests
- test_smoke_tests.py: Quick validation tests
- test_integration_e2e.py: Cross-module integration tests

Test markers:
- @pytest.mark.e2e: End-to-end tests
- @pytest.mark.smoke: Smoke tests
- @pytest.mark.integration: Integration tests
- @pytest.mark.asyncio: Async tests
- @pytest.mark.qt: Qt UI tests

Usage:
    # Run all tests
    pytest tests/ -v

    # Run E2E tests only
    pytest tests/ -v -m e2e

    # Run with coverage
    pytest tests/ -v --cov=app

    # Run specific test
    pytest tests/test_e2e_workflows.py::TestWorkflowWithGuardianApprovals -v
"""

__version__ = "1.0.0"
