#!/bin/bash
set -euo pipefail

echo "=== Setting up AI Survival Dashboard ==="

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

# Build and start dashboard
sudo docker compose build dashboard
sudo docker compose up -d dashboard

# Create systemd service for dashboard
sudo tee /etc/systemd/system/ai-survival-dashboard.service > /dev/null << 'EOF'
[Unit]
Description=AI Survival Dashboard
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/home/opc/ai_survival
ExecStartPre=-/usr/bin/docker compose down
ExecStartPre=-/usr/bin/docker compose build dashboard
ExecStart=/usr/bin/docker compose up dashboard
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ai-survival-dashboard

echo "=== Dashboard setup complete ==="
echo "Service enabled. Will start on reboot."
echo "To start now: sudo systemctl start ai-survival-dashboard"
