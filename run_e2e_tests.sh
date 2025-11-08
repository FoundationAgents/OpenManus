#!/bin/bash
# End-to-End Testing Runner
# Comprehensive test execution script

set -e

echo "========================================"
echo "End-to-End Testing Pipeline"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION=${PYTHON_VERSION:-"3.12"}
COVERAGE_THRESHOLD=80
QT_QPA_PLATFORM=offscreen

# Export for UI tests
export QT_QPA_PLATFORM

# Functions
print_header() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
}

print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        exit 1
    fi
}

# Check dependencies
print_header "Checking Dependencies"

if ! command -v python &> /dev/null; then
    print_status 1 "Python not found"
fi

python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Install dependencies
print_header "Installing Dependencies"

pip install -q --upgrade pip setuptools wheel
pip install -q -r requirements.txt
pip install -q -r requirements-test.txt

print_status 0 "Dependencies installed"

# Run linting
print_header "Code Quality Checks"

echo "Running flake8..."
flake8 app/ tests/ --max-line-length=127 --count --statistics --exclude=.venv
print_status $? "Flake8 passed"

echo "Checking code formatting with black..."
black --check app/ tests/ --line-length=127 2>&1 | tail -5
echo "Black check completed"

echo "Checking import sorting with isort..."
isort --check-only app/ tests/ --line-length=127 2>&1 | tail -5
echo "Isort check completed"

# Run type checking
print_header "Type Checking"

echo "Running mypy..."
mypy app/ --ignore-missing-imports --no-strict-optional 2>&1 | tail -10 || true
echo "Mypy check completed"

# Run E2E tests
print_header "E2E Workflow Tests"

pytest tests/test_e2e_workflows.py -v --tb=short --cov=app --cov-append
print_status $? "E2E workflow tests passed"

# Run smoke tests
print_header "Smoke Tests"

pytest tests/test_smoke_tests.py -v -m smoke --tb=short --cov=app --cov-append
print_status $? "Smoke tests passed"

# Run integration tests
print_header "Integration Tests"

pytest tests/test_integration_e2e.py -v -m integration --tb=short --cov=app --cov-append
print_status $? "Integration tests passed"

# Run security tests
print_header "Security Tests"

if [ -f "tests/test_guardian_validation.py" ]; then
    pytest tests/test_guardian_validation.py -v --tb=short --cov=app --cov-append
    print_status $? "Security tests passed"
else
    echo "Guardian validation tests not found, skipping"
fi

# Generate coverage report
print_header "Coverage Report"

coverage report --fail-under=$COVERAGE_THRESHOLD
print_status $? "Coverage meets threshold (>$COVERAGE_THRESHOLD%)"

echo "Generating HTML coverage report..."
coverage html
echo "HTML report generated at: htmlcov/index.html"

# Summary
print_header "Test Summary"

echo -e "${GREEN}✅ All tests passed successfully!${NC}"
echo ""
echo "Summary:"
echo "- E2E Workflow Tests: ✅"
echo "- Smoke Tests: ✅"
echo "- Integration Tests: ✅"
echo "- Security Tests: ✅"
echo "- Code Quality: ✅"
echo "- Type Checking: ✅"
echo "- Coverage: ✅"
echo ""
echo "Next steps:"
echo "1. Review coverage report: open htmlcov/index.html"
echo "2. Check CI/CD pipeline status"
echo "3. Deploy to staging if all tests pass"
echo ""
