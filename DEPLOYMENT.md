# Deployment Guide - Tax Budget Allocator

This guide covers deploying the Tax Budget Allocator to scale to millions of users.

## Quick Start (Development)

```bash
# Navigate to project
cd taxbudget

# Start the server
./start_server.sh

# Or manually:
source ../venv/bin/activate
python manage.py runserver
```

Access at: http://127.0.0.1:8000/

## Production Deployment

### Prerequisites

```bash
# Install production dependencies
pip install gunicorn psycopg2-binary django-redis redis sentry-sdk
```

### 1. Database Setup (PostgreSQL)

```bash
# Install PostgreSQL
brew install postgresql  # macOS
# or: apt-get install postgresql  # Ubuntu

# Create database
psql postgres
CREATE DATABASE taxbudget;
CREATE USER taxbudget_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE taxbudget TO taxbudget_user;
\q

# Update environment variables
export DB_NAME=taxbudget
export DB_USER=taxbudget_user
export DB_PASSWORD=secure_password
export DB_HOST=localhost
export DB_PORT=5432
```

Update `settings.py` to use PostgreSQL instead of SQLite.

### 2. Redis Setup

```bash
# Install Redis
brew install redis  # macOS
# or: apt-get install redis-server  # Ubuntu

# Start Redis
redis-server

# Update environment
export REDIS_URL=redis://127.0.0.1:6379/1
```

Update `settings.py` to use Redis cache backend.

### 3. Security Configuration

```bash
# Generate new secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Set environment variables
export DJANGO_SECRET_KEY='your-generated-key'
export DEBUG=False
export ALLOWED_HOSTS='yourdomain.com,www.yourdomain.com'
```

### 4. Static Files

```bash
# Collect static files
python manage.py collectstatic --noinput
```

### 5. Database Migrations

```bash
python manage.py migrate
python manage.py populate_categories
python manage.py createsuperuser
```

### 6. Run with Gunicorn

```bash
# Basic command
gunicorn taxbudget.wsgi:application

# Production with workers
gunicorn taxbudget.wsgi:application \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
```

### 7. Nginx Configuration

Create `/etc/nginx/sites-available/taxbudget`:

```nginx
upstream taxbudget_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    client_max_body_size 10M;

    location /static/ {
        alias /path/to/taxbudget/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://taxbudget_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/taxbudget /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8. Systemd Service

Create `/etc/systemd/system/taxbudget.service`:

```ini
[Unit]
Description=Tax Budget Allocator Gunicorn Daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/taxbudget
Environment="PATH=/path/to/venv/bin"
Environment="DJANGO_SECRET_KEY=your-key"
Environment="DB_NAME=taxbudget"
Environment="DB_USER=taxbudget_user"
Environment="DB_PASSWORD=secure_password"
ExecStart=/path/to/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    taxbudget.wsgi:application

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable taxbudget
sudo systemctl start taxbudget
sudo systemctl status taxbudget
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run gunicorn
CMD ["gunicorn", "taxbudget.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: taxbudget
      POSTGRES_USER: taxbudget_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  web:
    build: .
    command: gunicorn taxbudget.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DB_NAME=taxbudget
      - DB_USER=taxbudget_user
      - DB_PASSWORD=secure_password
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/1
    depends_on:
      - db
      - redis

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - static_volume:/app/staticfiles
    depends_on:
      - web

volumes:
  postgres_data:
  redis_data:
  static_volume:
```

Build and run:
```bash
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py populate_categories
docker-compose exec web python manage.py createsuperuser
```

## Kubernetes Deployment

### deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: taxbudget
spec:
  replicas: 3
  selector:
    matchLabels:
      app: taxbudget
  template:
    metadata:
      labels:
        app: taxbudget
    spec:
      containers:
      - name: web
        image: your-registry/taxbudget:latest
        ports:
        - containerPort: 8000
        env:
        - name: DEBUG
          value: "False"
        - name: DB_HOST
          value: postgres-service
        - name: REDIS_URL
          value: redis://redis-service:6379/1
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: taxbudget-service
spec:
  selector:
    app: taxbudget
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: taxbudget-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: taxbudget
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

Deploy:
```bash
kubectl apply -f deployment.yaml
```

## Monitoring & Observability

### Sentry (Error Tracking)

```python
# In settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
)
```

### Prometheus Metrics

```bash
pip install django-prometheus
```

Add to `INSTALLED_APPS` and `MIDDLEWARE` in settings.py, then expose metrics at `/metrics`.

## Load Testing

```bash
# Install Locust
pip install locust

# Create locustfile.py
from locust import HttpUser, task, between

class TaxAllocatorUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def view_form(self):
        self.client.get("/")
    
    @task(3)
    def submit_allocation(self):
        self.client.post("/", {
            "category_1": "20.00",
            "category_2": "15.00",
            # ... all categories summing to 100
        })
    
    @task(2)
    def view_aggregate(self):
        self.client.get("/aggregate/")

# Run load test
locust -f locustfile.py --host=http://localhost:8000
```

## Performance Benchmarks

Expected performance with optimizations:

- **Without caching**: ~100-200 requests/second
- **With Redis caching**: ~1000-2000 requests/second
- **With CDN + load balancing**: 10,000+ requests/second

## Cost Estimation (AWS)

For 1 million active users/month:

- **EC2 instances** (3x t3.medium): ~$75/month
- **RDS PostgreSQL** (db.t3.medium): ~$70/month
- **ElastiCache Redis** (cache.t3.micro): ~$15/month
- **ALB**: ~$20/month
- **Data transfer**: ~$50/month
- **CloudFront CDN**: ~$50/month

**Total: ~$280/month**

Scale up as needed with auto-scaling groups.

## Troubleshooting

### High Database Load
- Add read replicas
- Increase cache timeout
- Add database connection pooling (PgBouncer)

### High Memory Usage
- Reduce Gunicorn worker count
- Enable swap space
- Use async workers (gevent/eventlet)

### Slow Response Times
- Enable query logging to find slow queries
- Add database indexes
- Increase cache hit rate
- Use CDN for static assets

## Backup Strategy

```bash
# Database backup
pg_dump taxbudget > backup_$(date +%Y%m%d).sql

# Automated daily backups
0 2 * * * /usr/bin/pg_dump taxbudget > /backups/taxbudget_$(date +\%Y\%m\%d).sql
```

## Security Checklist

- [ ] Change SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS
- [ ] Enable HTTPS (SSL/TLS)
- [ ] Set secure cookie flags
- [ ] Enable HSTS
- [ ] Configure CSRF protection
- [ ] Set up firewall rules
- [ ] Regular security updates
- [ ] Database backups
- [ ] Monitor error logs
- [ ] Rate limiting (django-ratelimit)

## Support

For issues or questions, check:
- README.md for basic usage
- Django docs: https://docs.djangoproject.com/
- Deployment checklist: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
