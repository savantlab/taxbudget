# DigitalOcean Deployment Guide
## Tax Budget Allocator on tadpollster.com

⚠️ **CRITICAL: READ BEFORE DEPLOYING (Dec 2024 Update)**

This guide was written before discovering major platform limitations. **Actual deployment took 13 hours** due to:

1. **PostgreSQL 15+ Broken** - Managed PostgreSQL cannot be used with Django (permission errors)
2. **Redis Removed** - DigitalOcean removed managed Redis from App Platform in 2024
3. **Environment Conflicts** - Dashboard variables silently override app spec
4. **Poor Observability** - Error messages are opaque, logs frequently hang

**What Actually Works:**
- **Database**: SQLite (in-container), NOT managed PostgreSQL
- **Redis**: Manual droplet with PUBLIC IP, NOT managed Redis
- **Config**: App spec only, avoid dashboard environment variables

**Recommended Alternatives for Production:**
- AWS ECS/Fargate with RDS + ElastiCache
- GCP Cloud Run with Cloud SQL + Memorystore
- Docker Compose on DigitalOcean Droplets

**This guide documents the workarounds** that eventually succeeded.

**Domain**: tadpollster.com  
**Platform**: DigitalOcean App Platform (with significant limitations)  
**Tool**: doctl (DigitalOcean CLI)  
**Actual Cost**: $51/month (App Platform $45 + Redis droplet $6)

---

## Prerequisites

1. DigitalOcean account
2. `doctl` installed and authenticated
3. Domain: tadpollster.com (DNS configured)
4. Git repository

---

## Quick Start Deployment

### 1. Install and Configure doctl

```bash
# Install doctl (macOS)
brew install doctl

# Authenticate
doctl auth init

# Verify
doctl account get
```

### 2. Prepare Repository

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit: Tax Budget Allocator"

# Add GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/taxbudget.git
git push -u origin main
```

### 3. Create .env.production

```bash
# Create production environment file
cp .env.example .env.production
```

Edit `.env.production`:
```bash
DEBUG=False
SECRET_KEY=<generate-secure-key>
DB_PASSWORD=<strong-password>
ALLOWED_HOSTS=tadpollster.com,www.tadpollster.com
SECURE_SSL_REDIRECT=True
```

Generate secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Option 1: DigitalOcean App Platform (Recommended - Easiest)

### Create App via doctl

```bash
# Create app from spec file
doctl apps create --spec do-app-spec.yaml

# Or create from GitHub repo
doctl apps create-deployment <app-id>
```

### Configure Domain

```bash
# Add domain to app
doctl apps update <app-id> --spec do-app-spec.yaml

# Or via dashboard:
# Apps → Your App → Settings → Domains → Add Domain
# Domain: tadpollster.com
# Type: Primary
```

### DNS Configuration

Add these records to tadpollster.com:

```
Type: A
Hostname: @
Value: <app-platform-ip>
TTL: 3600

Type: CNAME
Hostname: www
Value: tadpollster.com
TTL: 3600
```

---

## Option 2: Droplet Deployment (Full Control)

### 1. Create Droplet

```bash
# Create Ubuntu 22.04 droplet
doctl compute droplet create tadpollster \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-4gb \
  --region nyc3 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header)

# Get droplet IP
doctl compute droplet get tadpollster --format PublicIPv4
```

### 2. Configure DNS

```bash
# Create A record
doctl compute domain records create tadpollster.com \
  --record-type A \
  --record-name @ \
  --record-data <droplet-ip> \
  --record-ttl 3600

# Create www CNAME
doctl compute domain records create tadpollster.com \
  --record-type CNAME \
  --record-name www \
  --record-data tadpollster.com \
  --record-ttl 3600
```

### 3. SSH and Setup

```bash
# SSH to droplet
doctl compute ssh tadpollster

# On droplet:
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose -y

# Clone repository
git clone https://github.com/YOUR_USERNAME/taxbudget.git
cd taxbudget

# Create .env file
cp .env.example .env
nano .env  # Edit with production values

# Start services
docker-compose up -d

# Setup SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d tadpollster.com -d www.tadpollster.com
```

---

## Option 3: Managed Databases + Container Registry

### 1. Create Managed Databases

```bash
# PostgreSQL
doctl databases create tadpollster-db \
  --engine pg \
  --region nyc3 \
  --size db-s-1vcpu-1gb \
  --num-nodes 1

# Get connection info
doctl databases connection tadpollster-db

# Redis
doctl databases create tadpollster-redis \
  --engine redis \
  --region nyc3 \
  --size db-s-1vcpu-1gb \
  --num-nodes 1

# Get Redis connection
doctl databases connection tadpollster-redis
```

### 2. Push to Container Registry

```bash
# Create registry
doctl registry create taxbudget-registry

