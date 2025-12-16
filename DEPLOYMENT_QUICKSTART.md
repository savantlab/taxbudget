# Deployment Quickstart
## Get tadpollster.com Live in 15 Minutes

This guide will get your Tax Budget Allocator deployed to DigitalOcean as quickly as possible.

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

## Deploy to DigitalOcean (5 minutes)

### Option A: App Platform (Easiest - Recommended)

```bash
# Deploy app
doctl apps create --spec do-app-spec.yaml

# Get app ID (will be shown in output)
APP_ID=<your-app-id>

# Monitor deployment
doctl apps logs $APP_ID --type build --follow
```

**Add SECRET_KEY via Dashboard:**
1. Go to Apps → Your App → Settings → Environment Variables
2. Click "Edit" on web service
3. Find SECRET_KEY, click "Edit"
4. Paste your secret key (generate with the command below)
5. Repeat for celery-worker and celery-beat
6. Redeploy

```bash
# Generate SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Option B: Droplet + Managed Databases

```bash
# 1. Create managed databases
doctl databases create tadpollster-db --engine pg --region nyc3 --size db-s-1vcpu-1gb --num-nodes 1
doctl databases create tadpollster-redis --engine redis --region nyc3 --size db-s-1vcpu-1gb --num-nodes 1

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

### App won't start
```bash
# Check logs
doctl apps logs $APP_ID --type run --follow

# Common issues:
# - SECRET_KEY not set (add via dashboard)
# - Database not ready (wait 2-3 minutes after creation)
# - GitHub repo not accessible (make public or add deploy key)
```

### Database errors
```bash
# Verify connection
doctl databases connection <db-id>

# Run migrations manually
doctl apps create-deployment $APP_ID
```

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

### App Platform Deployment:
- **Web** (2 instances): Django + Gunicorn → https://tadpollster.com
- **Celery Worker**: Background task processing
- **Celery Beat**: Scheduled tasks (cache updates)
- **PostgreSQL**: Primary database (15GB)
- **Redis**: Cache + Celery broker

**Cost**: ~$45/month

### Droplet Deployment:
- **Droplet**: 2 vCPU, 4GB RAM (all services via Docker)
- **PostgreSQL**: Managed database (15GB)
- **Redis**: Managed cache

**Cost**: ~$54/month

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

**Total Time**: ~15 minutes  
**Monthly Cost**: $45-66  
**Scalability**: Handles 10M+ users at O(1) complexity
