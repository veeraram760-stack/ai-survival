# AI Survival System - Oracle Cloud Deployment

This project is configured for deployment on Oracle Cloud Free Tier.

## Architecture

- **Backend**: FastAPI on VM.Standard.A1.Flex (4 OCPU, 24GB RAM)
- **Dashboard**: React/Vite on VM.Standard.A1.Flex (4 OCPU, 24GB RAM)
- **Redis**: VM.Standard.A1.Flex (4 OCPU, 24GB RAM)
- **Database**: PostgreSQL on backend VM (Docker volume)

## Prerequisites

1. Oracle Cloud Free Tier account
2. SSH key pair
3. Terraform installed
4. OCI CLI configured (optional)

## Quick Start

### Option 1: Terraform (Recommended)

```bash
cd oracle

# Configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your Oracle Cloud credentials

# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Deploy infrastructure
terraform apply

# Get outputs
terraform output
```

### Option 2: Manual Setup

```bash
# 1. Create VCN and subnets in Oracle Cloud Console
# 2. Create 3 ARM instances (VM.Standard.A1.Flex)
# 3. Run startup scripts on each instance:

# Backend
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/ai_survival/main/oracle/user-data-backend.sh | bash

# Dashboard
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/ai_survival/main/oracle/user-data-dashboard.sh | bash

# Redis
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/ai_survival/main/oracle/user-data-redis.sh | bash
```

## Access URLs

After deployment:
- Backend API: `http://<backend-ip>:8000`
- Dashboard: `http://<dashboard-ip>:3000`
- Redis: `redis://<redis-private-ip>:6379`

## Configuration

Set these secrets on your backend instance:

```bash
# SSH to backend
ssh -i ~/.ssh/id_rsa opc@<backend-public-ip>

# Set environment variables
sudo nano /home/opc/ai_survival/.env
```

Required environment variables:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `DISCORD_WEBHOOK_URL`
- `DATABASE_URL` (auto-configured)
- `REDIS_URL` (auto-configured)

## Management

```bash
# Check backend status
sudo systemctl status ai-survival-backend

# Check dashboard status
sudo systemctl status ai-survival-dashboard

# Check Redis status
sudo systemctl status redis

# View logs
sudo journalctl -u ai-survival-backend -f
sudo journalctl -u ai-survival-dashboard -f

# Restart services
sudo systemctl restart ai-survival-backend
sudo systemctl restart ai-survival-dashboard
```

## Cost

**$0/month** - All resources within Oracle Cloud Free Tier:
- 3x VM.Standard.A1.Flex (always free)
- 1GB block volume (always free)
- 10TB outbound/month (always free)

## Troubleshooting

### SSH Connection
```bash
# Make sure your SSH key is added to Oracle Cloud
# Default user is 'opc'
ssh -i ~/.ssh/id_rsa opc@<public-ip>
```

### Docker Issues
```bash
# Check Docker status
sudo systemctl status docker

# View Docker logs
sudo docker logs <container-id>
```

### Backend Not Starting
```bash
# Check logs
sudo journalctl -u ai-survival-backend -n 100

# Verify .env file
sudo cat /home/opc/ai_survival/.env

# Test Docker Compose
cd /home/opc/ai_survival
sudo docker compose up backend
```

## Security

1. Change default passwords in `.env`
2. Configure firewall rules (OCI Network Security Groups)
3. Use SSH keys for authentication
4. Enable OCI audit logging
5. Regularly update packages
