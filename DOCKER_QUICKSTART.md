# Docker Quick Start

Get the Tax Budget Allocator running in Docker in 3 minutes!

## Prerequisites

- Docker Desktop installed
- 2GB free disk space

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start all services
docker-compose up -d

# 3. Wait for services to be ready (~30 seconds)
docker-compose logs -f web

# 4. Access the app
```

**That's it!** Visit: http://localhost:8000

## What's Running

| Service | Port | Purpose |
|---------|------|---------|
| Django Web | 8000 | Main application |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache & message broker |
| Celery | - | Background tasks |
| Flower | 5555 | Task monitoring |
| Nginx | 80 | Reverse proxy |

## Common Commands

```bash
# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Restart a service
docker-compose restart web

# Run Django commands
docker-compose exec web python manage.py <command>

# Database backup
docker-compose exec db pg_dump -U postgres taxbudget > backup.sql
```

## Initial Setup Tasks

```bash
# Populate budget categories
docker-compose exec web python manage.py populate_categories

# Build aggregate statistics
docker-compose exec web python manage.py rebuild_aggregates

# Create admin user
docker-compose exec web python manage.py createsuperuser
```

## Access Points

- **Main App**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin (user: admin, pass: admin)
- **Aggregate Results**: http://localhost:8000/aggregate/
- **Submission History**: http://localhost:8000/history/
- **Flower Dashboard**: http://localhost:5555
- **Nginx Proxy**: http://localhost:80

## Troubleshooting

### Port conflicts

```bash
# Check what's using ports
lsof -i :8000
lsof -i :5432
lsof -i :6379

# Change ports in docker-compose.yml if needed
```

### Container won't start

```bash
# View detailed logs
docker-compose logs web

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Permission errors

```bash
# Fix permissions
docker-compose exec web chown -R 1000:1000 /app
```

## Production Deployment

For production, update `.env`:

```bash
DEBUG=False
SECRET_KEY=<generate-new-key>
DB_PASSWORD=<strong-password>
ALLOWED_HOSTS=yourdomain.com
```

Then:

```bash
docker-compose up -d web db redis celery celery-beat
```

## Full Documentation

See `DOCKER.md` for comprehensive documentation including:
- Volume management
- Scaling strategies
- Security best practices
- CI/CD integration
- Performance tuning

## Architecture

```
Browser → Nginx → Django (Gunicorn) → PostgreSQL
                     ↓
                   Redis ← Celery Workers
```

## Stop Everything

```bash
# Stop containers
docker-compose down

# Stop and remove volumes (data will be lost!)
docker-compose down -v
```

## Summary

✅ Full stack in one command  
✅ PostgreSQL + Redis + Celery included  
✅ Hot reload for development  
✅ Production-ready configuration  
✅ Easy scaling and monitoring  

Your app is fully containerized and ready to deploy!
