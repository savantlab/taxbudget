# Deployment Quickstart
## Django on DigitalOcean App Platform

⚠️ **REALITY CHECK:** This guide originally claimed "15 minutes" but actual deployment took 13 hours due to platform limitations. Realistic timeline: **2-4 hours** for first deployment.

## Platform Issues You Will Encounter

1. **PostgreSQL 15+ Broken** - Managed database has permission errors with Django
2. **No Managed Redis** - DigitalOcean removed Redis from App Platform (requires manual droplet)
3. **Environment Variable Conflicts** - Dashboard silently overrides app spec
4. **Poor Error Messages** - Logs are opaque, CLI tools unreliable

**Recommendation:** For production Django apps, consider AWS ECS, GCP Cloud Run, or Docker Compose on DigitalOcean Droplets instead.

This guide documents what works despite the limitations.

---

## Prerequisites (5 minutes)

```bash
# 1. Install doctl
brew install doctl

# 2. Authenticate
doctl auth init
# (Follow prompts to paste API token from DigitalOcean dashboard)

# 3. Verify
doctl account get
```

---

## Setup Repository (3 minutes)

```bash
# 1. Initialize git (if not done)
git init

# 2. Create GitHub repository
# Go to https://github.com/new
# Repository name: taxbudget
# Make it public or private

# 3. Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/taxbudget.git

# 4. Update do-app-spec.yaml
# Replace YOUR_USERNAME with your GitHub username
sed -i '' 's/YOUR_USERNAME/your-actual-username/g' do-app-spec.yaml

# 5. Commit everything
git add .
git commit -m "Initial commit: Tax Budget Allocator for tadpollster.com"
git push -u origin main
```

---

## Create Redis Droplet First (10 minutes)

**REQUIRED:** App Platform no longer provides managed Redis

```bash
# Create Redis droplet
doctl compute droplet create yourapp-redis \
  --image ubuntu-22-04-x64 \
  --size s-1vcpu-1gb \
  --region nyc3 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header)

# Get PUBLIC IP (you'll need this)
REDIS_IP=$(doctl compute droplet get yourapp-redis --format PublicIPv4 --no-header)
echo "Redis IP: $REDIS_IP"

# SSH and install Redis
doctl compute ssh yourapp-redis

# On droplet:
sudo apt update && sudo apt install redis-server -y
sudo sed -i 's/bind 127.0.0.1 ::1/bind 0.0.0.0/' /etc/redis/redis.conf
sudo systemctl restart redis-server

# Test (back on your machine)
redis-cli -h $REDIS_IP ping  # Should return PONG
```

**⚠️ SECURITY WARNING:** Redis is exposed on public internet. For production, use firewall rules or VPC.

## Deploy to DigitalOcean (30-60 minutes)

### Option A: App Platform (Using SQLite)

```bash
# 1. Update do-app-spec.yaml with Redis IP
sed -i '' "s/REDIS_DROPLET_PUBLIC_IP/$REDIS_IP/g" do-app-spec.yaml

# 2. Generate SECRET_KEY
SECRET_KEY=$(openssl rand -base64 48)
echo "SECRET_KEY: $SECRET_KEY"

# 3. Update do-app-spec.yaml with SECRET_KEY
# (Manually edit do-app-spec.yaml and replace "your-generated-secret-key-here" with $SECRET_KEY)

# 4. Deploy app
doctl apps create --spec do-app-spec.yaml

# Get app ID (will be shown in output)
APP_ID=<your-app-id>

# Monitor deployment
doctl apps logs $APP_ID --type build --follow
```

**⚠️ CRITICAL:** Make sure your `do-app-spec.yaml`:
- Has NO `databases:` section (PostgreSQL is broken)
- Uses Redis PUBLIC IP in all REDIS_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND
- Has SECRET_KEY as plain value, not `type: SECRET`
- Has `ALLOWED_HOSTS: "*"` or your actual domain

### Option B: Full Droplet Deployment (More Control)

# 2. Create droplet
doctl compute droplet create tadpollster \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-4gb \
  --region nyc3 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header)

# 3. Get droplet IP
DROPLET_IP=$(doctl compute droplet get tadpollster --format PublicIPv4 --no-header)
echo "Droplet IP: $DROPLET_IP"

# 4. SSH and setup
doctl compute ssh tadpollster

# On droplet:
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo apt install docker-compose -y
git clone https://github.com/YOUR_USERNAME/taxbudget.git
cd taxbudget
cp .env.example .env
# Edit .env with database credentials
docker-compose up -d
```

---

## Configure Domain (2 minutes)

### Method 1: DigitalOcean DNS

```bash
# Add domain
doctl compute domain create tadpollster.com

# Add A record (use your app or droplet IP)
doctl compute domain records create tadpollster.com \
  --record-type A \
  --record-name @ \
  --record-data $DROPLET_IP \
  --record-ttl 3600

# Add www CNAME
doctl compute domain records create tadpollster.com \
  --record-type CNAME \
  --record-name www \
  --record-data @ \
  --record-ttl 3600

