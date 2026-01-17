#!/bin/bash
# Deploy GitPod Self-Hosted for OpenManus

set -e

echo "🚀 Deploying GitPod Self-Hosted for OpenManus"
echo "=" | head -c 50 && echo

# Configuration
GITPOD_DOMAIN=${GITPOD_DOMAIN:-"gitpod.local"}
GITPOD_DIR="./gitpod-deployment"
REGISTRY_PORT=${REGISTRY_PORT:-5000}

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# Create deployment directory
log_info "Creating GitPod deployment structure..."
mkdir -p $GITPOD_DIR/{config,data,images}

# Create main docker-compose.yml
cat > $GITPOD_DIR/docker-compose.yml << EOF
version: '3.8'

services:
  gitpod:
    image: gitpod/gitpod:latest
    ports:
      - "80:80"
      - "443:443"
      - "22:22"
    volumes:
      - ./data:/var/lib/gitpod
      - ./config:/config
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      GITPOD_DOMAIN: $GITPOD_DOMAIN
      GITPOD_INSTALLATION_LONGNAME: "OpenManus GitPod"
      GITPOD_LICENSE_TYPE: "free"
      GITPOD_AUTH_PROVIDERS: "GitHub"
      GITPOD_DATABASE_HOST: "db"
      GITPOD_DATABASE_PASSWORD: "gitpod123"
      GITPOD_REGISTRY_HOST: "registry:5000"
      GITPOD_MINIO_ENDPOINT: "minio:9000"
      GITPOD_MINIO_ACCESS_KEY: "gitpod"
      GITPOD_MINIO_SECRET_KEY: "gitpod123"
    depends_on:
      - db
      - registry
      - minio
    restart: unless-stopped
    networks:
      - gitpod-network

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: gitpod
      MYSQL_USER: gitpod
      MYSQL_PASSWORD: gitpod123
    volumes:
      - db-data:/var/lib/mysql
    restart: unless-stopped
    networks:
      - gitpod-network

  registry:
    image: registry:2
    ports:
      - "$REGISTRY_PORT:5000"
    volumes:
      - registry-data:/var/lib/registry
    environment:
      REGISTRY_STORAGE_DELETE_ENABLED: "true"
    restart: unless-stopped
    networks:
      - gitpod-network

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
    networks:
      - gitpod-network

  # Optional: Traefik for SSL termination
  traefik:
    image: traefik:v2.10
    command:
      - --api.insecure=true
      - --providers.docker=true
      - --providers.docker.exposedbydefault=false
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --certificatesresolvers.letsencrypt.acme.httpchallenge=true
      - --certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web
      - --certificatesresolvers.letsencrypt.acme.email=admin@$GITPOD_DOMAIN
      - --certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json
    ports:
      - "8080:8080"  # Traefik dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik-data:/letsencrypt
    networks:
      - gitpod-network

volumes:
  db-data:
  registry-data:
  minio-data:
  traefik-data:

networks:
  gitpod-network:
    driver: bridge
EOF

# Create GitPod configuration
cat > $GITPOD_DIR/config/gitpod.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: gitpod-config
data:
  domain: $GITPOD_DOMAIN
  installation:
    longname: "OpenManus GitPod"
    shortname: "OpenManus"
  auth:
    providers:
      - id: "github"
        host: "github.com"
        type: "GitHub"
        clientId: "your-github-app-client-id"
        clientSecret: "your-github-app-client-secret"
  workspace:
    runtime:
      containerd:
        address: "/run/k3s/containerd/containerd.sock"
        namespace: "k8s.io"
    templates:
      default:
        spec:
          image: "gitpod/workspace-full:latest"
      python:
        spec:
          image: "gitpod/workspace-python:latest"
      openmanus:
        spec:
          image: "localhost:5000/openmanus-sandbox:latest"
EOF

# Build OpenManus sandbox image
log_info "Building OpenManus sandbox image..."
cat > $GITPOD_DIR/images/Dockerfile.openmanus << 'EOF'
FROM gitpod/workspace-full-vnc:latest

# Switch to root for installations
USER root

