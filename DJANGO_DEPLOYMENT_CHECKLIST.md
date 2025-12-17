# Django Deployment Checklist for DigitalOcean App Platform

⚠️ **WARNING: Based on Real Deployment Experience (Dec 2024)**  
This checklist documents lessons learned from a 13-hour deployment that encountered multiple platform limitations.

## Platform Limitations to Know

1. **PostgreSQL 15+ Broken** - Managed PostgreSQL has permission issues with Django migrations
2. **Redis Not Managed** - DigitalOcean removed managed Redis from App Platform in 2024
3. **Environment Variables** - Dashboard overrides spec file silently, causing conflicts
4. **Poor Observability** - Error messages are opaque, logs often hang

**Recommendation:** For production Django apps, consider AWS ECS, GCP Cloud Run, or Docker Compose on DigitalOcean Droplets instead of App Platform.

This checklist documents what works despite platform limitations.

## Pre-Deployment Checklist

### 1. Environment Variables in settings.py
**Status: ✅ REQUIRED**

Ensure `settings.py` reads from environment variables:

```python
import os
import dj_database_url

# Essential settings that MUST be configurable
SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-key')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Database - use DATABASE_URL
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Celery (if using)
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
```

**⚠️ COMMON MISTAKE:** Hardcoded `ALLOWED_HOSTS = []` will cause 400 errors!

### 2. Production Dockerfile
**Status: ✅ REQUIRED**

Create `Dockerfile.prod` (separate from Docker Compose Dockerfile):

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn psycopg2-binary

COPY . .
RUN mkdir -p /app/staticfiles

# Production entrypoint (NO host checks)
COPY entrypoint-prod.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "yourproject.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
```

**⚠️ CRITICAL:** Do NOT use Docker Compose entrypoint that waits for `db` and `redis` hostnames!

### 3. Production Entrypoint Script
**Status: ✅ REQUIRED**

Create `entrypoint-prod.sh`:

```bash
#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Populating budget categories..."
python manage.py populate_categories

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating superuser if needed..."
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin')" || true

echo "Starting application..."
exec "$@"
```

**⚠️ NO HOST CHECKS:** Don't use `nc -z db 5432` or `nc -z redis 6379` - App Platform uses environment variables, not hostnames.

### 4. App Spec Configuration
**Status: ✅ REQUIRED**

Create or update `do-app-spec.yaml`:

```yaml
name: yourapp
region: nyc

# NO databases section - using SQLite due to PostgreSQL 15+ permission issues
# See Platform Limitations section above

services:
  - name: web
    github:
      repo: username/repo
      branch: main
      deploy_on_push: true
    
    dockerfile_path: Dockerfile.prod  # Use production Dockerfile!
    
    envs:
      - key: DEBUG
        value: "False"
      - key: SECRET_KEY
        value: "your-generated-secret-key-here"  # Generate with openssl rand -base64 48
      - key: ALLOWED_HOSTS
        value: "*"  # Or specific domains: "app.com,www.app.com"
      - key: REDIS_URL
        value: "redis://REDIS_DROPLET_PUBLIC_IP:6379/0"  # Must use PUBLIC IP
      - key: CELERY_BROKER_URL
        value: "redis://REDIS_DROPLET_PUBLIC_IP:6379/0"
      - key: CELERY_RESULT_BACKEND
        value: "redis://REDIS_DROPLET_PUBLIC_IP:6379/0"
    
    http_port: 8000
    instance_count: 1
    instance_size_slug: basic-xs
    
    health_check:
      http_path: /
      initial_delay_seconds: 60
      period_seconds: 30
      timeout_seconds: 5
      success_threshold: 1
      failure_threshold: 3

workers:
  - name: celery-worker
    github:
      repo: username/repo
      branch: main
    
    dockerfile_path: Dockerfile.prod
    
    run_command: celery -A yourproject worker --loglevel=info --concurrency=2
    
    envs:
      - key: REDIS_URL
        value: "redis://REDIS_DROPLET_PUBLIC_IP:6379/0"
      - key: CELERY_BROKER_URL
        value: "redis://REDIS_DROPLET_PUBLIC_IP:6379/0"
      - key: CELERY_RESULT_BACKEND
        value: "redis://REDIS_DROPLET_PUBLIC_IP:6379/0"
      - key: SECRET_KEY
        value: "your-generated-secret-key-here"
    
    instance_count: 1
    instance_size_slug: basic-xs

  - name: celery-beat
    github:
      repo: username/repo
      branch: main
    
    dockerfile_path: Dockerfile.prod
    
    run_command: celery -A yourproject beat --loglevel=info
    
    envs:
      - key: REDIS_URL
        value: "redis://REDIS_DROPLET_PUBLIC_IP:6379/0"
      - key: CELERY_BROKER_URL
        value: "redis://REDIS_DROPLET_PUBLIC_IP:6379/0"
      - key: CELERY_RESULT_BACKEND
        value: "redis://REDIS_DROPLET_PUBLIC_IP:6379/0"
      - key: SECRET_KEY
        value: "your-generated-secret-key-here"
    
    instance_count: 1
    instance_size_slug: basic-xxs
