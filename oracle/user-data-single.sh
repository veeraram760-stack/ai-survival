#!/bin/bash
set -euo pipefail

echo "=== Setting up AI Survival System (Single Instance) ==="

# Install Docker
echo "Installing Docker..."
sudo yum install -y docker-engine docker-compose-plugin

sudo systemctl start docker
sudo systemctl enable docker

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
  
  # Update database URL for local PostgreSQL
  sed -i 's|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://ai_survival:ai_survival_pass@postgres:5432/ai_survival|' .env
  
  cat >> .env << 'EOF'

# Oracle Cloud Configuration
REDIS_HOST=redis
REDIS_PORT=6379
EOF
fi

# Create systemd service
sudo tee /etc/systemd/system/ai-survival.service > /dev/null << 'EOF'
[Unit]
Description=AI Survival System
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/home/opc/ai_survival
ExecStartPre=-/usr/bin/docker compose down
ExecStartPre=-/usr/bin/docker compose build
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10
Environment=APP_ENV=production
Environment=LOG_LEVEL=INFO

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ai-survival

echo "=== Setup complete ==="
echo "Service enabled. It will start on reboot."
echo "To start now: sudo systemctl start ai-survival"
