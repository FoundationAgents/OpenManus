#!/bin/bash
# Startup script for OpenManus

set -e

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

# Check if .env file exists
if [ ! -f .env ]; then
    log_warning ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        log_info "Please edit .env file with your configuration"
        exit 1
    else
        log_error ".env.example not found"
        exit 1
    fi
fi

# Load environment variables
set -a
source .env
set +a

# Check if config.toml exists
if [ ! -f config/config.toml ]; then
    log_warning "config/config.toml not found. Creating from example..."
    if [ -f config/config.example.toml ]; then
        cp config/config.example.toml config/config.toml
        log_info "Please edit config/config.toml with your API keys"
        exit 1
    else
        log_error "config.example.toml not found"
        exit 1
    fi
fi

# Parse arguments
MODE=${1:-main}

log_info "Starting OpenManus in mode: $MODE"

case "$MODE" in
    main)
        log_info "Starting OpenManus main agent..."
        python main.py "${@:2}"
        ;;
    mcp)
        log_info "Starting OpenManus with MCP support..."
        python run_mcp.py "${@:2}"
        ;;
    flow)
        log_info "Starting OpenManus multi-agent flow..."
        python run_flow.py "${@:2}"
        ;;
    fastapi)
        log_info "Starting FastAPI web interface..."
        python fastapi_standalone.py --host 0.0.0.0 --port 8000 "${@:2}"
        ;;
    chainlit)
        log_info "Starting Chainlit UI..."
        python run_chainlit.py --host 0.0.0.0 --port 8001 "${@:2}"
        ;;
    a2a)
        log_info "Starting A2A protocol server..."
        python -m protocol.a2a.app.main --host 0.0.0.0 --port 10000 "${@:2}"
        ;;
    sandbox)
        log_info "Starting OpenManus with Daytona sandbox..."
        python sandbox_main.py "${@:2}"
        ;;
    mcp-server)
        log_info "Starting MCP server..."
        python run_mcp_server.py "${@:2}"
        ;;
    *)
        log_error "Unknown mode: $MODE"
        echo ""
        echo "Usage: $0 [mode] [options]"
        echo ""
        echo "Available modes:"
        echo "  main       - Start main Manus agent (default)"
        echo "  mcp        - Start with MCP protocol support"
        echo "  flow       - Start multi-agent flow mode"
        echo "  fastapi    - Start FastAPI web interface"
        echo "  chainlit   - Start Chainlit UI"
        echo "  a2a        - Start A2A protocol server"
        echo "  sandbox    - Start with Daytona sandbox"
        echo "  mcp-server - Start MCP server"
        echo ""
        exit 1
        ;;
esac