```

### 5. Dependencies
**Status: ✅ REQUIRED**

Ensure `requirements.txt` includes:

```
Django>=6.0,<7.0
gunicorn
celery>=5.3.0  # If using
redis>=5.0.0   # If using

# Only if using PostgreSQL (currently broken on App Platform):
# dj-database-url>=2.1.0
# psycopg2-binary>=2.9.0
```

**Note:** `dj-database-url` and `psycopg2-binary` are only needed if using PostgreSQL. For SQLite deployment (recommended due to PostgreSQL issues), they're not required.

## Deployment Steps

### Step 1: Create External Resources (if needed)
**👤 USER ACTION REQUIRED**

If using external Redis droplet:

```bash
# Create Redis droplet
doctl compute droplet create taxbudget-redis \
  --image ubuntu-22-04-x64 \
  --size s-1vcpu-1gb \
  --region nyc3

# Note the PUBLIC IP address
doctl compute droplet list | grep redis
```

**📝 AGENT:** Update `do-app-spec.yaml` with the Redis public IP.

### Step 2: Initial Deployment
**👤 USER ACTION REQUIRED**

```bash
# Create the app
doctl apps create --spec do-app-spec.yaml

# Get app ID
doctl apps list
```

**📝 AGENT:** Save the app ID for future operations.

### Step 3: Set SECRET_KEY
**👤 USER ACTION REQUIRED**

```bash
# Generate a secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Set it in App Platform (replace APP_ID and SECRET)
doctl apps update APP_ID --spec do-app-spec.yaml
# Then go to App Platform dashboard → Settings → Environment Variables
# Add SECRET_KEY as a secret (encrypted) variable
```

**📝 AGENT:** Cannot set secrets via CLI - user must use dashboard.

### Step 4: Monitor Deployment
**📝 AGENT ACTION**

```bash
# Check deployment status
doctl apps get-deployment APP_ID DEPLOYMENT_ID

# Watch for these phases:
# - PENDING_BUILD → BUILDING → DEPLOYING → ACTIVE ✅
# - If ERROR ❌, check logs immediately

# Check logs
doctl apps logs APP_ID --type deploy
doctl apps logs APP_ID --type build
```

**Common error patterns to watch for:**
- `400 Bad Request` → ALLOWED_HOSTS issue
- `Connection refused` → Port or gunicorn config issue
- `getaddrinfo for host 'db'` → Using wrong Dockerfile/entrypoint
- `No module named 'dj_database_url'` → Missing dependency

### Step 5: Verify Deployment
**📝 AGENT ACTION**

```bash
# Get app URL
doctl apps get APP_ID -o json | python3 -c "import sys, json; data = json.load(sys.stdin); print(data[0].get('live_url', 'No URL'))"

