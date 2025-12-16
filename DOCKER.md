# Docker Deployment Guide

## Overview

The Tax Budget Allocator is fully containerized with Docker for easy deployment and scalability.

### Services

- **web** - Django application (Gunicorn WSGI server)
- **db** - PostgreSQL 15 database
- **redis** - Redis cache & message broker
- **celery** - Background task workers
- **celery-beat** - Periodic task scheduler
- **flower** - Celery monitoring dashboard
- **nginx** - Reverse proxy & static file server

## Quick Start

### 1. Prerequisites

- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Docker Compose v2.0+

```bash
# Verify installation
docker --version
docker-compose --version
```

### 2. Configuration

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# Minimum required
SECRET_KEY=your-super-secret-key-here
DB_PASSWORD=your-database-password
```

### 3. Build and Start

```bash
# Build images and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 4. Initial Setup

```bash
# Run migrations and create superuser (already done by entrypoint)
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# Populate budget categories
docker-compose exec web python manage.py populate_categories

# Build aggregates
docker-compose exec web python manage.py rebuild_aggregates
```

### 5. Access Application

- **Main App**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **Flower Dashboard**: http://localhost:5555
- **Nginx Proxy**: http://localhost:80

## Docker Compose Profiles

### Development (all services)

```bash
docker-compose up -d
```

### Production (without flower/nginx)

```bash
docker-compose up -d web db redis celery celery-beat
```

### Minimal (without celery)

```bash
docker-compose up -d web db redis
```

## Common Commands

### Container Management

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a service
docker-compose restart web

# View logs
docker-compose logs -f web
docker-compose logs -f celery

# Shell access
docker-compose exec web bash
docker-compose exec db psql -U postgres taxbudget
```

### Django Management

```bash
# Run any Django command
docker-compose exec web python manage.py <command>

# Examples:
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py rebuild_aggregates
```

### Database Operations

```bash
# PostgreSQL shell
docker-compose exec db psql -U postgres taxbudget

# Backup database
docker-compose exec db pg_dump -U postgres taxbudget > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres taxbudget < backup.sql

# View database logs
docker-compose logs db
```

### Redis Operations

```bash
# Redis CLI
docker-compose exec redis redis-cli

# View cached data
docker-compose exec redis redis-cli KEYS "aggregate*"
docker-compose exec redis redis-cli GET aggregate_allocations_v2

# Clear cache
docker-compose exec redis redis-cli FLUSHALL
```

### Celery Operations

```bash
# View active tasks
docker-compose exec celery celery -A taxbudget inspect active

# View registered tasks
docker-compose exec celery celery -A taxbudget inspect registered

# Restart celery worker
docker-compose restart celery

# Scale workers
docker-compose up -d --scale celery=4
```

## Volume Management

### Volumes Created

- `postgres_data` - PostgreSQL database files
- `redis_data` - Redis persistence
- `static_volume` - Collected static files

### Backup Volumes

```bash
# Backup postgres data
docker run --rm -v taxbudget_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data

# Restore postgres data
docker run --rm -v taxbudget_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /
```

### Clean Up

```bash
# Remove containers and networks
docker-compose down

# Remove containers, networks, and volumes
docker-compose down -v

# Remove all (including images)
docker-compose down -v --rmi all
```

## Production Deployment

### Environment Variables

Set these in `.env` for production:

```bash
DEBUG=False
SECRET_KEY=<generate-secure-key>
DB_PASSWORD=<strong-password>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECURE_SSL_REDIRECT=True
```

### Generate Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### SSL/TLS with Let's Encrypt

Update `docker-compose.yml` to add Certbot:

```yaml
certbot:
  image: certbot/certbot
  volumes:
    - ./certbot/conf:/etc/letsencrypt
    - ./certbot/www:/var/www/certbot
  command: certonly --webroot --webroot-path=/var/www/certbot --email your@email.com --agree-tos --no-eff-email -d yourdomain.com
```

### Scaling

```bash
# Scale celery workers
docker-compose up -d --scale celery=4

# Scale web servers (behind nginx)
docker-compose up -d --scale web=3
```

### Health Checks

All services have health checks configured:

```bash
# Check service health
docker-compose ps

