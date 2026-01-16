# Aegis.net — Docker Deployment Guide

## Quick Start

### Local Development

1. **Clone and navigate to project:**
   ```bash
   cd Aegis.net
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services:**
   ```bash
   docker-compose up
   ```

4. **Access services:**
   - Control Plane API: http://localhost:8000
   - Nginx Edge: http://localhost:80
   - API Docs: http://localhost:8000/docs

### Production Deployment

1. **On your server, copy .env.example to .env:**
   ```bash
   cp .env.example .env
   nano .env  # Configure production values
   ```

2. **Run deployment script:**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh production
   ```

3. **Verify deployment:**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   ```

## Architecture

### Containers

- **aegis-control-plane** — FastAPI application (port 8000)
- **aegis-nginx-edge** — Nginx reverse proxy with rate limiting (ports 80, 443)

### Volumes

- `nginx-configs` — Shared volume for dynamic Nginx configurations
- `nginx-logs` — Nginx access and error logs

### Network

- `aegis-network` — Internal bridge network for service communication

## Environment Variables

Required variables in `.env`:

```bash
# Authentication
AUTHORIZED_CLI_KEYS=your-ssh-public-key
WHITELISTED_IPS=127.0.0.1,your-ip

# Security
JWT_SECRET=random-secret-here
SECRET_KEY=another-random-secret

# Configuration
CLI_SESSION_TIMEOUT=3600
EDGE_NODES=http://edge1.example.com
```

## Common Commands

### Development

```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild images
docker-compose build

# Restart specific service
docker-compose restart control-plane
```

### Production

```bash
# Deploy
./deploy.sh production

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down

# Update and redeploy
git pull
./deploy.sh production
```

### Debugging

```bash
# Enter container shell
docker exec -it aegis-control-plane /bin/bash
docker exec -it aegis-nginx-edge /bin/sh

# Check container health
docker ps
docker inspect aegis-control-plane

# View Nginx config
docker exec aegis-nginx-edge cat /etc/nginx/nginx.conf

# Test Nginx config
docker exec aegis-nginx-edge nginx -t

# Reload Nginx
docker exec aegis-nginx-edge nginx -s reload
```

## Differences from Bare Metal

### Configuration Paths

- **Bare Metal**: `/etc/nginx/sites-available/`, `/etc/nginx/sites-enabled/`
- **Docker**: `/etc/nginx/conf.d/sites/`

### Nginx Reload

- **Bare Metal**: `systemctl reload nginx`
- **Docker**: `docker exec aegis-nginx-edge nginx -s reload`

The `nginx_manager.py` automatically detects the environment and uses the correct method.

## Health Checks

Both services have built-in health checks:

- **Control Plane**: `GET http://localhost:8000/health`
- **Nginx**: `GET http://localhost/health`

Docker will automatically restart unhealthy containers.

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 80
sudo lsof -i :80
# Kill it or change port in docker-compose.yml
```

### Permission Denied

```bash
# Ensure Docker daemon is running
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

### Nginx Config Not Applied

```bash
# Check shared volume
docker volume inspect aegis_nginx-configs

# Verify config file exists
docker exec aegis-control-plane ls -la /etc/nginx/conf.d/sites/

# Reload Nginx manually
docker exec aegis-nginx-edge nginx -s reload
```

### Container Won't Start

```bash
# Check logs
docker logs aegis-control-plane
docker logs aegis-nginx-edge

# Inspect container
docker inspect aegis-control-plane
```

## Scaling

To add more Edge Nodes:

1. Copy `nginx-edge` directory to new server
2. Update `EDGE_NODES` in Control Plane `.env`
3. Deploy on new server:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d nginx-edge
   ```

## Backup

```bash
# Backup volumes
docker run --rm -v aegis_nginx-configs:/data -v $(pwd):/backup \
  alpine tar czf /backup/nginx-configs-backup.tar.gz /data

# Restore volumes
docker run --rm -v aegis_nginx-configs:/data -v $(pwd):/backup \
  alpine tar xzf /backup/nginx-configs-backup.tar.gz -C /
```