# Install system packages
RUN apt-get update && apt-get install -y \
    google-chrome-stable \
    chromium-browser \
    tigervnc-standalone-server \
    tigervnc-common \
    supervisor \
    xfce4 \
    xfce4-terminal \
    && rm -rf /var/lib/apt/lists/*

# Switch back to gitpod user
USER gitpod

# Install Python packages
RUN pip install --user --no-cache-dir \
    playwright \
    selenium \
    browser-use \
    httpx \
    beautifulsoup4 \
    requests \
    aiofiles \
    asyncio

# Install Playwright browsers
RUN python -m playwright install chromium

# Setup VNC configuration
RUN mkdir -p ~/.vnc && \
    echo '#!/bin/bash\nexport XKL_XMODMAP_DISABLE=1\nexport XDG_CURRENT_DESKTOP="XFCE"\nexport XDG_SESSION_DESKTOP="xfce"\nunset SESSION_MANAGER\nstartxfce4 &' > ~/.vnc/xstartup && \
    chmod +x ~/.vnc/xstartup

# Create supervisor config directory
RUN mkdir -p ~/.config/supervisor

# Copy supervisor config
COPY --chown=gitpod:gitpod supervisor.conf ~/.config/supervisor/

# Expose ports
EXPOSE 6080 8080 9222

# Default command
CMD ["/usr/bin/supervisord", "-c", "/home/gitpod/.config/supervisor/supervisor.conf"]
EOF

# Create supervisor config for the image
cat > $GITPOD_DIR/images/supervisor.conf << 'EOF'
[supervisord]
nodaemon=true
user=gitpod
pidfile=/tmp/supervisord.pid
logfile=/tmp/supervisord.log

[unix_http_server]
file=/tmp/supervisor.sock
chown=gitpod:gitpod

[supervisorctl]
serverurl=unix:///tmp/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:vnc]
command=vncserver :1 -fg -geometry 1024x768 -depth 24 -localhost no -SecurityTypes None
autorestart=true
stdout_logfile=/tmp/vnc.log
stderr_logfile=/tmp/vnc_error.log
environment=HOME="/home/gitpod",USER="gitpod",DISPLAY=":1"

[program:chrome-debug]
command=google-chrome --remote-debugging-port=9222 --no-sandbox --disable-dev-shm-usage --disable-gpu --disable-software-rasterizer --run-all-compositor-stages-before-draw --no-first-run
autostart=false
autorestart=true
stdout_logfile=/tmp/chrome.log
stderr_logfile=/tmp/chrome_error.log
environment=DISPLAY=":1"
EOF

# Build the image
log_info "Building OpenManus sandbox Docker image..."
cd $GITPOD_DIR/images
docker build -t openmanus-sandbox:latest -f Dockerfile.openmanus .
docker tag openmanus-sandbox:latest localhost:$REGISTRY_PORT/openmanus-sandbox:latest
cd ..

# Create startup script
cat > $GITPOD_DIR/start-gitpod.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting GitPod for OpenManus..."

# Start services
docker-compose up -d

echo "⏳ Waiting for services to start..."
sleep 30

# Push OpenManus image to local registry
echo "📦 Pushing OpenManus sandbox image to registry..."
docker push localhost:5000/openmanus-sandbox:latest

echo "✅ GitPod is starting up!"
echo "📊 Monitor logs: docker-compose logs -f"
echo "🌐 Access GitPod: http://localhost (or http://$GITPOD_DOMAIN)"
echo "🗃️  Registry: http://localhost:5000"
echo "💾 MinIO: http://localhost:9001 (gitpod/gitpod123)"
echo "🔍 Traefik: http://localhost:8080"
EOF

chmod +x $GITPOD_DIR/start-gitpod.sh

# Create stop script
cat > $GITPOD_DIR/stop-gitpod.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping GitPod..."
docker-compose down
echo "✅ GitPod stopped"
EOF

chmod +x $GITPOD_DIR/stop-gitpod.sh

# Create management script
cat > $GITPOD_DIR/manage-gitpod.sh << 'EOF'
#!/bin/bash

case "$1" in
  start)
    ./start-gitpod.sh
    ;;
  stop)
    ./stop-gitpod.sh
    ;;
  restart)
    ./stop-gitpod.sh
    sleep 5
    ./start-gitpod.sh
    ;;
  logs)
    docker-compose logs -f ${2:-gitpod}
    ;;
  status)
    docker-compose ps
    ;;
  clean)
    echo "🧹 Cleaning up GitPod data..."
    docker-compose down -v
    docker system prune -f
    echo "✅ Cleanup complete"
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|logs|status|clean}"
    echo "  logs [service] - Show logs for specific service"
    exit 1
    ;;
esac
EOF

chmod +x $GITPOD_DIR/manage-gitpod.sh

# Create README
cat > $GITPOD_DIR/README.md << EOF
# GitPod Self-Hosted for OpenManus

This directory contains a complete GitPod self-hosted setup optimized for OpenManus sandbox usage.

## Quick Start

1. **Start GitPod:**
   \`\`\`bash
   ./start-gitpod.sh
   \`\`\`

2. **Access GitPod:**
   - Web UI: http://localhost
   - Registry: http://localhost:5000
   - MinIO: http://localhost:9001 (gitpod/gitpod123)

## Management

\`\`\`bash
# Start services
./manage-gitpod.sh start

# Stop services
./manage-gitpod.sh stop

# View logs
./manage-gitpod.sh logs

# Check status
./manage-gitpod.sh status

# Clean up everything
./manage-gitpod.sh clean
\`\`\`

## Configuration for OpenManus

Add this to your \`config/config.toml\`:

\`\`\`toml
[sandbox]
backend = "gitpod"
gitpod_url = "http://localhost"
gitpod_token = "your_api_token_here"
image = "localhost:5000/openmanus-sandbox:latest"
\`\`\`

## Getting API Token

1. Access GitPod at http://localhost
2. Sign in with GitHub
3. Go to Settings → Access Tokens
4. Create new token with workspace permissions
5. Copy token to your config

## Troubleshooting

- **Port conflicts**: Change ports in docker-compose.yml
- **Permission issues**: Ensure Docker daemon is running
- **Memory issues**: Increase Docker memory limit
- **GitHub auth**: Configure GitHub OAuth app

## Architecture

- **GitPod**: Main workspace service
- **Registry**: Local Docker registry for custom images
- **MinIO**: Object storage for workspaces
- **MySQL**: Database for GitPod metadata
- **Traefik**: Reverse proxy and SSL termination

EOF

log_success "GitPod deployment created in $GITPOD_DIR/"
log_info "Next steps:"
echo "  1. cd $GITPOD_DIR"
echo "  2. ./start-gitpod.sh"
echo "  3. Configure GitHub OAuth (see README.md)"
echo "  4. Get API token from http://localhost"
echo "  5. Update OpenManus config with token"

log_warning "Note: This is a development setup. For production, configure SSL, authentication, and security properly."