# View health check logs
docker inspect taxbudget_web | jq '.[0].State.Health'
```

## Troubleshooting

### Container won't start

```bash
# View logs
docker-compose logs web

# Check if ports are available
lsof -i :8000
lsof -i :5432
lsof -i :6379

# Rebuild image
docker-compose build --no-cache web
docker-compose up -d
```

### Database connection errors

```bash
# Check if postgres is healthy
docker-compose ps db

# Wait for postgres to be ready
docker-compose exec web python -c "import time; time.sleep(5)"

# Manually run migrations
docker-compose exec web python manage.py migrate
```

### Permission errors

```bash
# Fix volume permissions
docker-compose exec web chown -R 1000:1000 /app/staticfiles
```

### Redis connection errors

```bash
# Check redis status
docker-compose exec redis redis-cli ping

# Restart redis
docker-compose restart redis
```

### Celery tasks not processing

```bash
# Check worker status
docker-compose logs celery

# Restart workers
docker-compose restart celery

# View active tasks
docker-compose exec celery celery -A taxbudget inspect active
```

## Development Workflow

### Local Development with Docker

```bash
# Start services
docker-compose up -d

# Watch logs
docker-compose logs -f web celery

# Make changes to code (mounted as volume)
# Changes auto-reload in web container

# Run tests
docker-compose exec web python manage.py test

# Stop services
docker-compose down
```

### Hot Reload

Code changes are automatically detected because the app directory is mounted as a volume:

```yaml
volumes:
  - .:/app  # Live code mounting
```

## Monitoring

### View Resource Usage

```bash
# Container stats
docker stats

# Specific service
docker stats taxbudget_web taxbudget_celery
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service with tail
docker-compose logs -f --tail=100 web

# Since specific time
docker-compose logs --since 30m web
```

### Flower Dashboard

Access Celery monitoring at http://localhost:5555

Shows:
- Active/completed tasks
- Worker status
- Task success/failure rates
- Task execution times

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Docker Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build images
        run: docker-compose build
      
      - name: Run tests
        run: |
          docker-compose up -d db redis
          docker-compose run web python manage.py test
      
      - name: Deploy to production
        if: github.ref == 'refs/heads/main'
        run: |
          # Your deployment script here
          echo "Deploying to production..."
```

## Performance Tuning

### Gunicorn Workers

Adjust workers based on CPU cores:

```bash
# Formula: (2 × CPU cores) + 1
# 4 cores = 9 workers
docker-compose exec web gunicorn taxbudget.wsgi:application --bind 0.0.0.0:8000 --workers 9
```

Update `docker-compose.yml`:

```yaml
command: gunicorn taxbudget.wsgi:application --bind 0.0.0.0:8000 --workers 9 --timeout 120
```

### Celery Concurrency

```yaml
command: celery -A taxbudget worker --loglevel=info --concurrency=8
```

### PostgreSQL Connection Pool

In `production_settings.py`:

```python
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 600,  # 10 minutes
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

## Security Best Practices

1. **Never commit `.env` file**
2. **Use strong passwords** for DB_PASSWORD
3. **Generate new SECRET_KEY** for production
4. **Enable HTTPS** with SSL certificates
5. **Set DEBUG=False** in production
6. **Regular security updates**: `docker-compose pull`
7. **Limit exposed ports** in production
8. **Use Docker secrets** for sensitive data

## Architecture Diagram

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│    Nginx    │────▶│   Django    │
│   :80/443   │     │   Web :8000 │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────┼──────┐
                    │      │      │
                    ▼      ▼      ▼
              ┌──────┐ ┌─────┐ ┌────────┐
              │ PG   │ │Redis│ │ Celery │
              │ :5432│ │:6379│ │Workers │
              └──────┘ └─────┘ └────────┘
```

## Summary

✅ **Multi-container architecture** for scalability  
✅ **Production-ready** with Gunicorn, PostgreSQL, Redis  
✅ **Background tasks** with Celery workers  
✅ **Monitoring** with Flower dashboard  
✅ **Reverse proxy** with Nginx  
✅ **Health checks** for all services  
✅ **Easy deployment** with docker-compose  
✅ **Volume persistence** for data  

Your app is now containerized and ready to deploy anywhere Docker runs!
