# Docker Instructions for OpenManus

## Prerequisites

1. Install Docker:
   
- [Docker Desktop for Windows](https://docs.docker.com/docker-for-windows/install/)
- [Docker Desktop for MacOS](https://docs.docker.com/docker-for-mac/install/)
- [Docker Engine for Linux](https://docs.docker.com/engine/install/)

## Quick Start

1. Create a new directory for OpenManus and navigate to it:
   ```bash
   mkdir OpenManus
   cd OpenManus
   ```

2. Download the Dockerfile and docker-compose.yml:
   ```bash
   # Download Dockerfile
   curl -O https://raw.githubusercontent.com/mannaandpoem/OpenManus/refs/heads/main/Docker/Dockerfile
   
   # Download docker-compose.yml
   curl -O https://raw.githubusercontent.com/mannaandpoem/OpenManus/refs/heads/main/Docker/docker-compose.yml
   ```

3. Create a `.env` file with your configuration:
   ```bash
   touch .env
   ```

4. Edit the `.env` file with the following variables:
   ```
   OPENMANUS_PATH=/path/to/your/openmanus/data
   OPENMANUS_CONFIG=/path/to/your/openmanus/config
   TZ=Your/Timezone
   ```

5. Run OpenManus using Docker Compose:
   ```bash
   docker-compose up -d
   ```

6. View logs to monitor the application:
   ```bash
   docker-compose logs -f
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENMANUS_PATH` | Path to store OpenManus data | `~/.openmanus` |
| `OPENMANUS_CONFIG` | Path to store OpenManus configuration | `~/.openmanus_config` |
| `TZ` | Your timezone | `UTC` |

### Custom Configuration

OpenManus requires a configuration file. The Docker setup will automatically create a default configuration file at `config/config.toml` if one doesn't exist. You can customize this file by editing the mounted volume at the location specified by `OPENMANUS_CONFIG` in your `.env` file.

## Advanced Usage

### Running in Development Mode

To run OpenManus in development mode (using `run_flow.py` instead of `main.py`):

```bash
docker-compose run --rm openmanus dev
```

### Building the Docker Image Manually

If you prefer to build the Docker image manually:

```bash
docker build -t openmanus:latest .
```

### Running the Docker Container Manually

```bash
docker run -it --rm \
  -v $(pwd)/data:/app/OpenManus/data \
  -v $(pwd)/config:/app/OpenManus/config \
  -p 8000:8000 \
  openmanus:latest
```

## Troubleshooting

### Container Not Starting

If the container fails to start, check the logs:

```bash
docker-compose logs openmanus
```

### Permission Issues

If you encounter permission issues with mounted volumes:

1. Ensure that the host directories exist and have appropriate permissions
2. Check the ownership of files inside the container:
   ```bash
   docker-compose exec openmanus ls -la /app/OpenManus
   ```

## Updating OpenManus

To update to the latest version of OpenManus:

```bash
# Stop the current container
docker-compose down

# Remove the old image
docker rmi openmanus:latest

# Start the container again (will rebuild with latest code)
docker-compose up -d
```

Since the Dockerfile automatically clones the repository during container startup, this process will pull the latest version of OpenManus from GitHub.

## Security Considerations

- The Docker configuration runs OpenManus as a non-root user (`openmanususer`) for improved security
- Ensure proper file permissions on mounted volumes
