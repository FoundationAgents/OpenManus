#!/bin/bash
# Install dependencies for sandbox adapters

set -e

echo "📦 Installing OpenManus Sandbox Adapter Dependencies"
echo "=" | head -c 55 && echo

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Check Python version
check_python() {
    log_info "Checking Python version..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_success "Python $PYTHON_VERSION detected"

    # Check if version is 3.8+
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        log_success "Python version is compatible"
    else
        log_error "Python 3.8+ is required, found $PYTHON_VERSION"
        exit 1
    fi
}

# Install base dependencies
install_base() {
    log_info "Installing base dependencies..."

    pip install --upgrade pip

    # Core dependencies
    pip install \
        httpx \
        aiofiles \
        asyncio-extras \
        pydantic \
        typing-extensions

    log_success "Base dependencies installed"
}

# Install Docker adapter dependencies (already included in OpenManus)
install_docker_deps() {
    log_info "Checking Docker adapter dependencies..."

    # Docker Python SDK should already be installed
    if python3 -c "import docker" 2>/dev/null; then
        log_success "Docker Python SDK available"
    else
        log_info "Installing Docker Python SDK..."
        pip install docker
        log_success "Docker Python SDK installed"
    fi
}

# Install GitPod adapter dependencies
install_gitpod_deps() {
    log_info "Installing GitPod adapter dependencies..."

    # HTTPX for API calls (should already be installed)
    pip install httpx[http2]

    log_success "GitPod adapter dependencies installed"
}

# Install E2B adapter dependencies
install_e2b_deps() {
    log_info "Installing E2B adapter dependencies..."

    # Install E2B Code Interpreter
    pip install e2b-code-interpreter

    log_success "E2B adapter dependencies installed"
}

# Install optional browser automation dependencies
install_browser_deps() {
    log_info "Installing browser automation dependencies..."

    pip install \
        playwright \
        selenium \
        beautifulsoup4 \
        requests

    log_info "Installing Playwright browsers..."
    python3 -m playwright install chromium

    log_success "Browser automation dependencies installed"
}

# Verify installations
verify_installations() {
    log_info "Verifying installations..."

    # Test imports
    python3 -c "
print('Testing imports...')
try:
    import httpx
    print('✅ httpx')
except ImportError as e:
    print(f'❌ httpx: {e}')

try:
    import docker
    print('✅ docker')
except ImportError as e:
    print(f'❌ docker: {e}')

try:
    from e2b_code_interpreter import CodeInterpreter
    print('✅ e2b-code-interpreter')
except ImportError as e:
    print(f'⚠️  e2b-code-interpreter: {e} (optional)')

try:
    import playwright
    print('✅ playwright')
except ImportError as e:
    print(f'⚠️  playwright: {e} (optional)')

print('\n🎉 Import test complete!')
"

    log_success "Installation verification complete"
}

# Create requirements file for adapters
create_requirements() {
    log_info "Creating adapter requirements file..."

    cat > adapter-requirements.txt << 'EOF'
# OpenManus Sandbox Adapter Dependencies

# Base dependencies
httpx[http2]>=0.25.0
aiofiles>=23.0.0
pydantic>=2.0.0
typing-extensions>=4.0.0

# Docker adapter (should be in main requirements)
docker>=7.0.0

# E2B adapter
e2b-code-interpreter>=0.0.7

# Optional: Browser automation
playwright>=1.40.0
selenium>=4.15.0
beautifulsoup4>=4.12.0
requests>=2.31.0

# Optional: Additional async utilities
asyncio-extras>=1.3.0
aiohttp>=3.9.0
EOF

    log_success "Requirements file created: adapter-requirements.txt"
}

# Main installation function
main() {
    echo "Choose installation type:"
    echo "1) Full installation (all adapters + optional dependencies)"
    echo "2) Minimal installation (base + Docker only)"
    echo "3) GitPod adapter only"
    echo "4) E2B adapter only"
    echo "5) Browser automation dependencies only"
    echo "6) Create requirements file only"

    read -p "Enter your choice (1-6): " choice

    check_python

    case $choice in
        1)
            install_base
            install_docker_deps
            install_gitpod_deps
            install_e2b_deps
            install_browser_deps
            verify_installations
            create_requirements
            ;;
        2)
            install_base
            install_docker_deps
            verify_installations
            ;;
        3)
            install_base
            install_gitpod_deps
            verify_installations
            ;;
        4)
            install_base
            install_e2b_deps
            verify_installations
            ;;
        5)
            install_browser_deps
            verify_installations
            ;;
        6)
            create_requirements
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac

    echo
    log_success "Installation complete!"

    if [ "$choice" != "6" ]; then
        log_info "Next steps:"
        echo "  1. Test adapters: python3 scripts/test_sandbox_backends.py"
        echo "  2. Configure backends in config/config.toml"
        echo "  3. Set environment variables (E2B_API_KEY, GITPOD_TOKEN, etc.)"
    fi
}

# Run main function
main "$@"
