#!/bin/bash
set -euo pipefail

echo "=== Setting up AI Survival Backend ==="

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
  
  # Update database URL for Oracle Cloud
  sed -i 's|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://ai_survival:ai_survival_pass@redis:6379/0|' .env
  
  cat >> .env << 'EOF'

# Oracle Cloud Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# Start Celery worker in background
EOF
fi

# Create systemd service for backend
sudo tee /etc/systemd/system/ai-survival-backend.service > /dev/null << 'EOF'
[Unit]
Description=AI Survival Backend
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/home/opc/ai_survival
ExecStartPre=-/usr/bin/docker compose down
ExecStartPre=-/usr/bin/docker compose build backend
ExecStart=/usr/bin/docker compose up backend
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10
Environment=APP_ENV=production
Environment=LOG_LEVEL=INFO

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for celery worker
sudo tee /etc/systemd/system/ai-survival-worker.service > /dev/null << 'EOF'
[Unit]
Description=AI Survival Celery Worker
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/home/opc/ai_survival
ExecStartPre=-/usr/bin/docker compose down
ExecStartPre=-/usr/bin/docker compose build backend
ExecStart=/usr/bin/docker compose run --rm backend celery -A backend.execution.engine worker --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ai-survival-backend
sudo systemctl enable ai-survival-worker

echo "=== Backend setup complete ==="
echo "Services enabled. They will start on reboot."
echo "To start now: sudo systemctl start ai-survival-backend"
