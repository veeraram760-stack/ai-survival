#!/bin/bash
set -euo pipefail

echo "=== AI Survival System - Initial Setup ==="

# Install Docker
echo "Installing Docker..."
sudo yum install -y docker-engine docker-compose-plugin

sudo systemctl start docker
sudo systemctl enable docker

# Install git
echo "Installing git..."
sudo yum install -y git

# Clone repository
if [ ! -d "/home/opc/ai_survival" ]; then
  echo "Cloning repository..."
  sudo -u opc git clone https://github.com/YOUR_USERNAME/ai_survival.git /home/opc/ai_survival
fi

cd /home/opc/ai_survival

# Create environment file
if [ ! -f ".env" ]; then
  echo "Creating .env from example..."
  cp .env.example .env
  
  sed -i 's|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://ai_survival:ai_survival_pass@postgres:5432/ai_survival|' .env
  
  cat >> .env << 'EOF'

REDIS_HOST=redis
REDIS_PORT=6379
EOF
fi

echo "=== Setup complete ==="
echo "Please SSH into the instance and run: cd /home/opc/ai_survival && docker compose up -d"
