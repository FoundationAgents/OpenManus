#!/bin/bash
# Setup Open Source Sandbox Backends for OpenManus

set -e  # Exit on any error

echo "🚀 Setting up Open Source Sandbox Backends for OpenManus"
echo "=" | head -c 60 && echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check requirements
check_requirements() {
    log_info "Checking requirements..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is required but not installed"
        exit 1
    fi

    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is required but not installed"
        exit 1
    fi

    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi

    log_success "Requirements check passed"
}

# Setup Docker backend (already available)
setup_docker() {
    log_info "Setting up Docker backend..."

    # Docker is already implemented in OpenManus
    # Just verify it works
    if docker ps &> /dev/null; then
        log_success "Docker backend ready"
    else
        log_warning "Docker daemon not running. Please start Docker."
    fi
}

# Setup GitPod self-hosted
setup_gitpod() {
    log_info "Setting up GitPod self-hosted..."

    # Create GitPod directory
    mkdir -p ./gitpod-setup

    # Create docker-compose for GitPod
    cat > ./gitpod-setup/docker-compose.yml << 'EOF'
version: '3.8'
services:
  gitpod:
    image: gitpod/gitpod:latest
    ports:
      - "80:80"
      - "443:443"
      - "22:22"
    volumes:
      - gitpod-data:/var/lib/gitpod
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      GITPOD_DOMAIN: gitpod.local
      GITPOD_INSTALLATION_LONGNAME: "OpenManus GitPod"
      GITPOD_LICENSE_TYPE: "free"
    restart: unless-stopped

  registry:
    image: registry:2
    ports:
      - "5000:5000"
    volumes:
      - registry-data:/var/lib/registry
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: gitpod
      MINIO_ROOT_PASSWORD: gitpod123
    command: server /data --console-address ":9001"
    volumes:
      - minio-data:/data
    restart: unless-stopped

volumes:
  gitpod-data:
  registry-data:
  minio-data:
EOF

    # Create GitPod sandbox image
    cat > ./gitpod-setup/Dockerfile.sandbox << 'EOF'
FROM gitpod/workspace-full-vnc:latest

# Install additional packages for browser automation
RUN sudo apt-get update && \
    sudo apt-get install -y \
        google-chrome-stable \
        chromium-browser \
        tigervnc-standalone-server \
        supervisor && \
    sudo rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    playwright \
    selenium \
    browser-use \
    httpx \
    beautifulsoup4

# Install Playwright browsers
RUN python -m playwright install chromium

# Setup supervisor configuration
COPY supervisor.conf /etc/supervisor/conf.d/sandbox-services.conf

# Create VNC startup script
RUN mkdir -p ~/.vnc && \
    echo '#!/bin/bash\nexport XKL_XMODMAP_DISABLE=1\nexport XDG_CURRENT_DESKTOP="XFCE"\nexport XDG_SESSION_DESKTOP="xfce"\nunset SESSION_MANAGER\nstartxfce4 &' > ~/.vnc/xstartup && \
    chmod +x ~/.vnc/xstartup

EXPOSE 6080 8080 9222

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/sandbox-services.conf"]
EOF

    # Create supervisor config
    cat > ./gitpod-setup/supervisor.conf << 'EOF'
[supervisord]
nodaemon=true
user=root

[program:vnc]
command=vncserver :1 -fg -geometry 1024x768 -depth 24 -localhost no
autorestart=true
user=gitpod
environment=HOME="/home/gitpod",USER="gitpod"

[program:chrome-debug]
command=google-chrome --remote-debugging-port=9222 --no-sandbox --disable-dev-shm-usage --headless --disable-gpu
autorestart=true
user=gitpod
environment=DISPLAY=":1"
EOF

    log_success "GitPod setup files created in ./gitpod-setup/"
    log_info "To start GitPod: cd gitpod-setup && docker-compose up -d"
}

# Setup E2B
setup_e2b() {
    log_info "Setting up E2B..."

    # Install E2B package
    pip install --quiet e2b-code-interpreter

    # Create E2B example config
    cat > ./e2b-example.env << 'EOF'
# E2B Configuration
E2B_API_KEY=your_e2b_api_key_here
E2B_TEMPLATE=base
SANDBOX_BACKEND=e2b
EOF

    log_success "E2B setup complete"
    log_warning "Don't forget to set your E2B_API_KEY in environment or config"
}

