# Production Deployment Checklist

Use this checklist to ensure a safe and successful production deployment of OpenManus.

## Pre-Deployment

### Configuration
- [ ] Created `.env` file from `.env.example`
- [ ] Set all required API keys (ANTHROPIC_API_KEY or OPENAI_API_KEY)
- [ ] Set `ENV_MODE=PRODUCTION` in `.env`
- [ ] Created `config/config.toml` from example
- [ ] Configured LLM settings in `config/config.toml`
- [ ] Set up MCP servers in `config/mcp.json` (if using MCP)
- [ ] Reviewed and adjusted resource limits (memory, CPU)

### Security
- [ ] API keys stored securely (environment variables, not in code)
- [ ] `.env` file is in `.gitignore`
- [ ] `config/config.toml` is in `.gitignore`
- [ ] SSL certificates obtained and placed in `ssl/` directory
- [ ] Nginx HTTPS configuration enabled and tested
- [ ] Firewall rules configured (only necessary ports open)
- [ ] Strong passwords set for all services
- [ ] Security headers configured in nginx.conf

### Infrastructure
- [ ] Server meets minimum requirements (2GB RAM, 5GB disk)
- [ ] Docker and Docker Compose installed
- [ ] Server has internet access for pulling images
- [ ] Backup storage configured
- [ ] Monitoring system in place
- [ ] Log aggregation configured

### Testing
- [ ] Validated all configuration files (`make validate`)
- [ ] Tested Docker build locally (`make docker-build`)
- [ ] Tested Docker Compose locally (`make docker-up`)
- [ ] Verified health check endpoints work
- [ ] Tested with sample requests
- [ ] Load testing completed (if applicable)

## Deployment Steps

### 1. Prepare Server
```bash
# SSH into production server
ssh user@production-server

# Create deployment directory
mkdir -p /opt/openmanus
cd /opt/openmanus
```

### 2. Clone Repository
```bash
# Clone the repository
git clone https://github.com/FoundationAgents/OpenManus.git
cd OpenManus

# Or update existing installation
git pull origin main
```

### 3. Configure
```bash
# Create configuration files
cp .env.example .env
cp config/config.example.toml config/config.toml

# Edit with production values
nano .env
nano config/config.toml
```

### 4. Deploy
```bash
# Build images
docker compose build

# Start services (without nginx)
docker compose up -d

# Or with nginx (recommended for production)
docker compose --profile production up -d
```

### 5. Verify
```bash
# Check service status
docker compose ps

# Check logs
docker compose logs -f openmanus

# Test health endpoints
curl http://localhost/health
curl http://localhost/readiness
curl http://localhost/status

# Test main functionality
# (Use appropriate endpoint for your setup)
```

## Post-Deployment

### Monitoring
- [ ] Verify all services are running (`docker compose ps`)
- [ ] Check health endpoints are responding
- [ ] Review logs for errors (`docker compose logs`)
- [ ] Verify metrics collection (if configured)
- [ ] Test alert notifications (if configured)

### Backup
- [ ] Verify automated backups are running
- [ ] Test backup restoration procedure
- [ ] Document backup locations
- [ ] Schedule regular backup verification

### Documentation
- [ ] Update deployment documentation with any changes
- [ ] Document any custom configurations
- [ ] Create runbook for common operations
- [ ] Share credentials with team (securely)

### Team Notification
- [ ] Notify team of successful deployment
- [ ] Share access URLs
- [ ] Provide troubleshooting contacts
- [ ] Schedule post-deployment review

## Rollback Plan

If issues occur, follow these steps:

### Quick Rollback
```bash
# Stop services
docker compose down

# Switch to previous version
git checkout <previous-tag>

# Restart services
docker compose up -d
```

### Full Rollback
```bash
# Stop and remove everything
docker compose down -v

# Restore from backup
./restore-backup.sh <backup-date>

# Restart services
docker compose up -d
```

## Common Issues & Solutions

### Service won't start
```bash
# Check logs
docker compose logs openmanus

# Common causes:
# - Port already in use: Change PORT in .env
# - Missing API key: Check .env file
# - Config error: Validate config.toml syntax
```

### Health check failing
```bash
# Check container status
docker compose ps

# Check health endpoint directly
docker compose exec openmanus curl http://localhost:8000/health

# Common causes:
# - Application not ready: Wait 30 seconds
# - Configuration error: Check logs
# - Resource limits: Check memory/CPU
```

### High memory usage
```bash
# Check resource usage
docker stats

# Solutions:
# - Increase memory limits in docker-compose.yml
# - Scale down replicas
# - Optimize configuration
```

## Maintenance Windows

### Regular Maintenance
- [ ] Schedule weekly maintenance window
- [ ] Plan for dependency updates
- [ ] Schedule security patch reviews
- [ ] Plan capacity reviews

### Update Procedure
1. Announce maintenance window
2. Create backup
3. Test update in staging
4. Apply update in production
5. Verify functionality
6. Monitor for issues

## Performance Optimization

### After First Week
- [ ] Review logs for errors
- [ ] Analyze response times
- [ ] Check resource utilization
- [ ] Optimize configuration based on usage
- [ ] Scale services if needed

### Ongoing
- [ ] Weekly log review
- [ ] Monthly performance review
- [ ] Quarterly capacity planning
- [ ] Regular security updates

## Support Contacts

| Issue Type | Contact | Method |
|------------|---------|--------|
| Technical Issues | DevOps Team | Slack/Email |
| Security Issues | Security Team | Emergency line |
| API Issues | API Support | Support Portal |

## Success Criteria

Deployment is considered successful when:
- [ ] All services show "healthy" status
- [ ] Health endpoints return 200 OK
- [ ] Test requests complete successfully
- [ ] No errors in logs (first 5 minutes)
- [ ] Resource usage is within expected limits
- [ ] Monitoring alerts are silent

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| DevOps | | | |
| Security | | | |
| Product Owner | | | |

---

**Deployment Date:** ________________

**Deployment Version:** ________________

**Deployed By:** ________________

**Notes:**