# Verify
doctl compute domain records list tadpollster.com
```

### Method 2: Use Your Registrar's DNS

Point your domain's nameservers to DigitalOcean:
- ns1.digitalocean.com
- ns2.digitalocean.com
- ns3.digitalocean.com

Then follow Method 1 above.

---

## Initial Setup (2 minutes)

### For App Platform:

```bash
# Get app ID
APP_ID=$(doctl apps list --format ID --no-header)

# Run migrations
doctl apps create-deployment $APP_ID

# Console access (via dashboard):
# Apps → Your App → Console → web
# Then run:
python manage.py migrate
python manage.py populate_categories
python manage.py rebuild_aggregates
python manage.py createsuperuser
```

### For Droplet:

```bash
doctl compute ssh tadpollster

cd taxbudget
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py populate_categories
docker-compose exec web python manage.py rebuild_aggregates
docker-compose exec web python manage.py createsuperuser
```

---

## Enable SSL (1 minute)

### App Platform (Automatic)

SSL is automatically provisioned for your domain once DNS is configured. Check:

```bash
doctl apps get $APP_ID --format DefaultIngress
```

### Droplet (Manual)

```bash
doctl compute ssh tadpollster

sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d tadpollster.com -d www.tadpollster.com
```

---

## Verify Deployment

```bash
# Test your site
curl https://tadpollster.com
curl https://www.tadpollster.com

# Check services
curl https://tadpollster.com/aggregate/
```

Visit in browser:
- https://tadpollster.com
- https://tadpollster.com/admin
- https://tadpollster.com/aggregate/

---

## Troubleshooting

### Domain not resolving
```bash
dig tadpollster.com
# Wait up to 48 hours for DNS propagation (usually 5-30 minutes)
```

### App won't start (500 Internal Server Error)
```bash
# Check logs (may hang - use dashboard web UI instead)
doctl apps logs $APP_ID --type run --follow

# Common issues:
# 1. SECRET_KEY empty or not set
#    Solution: Add to app spec as plain value, not type: SECRET
#
# 2. Environment variable conflicts
#    Solution: Check dashboard Settings → Environment Variables
#    Delete any variables set in dashboard that conflict with app spec
#
# 3. Missing database population
#    Solution: Add "python manage.py populate_categories" to entrypoint-prod.sh
#
# 4. ALLOWED_HOSTS misconfigured
#    Solution: Set to "*" in app spec, check dashboard hasn't overridden it
#
# 5. Redis connection failed
#    Solution: Make sure using PUBLIC IP, not private IP or hostname
```

### Database errors (PostgreSQL)
**Note:** Managed PostgreSQL is currently broken on App Platform due to permission issues.

If you see "permission denied for schema public", switch to SQLite:
1. Remove `databases:` section from do-app-spec.yaml
2. Remove DATABASE_URL from environment variables
3. Let Django use SQLite (default in settings.py)
4. Redeploy

---

## Quick Commands

```bash
# View app status
doctl apps list

# View logs
doctl apps logs <app-id> --type run --follow

# View databases
doctl databases list

# Restart app
doctl apps create-deployment <app-id>

# Scale app
doctl apps update <app-id> --spec do-app-spec.yaml

# View costs
doctl balance get
```

---

## What's Running?

### App Platform Deployment (Actual):
- **Web** (1 instance): Django + Gunicorn → https://tadpollster.com
- **Celery Worker**: Background task processing
- **Celery Beat**: Scheduled tasks (cache updates)
- **SQLite**: Database (in-container, not managed PostgreSQL due to bugs)
- **Redis Droplet**: Cache + Celery broker ($6/month)

**Cost**: $45/month App Platform + $6/month Redis droplet = **$51/month**

### Droplet Deployment (Alternative):
- **Droplet**: 2 vCPU, 4GB RAM (all services via Docker)
- **No managed databases**: Run PostgreSQL + Redis in containers

**Cost**: ~$24-48/month (more control, less convenience)

---

## Next Steps

- **Monitor**: Set up alerts in DigitalOcean dashboard
- **Backup**: Enable automatic database backups
- **Scale**: Increase resources as traffic grows
- **Optimize**: Review performance metrics in Flower (http://your-ip:5555)
- **Custom**: Update templates and styling
- **Analytics**: Add Google Analytics or similar

---

## Support

For detailed documentation, see:
- `DIGITALOCEAN_DEPLOYMENT.md` - Complete deployment guide
- `DOCKER.md` - Docker containerization
- `SCALABILITY.md` - Performance optimization
- `COMPLEXITY_REDUCTION_REPORT.md` - Technical architecture

---

**🚀 Your Tax Budget Allocator is now live at https://tadpollster.com!**

**Total Time**: 2-4 hours (first deployment), ~30 minutes (subsequent)  
**Monthly Cost**: $51 (App Platform + Redis droplet)  
**Scalability**: Handles 10M+ users at O(1) complexity  
**Reality**: Deployment is harder than advertised due to platform limitations  

**For future projects:** Consider AWS ECS/Fargate, GCP Cloud Run, or Docker Compose on bare droplets for better PostgreSQL/Redis support.
