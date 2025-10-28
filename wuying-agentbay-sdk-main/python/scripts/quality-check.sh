#!/bin/bash

# Python code formatting script
# This script runs linting, security scanning, and unit tests

set -e # Exit on error

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_section() {
    echo -e "\n${GREEN}=== $1 ===${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

print_success() {
    echo -e "${GREEN}SUCCESS: $1${NC}"
}

# Check for command line arguments
SKIP_TESTS=false
SKIP_SECURITY=false
SKIP_LINT=false

for arg in "$@"
do
    case $arg in
        --skip-tests)
        SKIP_TESTS=true
        shift
        ;;
        --skip-security)
        SKIP_SECURITY=true
        shift
        ;;
        --skip-lint)
        SKIP_LINT=true
        shift
        ;;
    esac
done

# Install required tools
install_tools() {
    print_section "Installing required tools"

    python -m pip install --upgrade pip

    # Install linting tools
    pip install flake8 black

    # Install security tools
    pip install bandit pip-audit

    # Install testing tools
    pip install pytest pytest-cov
}

# Linting function
run_linting() {
    if [ "$SKIP_LINT" = true ]; then
        print_warning "Skipping linting checks"
        return 0
    fi

    print_section "Running code linting and formatting"

    # Run flake8 to check for code issues
    echo "Running flake8..."
    python -m flake8 agentbay tests --count --select=E9,F63,F7,F82 --show-source --statistics

    # For more comprehensive checks (uncomment when ready)
    # python -m flake8 agentbay tests --count --max-complexity=10 --max-line-length=127 --statistics

    # Run black to format code, excluding agentbay/api/models directory
    echo "Running black formatter..."
    python -m black agentbay tests --exclude "agentbay/api/models"

    # Check if there are uncommitted changes after formatting
    if ! git diff --quiet agentbay tests; then
        print_warning "Formatting changes were made. Please review and commit these changes."
    else
        print_success "No formatting changes needed."
    fi
}

# Security scanning function
run_security_scan() {
    if [ "$SKIP_SECURITY" = true ]; then
        print_warning "Skipping security scans"
        return 0
    fi

    print_section "Running security scans"

    # Run Bandit for security vulnerabilities
    echo "Running bandit security scanner..."
    python -m bandit -r agentbay -f txt --skip B105,B106,B107

    # Run pip-audit for dependency vulnerabilities
    echo "Running pip-audit for dependency vulnerabilities..."
    pip install -e .
    python -m pip_audit

    print_success "Security scans completed"
}

# Unit tests function
run_tests() {
    if [ "$SKIP_TESTS" = true ]; then
        print_warning "Skipping tests"
        return 0
    fi

    print_section "Running unit tests"

    # Run pytest with coverage report
    echo "Running pytest with coverage..."
    python -m pytest tests/unit -v --cov=agentbay --cov-report=term --cov-report=xml

    print_success "All tests passed!"
}

# Main execution
main() {
    # Install tools if not already installed
    install_tools

    # Run linting
    run_linting

    # Run security scans
    run_security_scan

    # Run tests
    run_tests

    print_section "All checks completed successfully!"
}

# Execute main function
main
