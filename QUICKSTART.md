# OpenManus Quick Deployment Reference

## 🚀 Quick Start (Local)

```bash
# 1. Setup
make install
make setup

# 2. Edit configuration
nano .env              # Add your API keys
nano config/config.toml  # Configure LLM settings

# 3. Run
make run               # or: python main.py
```

## 🐳 Docker Deployment

```bash
# Quick deploy
docker compose up -d

# With nginx (production)
docker compose --profile production up -d

# View logs
docker compose logs -f openmanus

# Stop
docker compose down
```

## 🔧 Available Modes

| Mode | Command | Description |
|------|---------|-------------|
| Main | `make run` or `./start.sh main` | Main Manus agent |
| MCP | `make run-mcp` or `./start.sh mcp` | With MCP protocol |
| Flow | `make run-flow` or `./start.sh flow` | Multi-agent flow |
| FastAPI | `make run-fastapi` or `./start.sh fastapi` | Web API |
| Chainlit | `make run-chainlit` or `./start.sh chainlit` | UI frontend |
| A2A | `./start.sh a2a` | A2A protocol server |

## 🔑 Required Environment Variables

```bash
# Minimal setup
ANTHROPIC_API_KEY=sk-ant-...  # or OPENAI_API_KEY
ENV_MODE=LOCAL                 # or PRODUCTION
```

## 📋 Health Checks

- `http://localhost:8000/health` - Basic health
- `http://localhost:8000/readiness` - Ready for traffic
- `http://localhost:8000/status` - Detailed status

## 🛠️ Makefile Commands

```bash
make help           # Show all commands
make install        # Install dependencies
make setup          # Create config files
make validate       # Validate installation
make docker-build   # Build Docker image
make docker-up      # Start services
make deploy-prod    # Deploy to production
make clean          # Clean up
```

## 📁 Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (API keys, ports) |
| `config/config.toml` | Main configuration (LLM, sandbox, browser) |
| `config/mcp.json` | MCP server configuration |
| `docker-compose.yml` | Docker services orchestration |
| `nginx.conf` | Reverse proxy configuration |

## 🌐 Service Ports

| Service | Port | URL |
|---------|------|-----|
| Main/FastAPI | 8000 | http://localhost:8000 |
| Chainlit | 8001 | http://localhost:8001 |
| A2A Server | 10000 | http://localhost:10000 |
| Nginx | 80/443 | http://localhost |

## 🔒 Security Checklist

- [ ] `.env` file is in `.gitignore`
- [ ] API keys are set as environment variables
- [ ] `config/config.toml` is in `.gitignore`
- [ ] SSL certificates configured for production
- [ ] Firewall rules configured
- [ ] Log monitoring enabled
- [ ] Resource limits set in docker-compose.yml

## 📚 Documentation

- [Main README](README.md) - Getting started
- [DEPLOYMENT.md](DEPLOYMENT.md) - Full deployment guide
- [INTEGRACAO_CHAINLIT.md](INTEGRACAO_CHAINLIT.md) - Chainlit integration
- [SANDBOX_IMPLEMENTATION.md](SANDBOX_IMPLEMENTATION.md) - Sandbox setup

## 🐛 Troubleshooting

```bash
# Check logs
docker compose logs -f

# Validate config
make validate

# Test health
curl http://localhost:8000/health

# Check environment
env | grep -E "API_KEY|ENV_MODE|LLM"

# Restart services
docker compose restart
```

## 💡 Common Issues

| Issue | Solution |
|-------|----------|
| Port already in use | Change `PORT` in `.env` |
| API key not found | Check `.env` and `config/config.toml` |
| Container won't start | Check `docker compose logs openmanus` |
| Permission denied | `chmod +x start.sh` |
| Out of memory | Increase Docker memory limit |

## 🔄 Update Procedure

```bash
# 1. Pull latest changes
git pull origin main

# 2. Update dependencies
make install

# 3. Restart services
docker compose restart
# or
docker compose up -d --build
```

---

For detailed information, see [DEPLOYMENT.md](DEPLOYMENT.md)
