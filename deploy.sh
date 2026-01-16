#!/bin/bash
# Aegis.net Deployment Script

set -e

ENVIRONMENT=${1:-development}
COMPOSE_FILE="docker-compose.yml"

if [ "$ENVIRONMENT" = "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
fi

echo "🚀 Deploying Aegis.net ($ENVIRONMENT environment)..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env with your configuration before deploying to production!"
    if [ "$ENVIRONMENT" = "production" ]; then
        exit 1
    fi
fi

# Build images
echo "🔨 Building Docker images..."
docker-compose -f $COMPOSE_FILE build

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f $COMPOSE_FILE down

# Start services
echo "▶️  Starting services..."
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
echo "🏥 Checking service health..."
docker-compose -f $COMPOSE_FILE ps

echo "✅ Deployment complete!"
echo ""
echo "📊 Service URLs:"
echo "  - Control Plane: http://localhost:8000"
echo "  - Nginx Edge:    http://localhost:80"
echo ""
echo "📝 View logs:"
echo "  docker-compose -f $COMPOSE_FILE logs -f"
echo ""
echo "🛑 Stop services:"
echo "  docker-compose -f $COMPOSE_FILE down"
