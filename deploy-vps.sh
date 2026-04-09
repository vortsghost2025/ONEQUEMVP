#!/bin/bash
# OneQueue VPS Deployment Script
# Run this on the VPS to set up OneQueue with Docker

set -e

echo "=== OneQueue VPS Deployment ==="
echo ""

# 1. Update system
echo "Updating system packages..."
apt-get update && apt-get upgrade -y

# 2. Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# 3. Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    apt-get install -y docker-compose-plugin
fi

# 4. Create OneQueue directory
echo "Creating OneQueue directory..."
mkdir -p /opt/onequeue
cd /opt/onequeue

# 5. Clone repository (or upload files)
if [ ! -d "app" ]; then
    echo "Cloning OneQueue..."
    # Option 1: Git clone (if public repo)
    # git clone https://github.com/yourorg/onequeue.git .
    
    # Option 2: Create from scratch
    mkdir -p app/api app/services
fi

# 6. Create .env file
echo "Creating .env file..."
cat > .env <<EOF
NVIDIA_API_KEY=${NVIDIA_API_KEY}
OLLAMA_BASE_URL=http://ollama:11434
POLLING_INTERVAL_SECONDS=1
DATABASE_URL=sqlite:////app/onequeue.db
EOF

# 7. Set permissions
echo "Setting permissions..."
chmod -R 755 /opt/onequeue

# 8. Pull Docker images
echo "Pulling Docker images..."
docker compose pull

# 9. Start services
echo "Starting OneQueue services..."
docker compose up -d

# 10. Wait for services to start
echo "Waiting for services to start..."
sleep 10

# 11. Check health
echo "Checking service health..."
curl -f http://localhost:8081/health || echo "Health check failed"

echo ""
echo "=== Deployment Complete ==="
echo "OneQueue is running at: http://$(curl -s ifconfig.me):8081"
echo ""
echo "Logs: docker compose logs -f"
echo "Stop: docker compose down"
echo "Restart: docker compose restart"
