#!/bin/bash
set -euo pipefail

echo "=== Setting up Redis on Oracle Cloud ==="

# Install Docker
sudo yum install -y docker-engine docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker

# Create Redis directory
mkdir -p /home/opc/redis
cd /home/opc/redis

# Create docker-compose for Redis only
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    restart: always
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    deploy:
      resources:
        limits:
          memory: 512M

volumes:
  redis_data:
EOF

# Create systemd service
sudo tee /etc/systemd/system/redis.service > /dev/null << 'EOF'
[Unit]
Description=Redis
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/home/opc/redis
ExecStartPre=-/usr/bin/docker compose down
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable redis
sudo systemctl start redis

echo "=== Redis setup complete ==="
echo "Redis running on port 6379"
echo "Connect from backend: redis://${HOSTNAME}:6379/0"
