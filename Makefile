# OpenManus Makefile

.PHONY: help install test run setup clean dev docker docker-build docker-up docker-down deploy info

# Default target
help:
	@echo "🤖 OpenManus - Multi-Agent AI Framework"
	@echo "========================================"
	@echo ""
	@echo "Development Commands:"
	@echo "  install          - Install all dependencies"
	@echo "  setup            - Setup configuration files"
	@echo "  test             - Run tests"
	@echo "  run              - Run main agent"
	@echo "  run-mcp          - Run with MCP support"
	@echo "  run-flow         - Run multi-agent flow"
	@echo "  run-fastapi      - Run FastAPI web interface"
	@echo "  run-chainlit     - Run Chainlit UI"
	@echo "  dev              - Start in development mode"
	@echo "  clean            - Clean up generated files"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-build     - Build Docker image"
	@echo "  docker-up        - Start services with docker-compose"
	@echo "  docker-down      - Stop services"
	@echo "  docker-logs      - View docker logs"
	@echo "  docker-restart   - Restart services"
	@echo ""
	@echo "Deployment Commands:"
	@echo "  deploy-prod      - Deploy to production"
	@echo "  deploy-staging   - Deploy to staging"
	@echo "  validate         - Validate installation"
	@echo ""
	@echo "Other Commands:"
	@echo "  info             - Show project information"
	@echo "  quickstart       - Quick start (install + setup + validate)"
	@echo ""

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed!"

# Setup configuration
setup:
	@echo "⚙️ Setting up configuration..."
	@test -f .env || cp .env.example .env && echo "✅ Created .env file (please edit with your keys)"
	@test -f config/config.toml || cp config/config.example.toml config/config.toml && echo "✅ Created config.toml (please edit with your keys)"
	@echo "⚠️  Please edit .env and config/config.toml with your API keys before running"

# Run main agent
run:
	@echo "🚀 Starting OpenManus main agent..."
	python main.py

# Run with MCP
run-mcp:
	@echo "🚀 Starting OpenManus with MCP..."
	python run_mcp.py

# Run flow
run-flow:
	@echo "🚀 Starting OpenManus multi-agent flow..."
	python run_flow.py

# Run FastAPI
run-fastapi:
	@echo "🚀 Starting FastAPI web interface..."
	python fastapi_standalone.py --host 0.0.0.0 --port 8000

# Run Chainlit
run-chainlit:
	@echo "🚀 Starting Chainlit UI..."
	python run_chainlit.py

# Development mode
dev:
	@echo "🔧 Starting in development mode..."
	ENV_MODE=LOCAL python main.py

# Run tests
test:
	@echo "🧪 Running tests..."
	pytest tests/ -v

# Docker build
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t openmanus:latest .

# Docker compose up
docker-up:
	@echo "🐳 Starting services with docker-compose..."
	docker compose up -d
	@echo "✅ Services started!"
	@echo "📊 Check status: make docker-logs"

# Docker compose down
docker-down:
	@echo "🐳 Stopping services..."
	docker compose down
	@echo "✅ Services stopped!"

# Docker logs
docker-logs:
	@echo "📋 Viewing logs..."
	docker compose logs -f

# Docker restart
docker-restart:
	@echo "🔄 Restarting services..."
	docker compose restart
	@echo "✅ Services restarted!"

# Deploy to production
deploy-prod:
	@echo "🚀 Deploying to production..."
	@test -f .env || (echo "❌ .env file not found! Run 'make setup' first" && exit 1)
	ENV_MODE=PRODUCTION docker compose --profile production up -d
	@echo "✅ Production deployment complete!"

# Deploy to staging
deploy-staging:
	@echo "🚀 Deploying to staging..."
	ENV_MODE=STAGING docker compose up -d
	@echo "✅ Staging deployment complete!"

# Validate installation
validate:
	@echo "🔍 Validating installation..."
	python -c "import pydantic; print('✅ Pydantic installed')"
	python -c "import openai; print('✅ OpenAI installed')"
	python -c "import fastapi; print('✅ FastAPI installed')"
	python -c "from app.agent.manus import Manus; print('✅ Manus agent available')"
	@test -f config/config.toml || (echo "⚠️  config.toml not found - run 'make setup'" && exit 1)
	@echo "✅ Validation complete!"

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	rm -rf .chainlit/
	rm -rf __pycache__/
	rm -rf app/**/__pycache__/
	rm -rf logs/*.log
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Quick start
quickstart: install setup validate
	@echo ""
	@echo "🎉 Quick start complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your API keys"
	@echo "  2. Edit config/config.toml with your settings"
	@echo "  3. Run: make run"

# Show project info
info:
	@echo "📋 OpenManus Project Info"
	@echo "========================="
	@echo ""
	@echo "Project Structure:"
	@echo "  app/                   - Core application code"
	@echo "  config/                - Configuration files"
	@echo "  protocol/              - Protocol implementations (A2A, MCP)"
	@echo "  examples/              - Usage examples"
	@echo "  tests/                 - Test files"
	@echo ""
	@echo "Configuration:"
	@echo "  .env                   - Environment variables"
	@echo "  config/config.toml     - Main configuration"
	@echo "  config/mcp.json        - MCP server configuration"
	@echo ""
	@echo "Documentation:"
	@echo "  README.md              - Main documentation"
	@echo "  DEPLOYMENT.md          - Deployment guide"
	@echo "  INTEGRACAO_CHAINLIT.md - Chainlit integration"
	@echo ""