# Create example configuration
create_example_config() {
    log_info "Creating example configuration..."

    cat > ./sandbox-backends-example.toml << 'EOF'
# OpenManus Sandbox Backends Configuration

[sandbox]
# Available backends: docker, gitpod, e2b
backend = "docker"  # Default: local Docker
use_sandbox = true
image = "python:3.12-slim"
work_dir = "/workspace"
memory_limit = "1g"
cpu_limit = 2.0
timeout = 300
network_enabled = true
auto_cleanup = true
max_sandboxes = 10
idle_timeout = 3600

# GitPod backend settings (when backend = "gitpod")
gitpod_url = "http://localhost"  # Your GitPod instance
gitpod_token = "your_gitpod_api_token_here"

# E2B backend settings (when backend = "e2b")
e2b_api_key = "your_e2b_api_key_here"  # Or set E2B_API_KEY env var
e2b_template = "base"  # E2B template to use
EOF

    log_success "Example configuration created: sandbox-backends-example.toml"
}

# Test sandbox backends
test_backends() {
    log_info "Testing sandbox backends..."

    # Create test script
    cat > ./test_sandbox_backends.py << 'EOF'
#!/usr/bin/env python3
"""Test script for sandbox backends."""

import asyncio
import os
import sys
sys.path.insert(0, './app')

from sandbox.adapters.factory import SandboxFactory
from sandbox.adapters.unified_client import UnifiedSandboxClient

async def test_backend(backend_name, config=None):
    """Test a specific backend."""
    print(f"\n🧪 Testing {backend_name} backend...")

    try:
        client = UnifiedSandboxClient(backend_name, config)
        print(f"✅ {backend_name} client created successfully")

        # Test basic functionality
        async with client.sandbox_context() as sandbox_id:
            print(f"✅ Sandbox created: {sandbox_id}")

            # Test command execution
            result = await client.execute(sandbox_id, "echo 'Hello from sandbox!'")
            print(f"✅ Command executed: {result.stdout.strip()}")

            # Test file operations
            await client.write_file(sandbox_id, "/tmp/test.txt", "Hello World!")
            content = await client.read_file(sandbox_id, "/tmp/test.txt")
            print(f"✅ File operations work: {content.strip()}")

        print(f"✅ {backend_name} backend test passed!")
        return True

    except Exception as e:
        print(f"❌ {backend_name} backend test failed: {e}")
        return False

async def main():
    print("🚀 Testing OpenManus Sandbox Backends\n")

    results = {}

    # Test Docker (should always work)
    results['docker'] = await test_backend('docker')

    # Test GitPod if configured
    if os.getenv('GITPOD_TOKEN'):
        gitpod_config = {
            'gitpod_url': os.getenv('GITPOD_URL', 'http://localhost'),
            'gitpod_token': os.getenv('GITPOD_TOKEN')
        }
        results['gitpod'] = await test_backend('gitpod', gitpod_config)
    else:
        print("⏭️  Skipping GitPod test (no GITPOD_TOKEN)")

    # Test E2B if configured
    if os.getenv('E2B_API_KEY'):
        e2b_config = {
            'api_key': os.getenv('E2B_API_KEY'),
            'template': os.getenv('E2B_TEMPLATE', 'base')
        }
        results['e2b'] = await test_backend('e2b', e2b_config)
    else:
        print("⏭️  Skipping E2B test (no E2B_API_KEY)")

    # Summary
    print("\n📊 Test Results:")
    for backend, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {backend}: {status}")

    successful = sum(results.values())
    total = len(results)
    print(f"\n🎯 {successful}/{total} backends working")

    if successful > 0:
        print("\n🎉 OpenManus sandbox backends are ready to use!")
    else:
        print("\n⚠️  No sandbox backends are working. Check your configuration.")

if __name__ == "__main__":
    asyncio.run(main())
EOF

    chmod +x ./test_sandbox_backends.py

    log_info "Running backend tests..."
    python3 ./test_sandbox_backends.py
}

# Main setup flow
main() {
    echo "Choose sandbox backends to setup:"
    echo "1) Docker (local, free)"
    echo "2) GitPod self-hosted (free, requires setup)"
    echo "3) E2B (cloud, requires API key)"
    echo "4) All backends"
    echo "5) Test existing backends"
    echo "6) Create example config only"

    read -p "Enter your choice (1-6): " choice

    case $choice in
        1)
            check_requirements
            setup_docker
            create_example_config
            ;;
        2)
            check_requirements
            setup_gitpod
            create_example_config
            ;;
        3)
            setup_e2b
            create_example_config
            ;;
        4)
            check_requirements
            setup_docker
            setup_gitpod
            setup_e2b
            create_example_config
            test_backends
            ;;
        5)
            test_backends
            ;;
        6)
            create_example_config
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac

    echo
    log_success "Setup complete!"
    log_info "Next steps:"
    echo "  1. Copy sandbox-backends-example.toml to config/config.toml"
    echo "  2. Update API keys and URLs in the config"
    echo "  3. Set environment variables if needed"
    echo "  4. Run: python test_sandbox_backends.py"
}

# Run main function
main "$@"
