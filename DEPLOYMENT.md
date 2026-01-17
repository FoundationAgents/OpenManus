# OpenManus Deployment Guide

This guide covers various deployment options for OpenManus, from local development to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Deployment Options](#deployment-options)
  - [Local Development](#local-development)
  - [Docker](#docker)
  - [Docker Compose](#docker-compose)
  - [Production Deployment](#production-deployment)
- [Environment Variables](#environment-variables)
- [Health Checks](#health-checks)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- Python 3.12 or higher
- Docker (for containerized deployment)
- Docker Compose (for multi-service deployment)
- 2GB RAM minimum (4GB recommended)
- 5GB disk space

### API Keys

You'll need API keys from one or more LLM providers:

- Anthropic (Claude)
- OpenAI (GPT)
- Azure OpenAI
- AWS Bedrock
- Google AI
- Ollama (self-hosted)

## Configuration

### 1. Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Required
ANTHROPIC_API_KEY=your_key_here
# or
OPENAI_API_KEY=your_key_here

# Optional
ENV_MODE=PRODUCTION
PORT=8000
```

### 2. Application Configuration

Copy the example config file:

```bash
cp config/config.example.toml config/config.toml
```

Edit `config/config.toml` with your LLM settings:

```toml
[llm]
model = "claude-3-7-sonnet-20250219"
base_url = "https://api.anthropic.com/v1/"
api_key = "YOUR_API_KEY"
max_tokens = 8192
temperature = 0.0
```

### 3. MCP Configuration (Optional)

If using MCP (Model Context Protocol):

```bash
cp config/mcp.example.json config/mcp.json
```

Edit `config/mcp.json` with your MCP servers.

## Deployment Options

### Local Development

#### Using the Start Script

The easiest way to run OpenManus:

```bash
# Main agent mode (default)
./start.sh main

# With MCP support
./start.sh mcp

# Multi-agent flow
./start.sh flow

# Web interface
./start.sh fastapi

# Chainlit UI
./start.sh chainlit

# A2A protocol server
./start.sh a2a
```

#### Manual Start

```bash
# Activate virtual environment
source .venv/bin/activate

# Run specific mode
python main.py                    # Main agent
python run_mcp.py                 # MCP mode
python run_flow.py                # Flow mode
python fastapi_standalone.py      # FastAPI
python run_chainlit.py            # Chainlit
```

### Docker

#### Build the Image

```bash
docker build -t openmanus:latest .
```

#### Run Container

```bash
docker run -d \
  --name openmanus \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your_key \
  -v $(pwd)/config:/app/OpenManus/config:ro \
  -v openmanus-workspace:/app/OpenManus/workspace \
  -v openmanus-logs:/app/OpenManus/logs \
  openmanus:latest
```

#### With Environment File

```bash
docker run -d \
  --name openmanus \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/config:/app/OpenManus/config:ro \
  -v openmanus-workspace:/app/OpenManus/workspace \
  openmanus:latest
```

### Docker Compose

#### Basic Deployment

Start all services:

```bash
docker-compose up -d
```

Start specific services:

```bash
# Only main service
docker-compose up -d openmanus

# Main + FastAPI
docker-compose up -d openmanus fastapi

# Full stack with UI
docker-compose up -d openmanus fastapi chainlit
```

#### With Nginx (Production)

```bash
# Start with nginx reverse proxy
docker-compose --profile production up -d
```

#### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f openmanus
```

#### Stop Services

```bash
docker-compose down

# Remove volumes too
docker-compose down -v
```

### Production Deployment

#### 1. Prepare Environment

```bash
# Clone repository
git clone https://github.com/FoundationAgents/OpenManus.git
cd OpenManus

# Copy and configure environment
cp .env.example .env
cp config/config.example.toml config/config.toml

# Edit files with production values
nano .env
nano config/config.toml
```

#### 2. SSL Configuration (Optional)

For HTTPS, place your SSL certificates:

```bash
mkdir -p ssl
cp your-cert.pem ssl/cert.pem
cp your-key.pem ssl/key.pem
```

Update `nginx.conf` to enable HTTPS section.

#### 3. Deploy with Docker Compose

```bash
# Build images
docker-compose build

# Start services
docker-compose --profile production up -d

# Check status
docker-compose ps
```

#### 4. Set Up Monitoring

Configure health check monitoring:

```bash
# Health check endpoint
curl http://localhost/health

# Readiness check
curl http://localhost/readiness

# Status endpoint
curl http://localhost/status
```

## Environment Variables

### Core Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENV_MODE` | Environment mode (LOCAL/PRODUCTION) | LOCAL | No |
| `HOST` | Server host | 0.0.0.0 | No |
| `PORT` | Server port | 8000 | No |

### LLM Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes* |
| `OPENAI_API_KEY` | OpenAI API key | Yes* |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI key | Yes* |
| `LLM_MODEL` | Model name | No |
| `LLM_BASE_URL` | API base URL | No |

*At least one LLM provider key is required.

### Sandbox Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_SANDBOX` | Enable sandbox | false |
| `SANDBOX_BACKEND` | Backend type (docker/gitpod/e2b) | docker |
| `SANDBOX_IMAGE` | Docker image | python:3.12-slim |
| `GITPOD_URL` | GitPod URL | - |
| `GITPOD_TOKEN` | GitPod API token | - |
| `E2B_API_KEY` | E2B API key | - |
| `DAYTONA_API_KEY` | Daytona API key | - |

## Health Checks

### Endpoints

- `/health` - Basic health check
- `/readiness` - Readiness probe (checks dependencies)
- `/status` - Detailed status information

### Using with Docker

Docker health check is built into the image:

```bash
docker inspect --format='{{.State.Health.Status}}' openmanus
```

### Using with Kubernetes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /readiness
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

## Monitoring

### Logs

#### Docker Compose

```bash
# All services
docker-compose logs -f

# Specific service with timestamps
docker-compose logs -f --timestamps openmanus

# Last 100 lines
docker-compose logs --tail=100 openmanus
```

#### Production Logging

Logs are stored in:
- Docker: `/app/OpenManus/logs/`
- Local: `./logs/`

Configure log level with `LOG_LEVEL` environment variable:
- `DEBUG` - Detailed debugging information
- `INFO` - General information (default)
- `WARNING` - Warning messages
- `ERROR` - Error messages only

### Metrics

Monitor these key metrics:

- Container health status
- Memory usage
- CPU usage
- Response times
- Error rates

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Check what's using the port
lsof -i :8000

# Change port in .env
PORT=8001
```

#### API Key Issues

```bash
# Verify environment variables
docker-compose exec openmanus env | grep API_KEY

# Check config file
docker-compose exec openmanus cat config/config.toml
```

#### Permission Issues

```bash
# Fix volume permissions
sudo chown -R $(id -u):$(id -g) workspace logs

# Or run with proper user
docker-compose run --user $(id -u):$(id -g) openmanus
```

#### Container Won't Start

```bash
# Check logs
docker-compose logs openmanus

# Check config syntax
docker-compose config

# Rebuild images
docker-compose build --no-cache openmanus
```

#### Out of Memory

```bash
# Increase Docker memory limit
# In docker-compose.yml, add:
services:
  openmanus:
    mem_limit: 2g
```

### Debug Mode

Enable debug logging:

```bash
# In .env
ENV_MODE=LOCAL
LOG_LEVEL=DEBUG

# Or in docker-compose
docker-compose up openmanus
```

### Getting Help

1. Check logs: `docker-compose logs -f`
2. Verify configuration: `docker-compose config`
3. Check health: `curl http://localhost/health`
4. Review documentation: [README.md](README.md)
5. Open issue: [GitHub Issues](https://github.com/FoundationAgents/OpenManus/issues)

## Security Best Practices

1. **Never commit secrets**: Keep `.env` and `config/config.toml` out of version control
2. **Use environment variables**: Prefer environment variables over hardcoded values
3. **Enable HTTPS**: Use SSL certificates in production
4. **Limit exposure**: Use firewall rules to restrict access
5. **Update regularly**: Keep dependencies and base images updated
6. **Monitor logs**: Set up log monitoring and alerting
7. **Resource limits**: Configure memory and CPU limits

## Scaling

### Horizontal Scaling

For high availability, run multiple instances:

```yaml
services:
  openmanus:
    deploy:
      replicas: 3
```

Use a load balancer (nginx) to distribute traffic.

### Vertical Scaling

Increase resources per container:

```yaml
services:
  openmanus:
    mem_limit: 4g
    cpus: 2
```

## Backup and Recovery

### Backup Important Data

```bash
# Backup workspace
docker cp openmanus:/app/OpenManus/workspace ./backup/workspace

# Backup configuration
cp config/config.toml ./backup/
cp .env ./backup/

# Backup logs
docker cp openmanus:/app/OpenManus/logs ./backup/logs
```

### Restore

```bash
# Restore workspace
docker cp ./backup/workspace openmanus:/app/OpenManus/workspace

# Restore configuration
cp ./backup/config.toml config/
cp ./backup/.env .
```

## Additional Resources

- [Main README](README.md)
- [Chainlit Integration](INTEGRACAO_CHAINLIT.md)
- [Sandbox Implementation](SANDBOX_IMPLEMENTATION.md)
- [GitHub Repository](https://github.com/FoundationAgents/OpenManus)
- [Discord Community](https://discord.gg/DYn29wFk9z)