# Login
doctl registry login

# Build and push
docker build -t registry.digitalocean.com/taxbudget-registry/taxbudget:latest .
docker push registry.digitalocean.com/taxbudget-registry/taxbudget:latest
```

### 3. Deploy from Registry

```bash
# Create droplet and pull image
doctl compute droplet create tadpollster \
  --image docker-20-04 \
  --size s-2vcpu-4gb \
  --region nyc3 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header)

# SSH and run
doctl compute ssh tadpollster

docker login registry.digitalocean.com
docker pull registry.digitalocean.com/taxbudget-registry/taxbudget:latest
docker-compose up -d
```

---

## App Platform Specification File

Create `do-app-spec.yaml`:

```yaml
name: tadpollster
region: nyc

domains:
  - domain: tadpollster.com
    type: PRIMARY
    wildcard: false
  - domain: www.tadpollster.com
    type: ALIAS
    wildcard: false

services:
  - name: web
    github:
      repo: YOUR_USERNAME/taxbudget
      branch: main
      deploy_on_push: true
    
    build_command: |
      pip install -r requirements.txt
      python manage.py collectstatic --noinput
    
    run_command: |
      python manage.py migrate
      gunicorn taxbudget.wsgi:application --bind 0.0.0.0:8000 --workers 4
    
    envs:
      - key: DEBUG
        value: "False"
      - key: SECRET_KEY
        value: ${SECRET_KEY}
        type: SECRET
      - key: DATABASE_URL
        value: ${db.DATABASE_URL}
      - key: REDIS_URL
        value: ${redis.DATABASE_URL}
      - key: ALLOWED_HOSTS
        value: "tadpollster.com,www.tadpollster.com"
    
    http_port: 8000
    
    instance_count: 2
    instance_size_slug: basic-xs
    
    health_check:
      http_path: /
      initial_delay_seconds: 60
      period_seconds: 30
      timeout_seconds: 5
      success_threshold: 1
      failure_threshold: 3

  - name: celery
    github:
      repo: YOUR_USERNAME/taxbudget
      branch: main
    
    build_command: pip install -r requirements.txt
    run_command: celery -A taxbudget worker --loglevel=info --concurrency=2
    
    envs:
      - key: DATABASE_URL
        value: ${db.DATABASE_URL}
      - key: REDIS_URL
        value: ${redis.DATABASE_URL}
    
    instance_count: 1
    instance_size_slug: basic-xs

databases:
  - name: db
    engine: PG
    version: "15"
    size: db-s-1vcpu-1gb
    num_nodes: 1
    production: true

  - name: redis
    engine: REDIS
    version: "7"
    size: db-s-1vcpu-1gb
    num_nodes: 1
    production: true

workers:
  - name: celery-beat
    github:
      repo: YOUR_USERNAME/taxbudget
      branch: main
    build_command: pip install -r requirements.txt
    run_command: celery -A taxbudget beat --loglevel=info
    instance_count: 1
    instance_size_slug: basic-xxs
```

---

## DNS Configuration Steps

### Via DigitalOcean Dashboard

1. Go to Networking → Domains
2. Add domain: `tadpollster.com`
3. Add A record:
   - Hostname: `@`
   - Will Direct to: Your droplet or app
   - TTL: 3600
4. Add CNAME record:
   - Hostname: `www`
   - Is an alias of: `tadpollster.com`
   - TTL: 3600

### Via doctl

```bash
# Create domain
doctl compute domain create tadpollster.com

# List your resources
doctl compute droplet list
doctl apps list

# Add A record (replace with your droplet IP)
doctl compute domain records create tadpollster.com \
  --record-type A \
  --record-name @ \
  --record-data 159.89.123.456 \
  --record-ttl 3600

# Add www CNAME
doctl compute domain records create tadpollster.com \
  --record-type CNAME \
  --record-name www \
  --record-data @ \
  --record-ttl 3600

# Verify records
doctl compute domain records list tadpollster.com
```

---

## SSL Certificate Setup

### Option 1: Let's Encrypt (Free)

```bash
# SSH to droplet
doctl compute ssh tadpollster

# Install Certbot
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot

# Get certificate
sudo certbot --nginx -d tadpollster.com -d www.tadpollster.com

# Auto-renewal is automatic via systemd timer
sudo systemctl status snap.certbot.renew.timer
```

### Option 2: DigitalOcean Managed Certificate

```bash
# Create certificate
doctl compute certificate create \
  --name tadpollster-cert \
  --dns-names tadpollster.com,www.tadpollster.com \
  --type lets_encrypt
```

---

## Post-Deployment Checklist

### 1. Initial Setup

```bash
# SSH to server
doctl compute ssh tadpollster

# Navigate to app directory
cd taxbudget

