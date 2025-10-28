#!/bin/bash

# TypeScript code formatting script
# This script runs linting, security scanning, and unit tests for TypeScript code

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

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing npm dependencies..."
        npm install
    fi

    # Ensure security tools are installed
    npm install --no-save eslint prettier typescript jest ts-jest @typescript-eslint/parser @typescript-eslint/eslint-plugin
    npm install --no-save audit-ci snyk

    if ! command -v nancy &> /dev/null; then
        echo "Installing nancy..."
        go install github.com/sonatype-nexus-community/nancy@latest
    fi
}

# Linting function
run_linting() {
    if [ "$SKIP_LINT" = true ]; then
        print_warning "Skipping linting checks"
        return 0
    fi

    print_section "Running code linting and formatting"

    # Run ESLint with auto-fix
    echo "Running ESLint with auto-fix..."
    npm run lint -- --fix

    # Run Prettier formatting, excluding api/models directory
    echo "Running Prettier formatting..."
    npx prettier --write "src/**/*.ts" "tests/**/*.ts" "!src/api/models/**"

    # Check if there are uncommitted changes after formatting
    if ! git diff --quiet src tests; then
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

    # Run npm audit for vulnerability scanning
    echo "Running npm audit..."
    npm audit

    # Run audit-ci for more detailed checks
    echo "Running audit-ci..."
    npx audit-ci --moderate

    # Run snyk test (if you have a Snyk account)
    echo "Running snyk test..."
    if command -v snyk &> /dev/null; then
        snyk test || print_warning "Snyk test found vulnerabilities, but continuing..."
    else
        print_warning "Snyk not available or not authenticated. Skipping snyk test."
    fi

    print_success "Security scans completed"
}

# Unit tests function
run_tests() {
    if [ "$SKIP_TESTS" = true ]; then
        print_warning "Skipping tests"
        return 0
    fi

    print_section "Running unit tests"

    # Run only unit tests without integration tests
    echo "Running unit tests..."
    npm run test:unit

    print_success "All unit tests passed!"
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