# Test the URL
curl -I https://APP_URL.ondigitalocean.app
```

**✅ Success indicators:**
- HTTP 200 response
- Phase: ACTIVE
- No errors in logs
- Celery workers connected (if applicable)

## Common Issues and Solutions

### Issue 1: 400 Bad Request on Health Checks
**Cause:** `ALLOWED_HOSTS` not properly configured  
**Solution:** Ensure `settings.py` reads from environment and app spec sets `ALLOWED_HOSTS: "*"`

### Issue 2: "getaddrinfo for host 'db' port 5432"
**Cause:** Using Docker Compose entrypoint that waits for hostnames  
**Solution:** Use `Dockerfile.prod` with `entrypoint-prod.sh` (no host checks)

### Issue 3: "ModuleNotFoundError: No module named '${redis'"
**Cause:** App spec using `${redis.DATABASE_URL}` without defining managed Redis  
**Solution:** Either:
- Add managed Redis to app spec databases section, OR
- Use external Redis droplet with public IP directly

### Issue 4: Redis Connection Timeout
**Cause:** App Platform can't reach Redis droplet private IP (different VPC)  
**Solution:** Use Redis droplet's PUBLIC IP address, not private IP

### Issue 5: Build Uses Cached Old Image
**Cause:** Docker layer caching  
**Solution:** 
```bash
doctl apps create-deployment APP_ID --force-rebuild
```

### Issue 6: Environment Variable Conflicts (CRITICAL)
**Cause:** Dashboard environment variables override app spec configuration  
**Symptoms:**
- App spec changes don't take effect
- "UnknownSchemeError: Scheme '://' is unknown" (empty DATABASE_URL in dashboard)
- 400 Bad Request (wrong ALLOWED_HOSTS in dashboard)

**Solution:**
1. Go to DigitalOcean Dashboard → Apps → Your App → Settings
2. Check Environment Variables section
3. Delete ANY variables that conflict with your app spec
4. Use app spec as single source of truth
5. Force redeploy after cleaning up dashboard variables

**Prevention:** Never set environment variables in both dashboard AND app spec

### Issue 7: Missing Database Population
**Cause:** Custom management commands not run automatically  
**Solution:** Add to `entrypoint-prod.sh`:
```bash
echo "Populating budget categories..."
python manage.py populate_categories
```

### Issue 8: SECRET_KEY Empty or Not Set
**Cause:** SECRET_KEY type: SECRET requires manual dashboard configuration  
**Solution:** Use plain value in app spec instead:
```yaml
- key: SECRET_KEY
  value: "generated-secret-key-here"
```
Generate with: `openssl rand -base64 48`

## Post-Deployment

### DNS Configuration
**👤 USER ACTION REQUIRED** (if using custom domain)

1. Deploy app first to get URL
2. Go to domain registrar (Squarespace, etc.)
3. Add CNAME records:
   - `@` → `app-name.ondigitalocean.app`
   - `www` → `app-name.ondigitalocean.app`
4. Wait for DNS propagation (5-30 minutes)
5. SSL certificates are automatic

### Update ALLOWED_HOSTS
**📝 AGENT ACTION** (once domain is configured)

Update `do-app-spec.yaml`:
```yaml
- key: ALLOWED_HOSTS
  value: "yourdomain.com,www.yourdomain.com,.ondigitalocean.app"
```

## Deployment Monitoring Script

Use `check_deploy.sh`:

```bash
./check_deploy.sh
```

This shows:
- Current deployment status
- Phase (BUILDING/DEPLOYING/ACTIVE/ERROR)
- Progress (X/13)
- Live URL (if active)
- Recent errors (if any)

## Quick Reference

### Key Files Needed
- ✅ `Dockerfile.prod` - Production container
- ✅ `entrypoint-prod.sh` - Production startup script
- ✅ `do-app-spec.yaml` - App Platform configuration
- ✅ `settings.py` - Must read environment variables
- ✅ `requirements.txt` - Must include `dj-database-url`

### Essential Commands
```bash
# Check status
doctl apps get APP_ID

# List deployments
doctl apps list-deployments APP_ID

# Check deployment
doctl apps get-deployment APP_ID DEPLOYMENT_ID

# View logs
doctl apps logs APP_ID --type deploy
doctl apps logs APP_ID --type build

# Force rebuild
doctl apps create-deployment APP_ID --force-rebuild

# Update app spec
doctl apps update APP_ID --spec do-app-spec.yaml
```

## Checklist Summary

Before deploying, verify:

- [ ] `settings.py` reads `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` from environment
- [ ] `settings.py` handles missing DATABASE_URL gracefully (defaults to SQLite)
- [ ] `Dockerfile.prod` exists and doesn't wait for db/redis hostnames
- [ ] `entrypoint-prod.sh` exists with no host checks
- [ ] `entrypoint-prod.sh` includes `python manage.py populate_categories` (or equivalent data seeding)
- [ ] `do-app-spec.yaml` references `Dockerfile.prod` (not `Dockerfile`)
- [ ] `requirements.txt` includes gunicorn, celery, redis
- [ ] NO databases section in app spec (using SQLite due to PostgreSQL issues)
- [ ] Redis droplet created with PUBLIC IP documented
- [ ] All Redis URLs use PUBLIC IP address (not private IP, not hostname)
- [ ] `ALLOWED_HOSTS` set to `*` or specific domains
- [ ] SECRET_KEY generated and added to app spec as plain value (not type: SECRET)
- [ ] Dashboard environment variables checked and cleared (conflicts with app spec)
- [ ] Health checks disabled or properly configured

**Reality Check:** Expect 2-4 hours for first deployment, not 15 minutes. Platform has significant limitations.

Follow this checklist to avoid the pitfalls we encountered! 🚀
