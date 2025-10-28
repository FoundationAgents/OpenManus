#!/bin/bash

# Golang code formatting script
# This script runs linting, security scanning, and unit tests for Golang code

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
VERBOSE=false

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
        --verbose)
        VERBOSE=true
        shift
        ;;
    esac
done

# Check if go is installed
if ! command -v go &> /dev/null; then
    print_error "go is not installed"
    exit 1
fi

# Install required tools
install_tools() {
    print_section "Installing required tools"

    # Install linting tools
    if ! command -v golint &> /dev/null; then
        echo "Installing golint..."
        go install golang.org/x/lint/golint@latest
    fi

    # Install security scanning tools
    if ! command -v gosec &> /dev/null; then
        echo "Installing gosec..."
        go install github.com/securego/gosec/v2/cmd/gosec@latest
    fi

    # Install dependency check tool
    if ! command -v govulncheck &> /dev/null; then
        echo "Installing govulncheck..."
        go install golang.org/x/vuln/cmd/govulncheck@latest
    fi
}

# Linting function
run_linting() {
    if [ "$SKIP_LINT" = true ]; then
        print_warning "Skipping linting checks"
        return 0
    fi

    print_section "Running code linting and formatting"

    # Run gofmt to format code, excluding api/client directory
    echo "Running gofmt..."
    find . -name "*.go" -not -path "./vendor/*" -not -path "*/api/client/*" | xargs gofmt -w -s

    # Run go fmt, excluding api/client directory
    echo "Running go fmt..."
    for dir in $(go list ./... | grep -v "/api/client"); do
        go fmt $dir
    done

    # Run golint to check for style issues
    echo "Running golint..."
    golint ./...

    # Run go vet for deeper code analysis
    echo "Running go vet..."
    go vet ./...

    # Check if there are uncommitted changes after formatting
    if ! git diff --quiet; then
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

    # Run gosec for security vulnerabilities
    echo "Running gosec security scanner..."
    gosec -fmt=text ./...

    # Run govulncheck for dependency vulnerabilities
    echo "Running govulncheck for dependency vulnerabilities..."
    govulncheck ./...

    print_success "Security scans completed"
}

# Unit tests function
run_tests() {
    if [ "$SKIP_TESTS" = true ]; then
        print_warning "Skipping tests"
        return 0
    fi

    print_section "Running unit tests"

    # Run tests with coverage
    VERBOSE_FLAG=""
    if [ "$VERBOSE" = true ]; then
        VERBOSE_FLAG="-v"
    fi

    echo "Running unit tests with coverage..."
    go test $VERBOSE_FLAG -race  ./tests/pkg/unit/...

    print_success "Unit tests passed!"
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