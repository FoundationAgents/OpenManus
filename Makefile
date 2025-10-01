# OpenManus Chainlit Integration Makefile

.PHONY: help install test run setup clean dev

# Default target
help:
	@echo "🤖 OpenManus Chainlit Integration"
	@echo "=================================="
	@echo ""
	@echo "Available targets:"
	@echo "  help       - Show this help message"
	@echo "  install    - Install all dependencies"
	@echo "  setup      - Setup Chainlit configuration"
	@echo "  test       - Run integration tests"
	@echo "  run        - Start Chainlit frontend"
	@echo "  dev        - Start in development mode"
	@echo "  clean      - Clean up generated files"
	@echo ""
	@echo "Examples:"
	@echo "  make install && make setup && make test && make run"
	@echo "  make dev  # For development with auto-reload"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install chainlit uvicorn fastapi websockets aiofiles pydantic openai tenacity loguru boto3 docker structlog tiktoken
	@echo "✅ Dependencies installed!"

# Setup configuration
setup:
	@echo "⚙️ Setting up Chainlit configuration..."
	python run_chainlit.py --config-only
	@echo "✅ Configuration setup complete!"

# Run integration tests
test:
	@echo "🧪 Running integration tests..."
	python examples/test_chainlit_integration.py
	@echo "✅ Tests completed!"

# Start Chainlit frontend
run:
	@echo "🚀 Starting Chainlit frontend..."
	python run_chainlit.py

# Development mode with auto-reload
dev:
	@echo "🔧 Starting in development mode..."
	python run_chainlit.py --debug --auto-reload

# Custom host and port
run-custom:
	@echo "🌐 Starting on custom host/port..."
	python run_chainlit.py --host 0.0.0.0 --port 8080

# Headless mode (no browser auto-open)
run-headless:
	@echo "🔇 Starting in headless mode..."
	python run_chainlit.py --headless

# Clean up generated files
clean:
	@echo "🧹 Cleaning up..."
	rm -rf .chainlit/
	rm -rf __pycache__/
	rm -rf app/frontend/__pycache__/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	@echo "✅ Cleanup complete!"

# Quick start (install + setup + test + run)
quickstart: install setup test
	@echo ""
	@echo "🎉 Quick start complete! Starting frontend..."
	@make run

# Validate installation
validate:
	@echo "🔍 Validating installation..."
	python -c "import chainlit; print('✅ Chainlit:', chainlit.__version__)"
	python -c "import fastapi; print('✅ FastAPI:', fastapi.__version__)"
	python -c "import uvicorn; print('✅ Uvicorn:', uvicorn.__version__)"
	python -c "from app.frontend.chainlit_app import ChainlitOpenManus; print('✅ OpenManus integration ready')"
	@echo "✅ Validation complete!"

# Show project info
info:
	@echo "📋 OpenManus Chainlit Integration Info"
	@echo "====================================="
	@echo ""
	@echo "Project Structure:"
	@echo "  app/frontend/          - Frontend integration code"
	@echo "  run_chainlit.py        - Main launcher script"
	@echo "  examples/              - Usage examples and tests"
	@echo ""
	@echo "Key Files:"
	@echo "  app/frontend/chainlit_app.py     - Main Chainlit application"
	@echo "  app/frontend/chainlit_config.py  - Configuration management"
	@echo "  app/frontend/README.md           - Detailed documentation"
	@echo ""
	@echo "Quick Commands:"
	@echo "  make quickstart        - Install, setup, test, and run"
	@echo "  make dev              - Development mode with auto-reload"
	@echo "  python run_chainlit.py --help  - See all options"