# Run migrations
docker-compose exec web python manage.py migrate

# Populate categories
docker-compose exec web python manage.py populate_categories

# Build aggregates
docker-compose exec web python manage.py rebuild_aggregates

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

### 2. Verify Services

```bash
# Check all containers are running
docker-compose ps

# Check logs
docker-compose logs -f web
docker-compose logs -f celery

# Test the site
curl https://tadpollster.com
curl https://tadpollster.com/aggregate/
```

### 3. Configure Firewall

```bash
# Create firewall
doctl compute firewall create \
  --name tadpollster-fw \
  --inbound-rules "protocol:tcp,ports:22,sources:addresses:0.0.0.0/0,sources:addresses:::/0 protocol:tcp,ports:80,sources:addresses:0.0.0.0/0,sources:addresses:::/0 protocol:tcp,ports:443,sources:addresses:0.0.0.0/0,sources:addresses:::/0" \
  --outbound-rules "protocol:tcp,ports:all,destinations:addresses:0.0.0.0/0,destinations:addresses:::/0 protocol:udp,ports:all,destinations:addresses:0.0.0.0/0,destinations:addresses:::/0"

# Apply to droplet
doctl compute firewall add-droplets <firewall-id> --droplet-ids <droplet-id>
```

---

## Monitoring and Maintenance

### View Logs

```bash
# App Platform
doctl apps logs <app-id> --type run

# Droplet
doctl compute ssh tadpollster
docker-compose logs -f
```

### Update Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose up -d --build

# Run migrations
docker-compose exec web python manage.py migrate
```

### Backup Database

```bash
# Manual backup
docker-compose exec db pg_dump -U postgres taxbudget > backup.sql

# Or via DigitalOcean
doctl databases backups list <database-id>
```

### Scale Resources

```bash
# Scale droplet
doctl compute droplet-action resize <droplet-id> --size s-4vcpu-8gb

# Scale database
doctl databases resize <database-id> --size db-s-2vcpu-4gb

# Scale workers
docker-compose up -d --scale celery=4
```

---

## Cost Estimate (DigitalOcean)

### App Platform Deployment

| Resource | Specs | Cost |
|----------|-------|------|
| Web (2 instances) | Basic XS | $10/mo |
| Celery Worker | Basic XS | $5/mo |
| PostgreSQL | 1GB RAM, 10GB | $15/mo |
| Redis | 1GB RAM | $15/mo |
| Bandwidth | 1TB included | $0 |
| **Total** | | **$45/mo** |

### Droplet Deployment

| Resource | Specs | Cost |
|----------|-------|------|
| Droplet | 2 vCPU, 4GB RAM | $24/mo |
| Managed PostgreSQL | 1GB RAM, 10GB | $15/mo |
| Managed Redis | 1GB RAM | $15/mo |
| Load Balancer | Optional | $12/mo |
| **Total** | | **$54-66/mo** |

---

## Troubleshooting

### Domain not resolving

```bash
# Check DNS propagation
dig tadpollster.com
nslookup tadpollster.com

# Verify DigitalOcean DNS
doctl compute domain records list tadpollster.com
```

### SSL certificate issues

```bash
# Renew certificate
sudo certbot renew --dry-run

# Check certificate status
sudo certbot certificates
```

### Application errors

```bash
# Check logs
docker-compose logs web --tail=100

# Restart services
docker-compose restart web

# Check Django settings
docker-compose exec web python manage.py check --deploy
```

### Database connection issues

```bash
# Verify DATABASE_URL
docker-compose exec web env | grep DATABASE

# Test connection
docker-compose exec web python manage.py dbshell
```

---

## Security Checklist

- [x] SSL certificate installed
- [x] Firewall configured (ports 80, 443, 22 only)
- [x] DEBUG=False in production
- [x] SECRET_KEY is secure and unique
- [x] ALLOWED_HOSTS properly configured
- [x] Database uses strong password
- [x] Regular backups enabled
- [x] Security updates automated

---

## Quick Commands Reference

```bash
# Deploy
doctl apps create --spec do-app-spec.yaml

# DNS
doctl compute domain records create tadpollster.com --record-type A --record-name @ --record-data <ip>

# SSH
doctl compute ssh tadpollster

# Logs
doctl apps logs <app-id>

# Scale
doctl compute droplet-action resize <droplet-id> --size s-4vcpu-8gb

# Backup
doctl databases backups list <database-id>

# Certificate
sudo certbot --nginx -d tadpollster.com -d www.tadpollster.com
```

---

**Next Steps**:
1. Set up GitHub repository
2. Configure domain DNS at tadpollster.com registrar
3. Create DigitalOcean resources
4. Deploy application
5. Configure SSL
6. Test and go live!

Your Tax Budget Allocator will be live at **https://tadpollster.com** 🚀
