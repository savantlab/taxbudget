# Tax Budget Allocator - Production Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn psycopg2-binary

# Copy project
COPY . .

# Create directory for static files
RUN mkdir -p /app/staticfiles

# Collect static files (will be overridden by volume in docker-compose)
RUN python manage.py collectstatic --noinput || true

# Create entrypoint script
RUN echo '#!/bin/sh\n\
set -e\n\
\n\
echo "Waiting for PostgreSQL..."\n\
while ! nc -z db 5432; do\n\
  sleep 0.1\n\
done\n\
echo "PostgreSQL started"\n\
\n\
echo "Waiting for Redis..."\n\
while ! nc -z redis 6379; do\n\
  sleep 0.1\n\
done\n\
echo "Redis started"\n\
\n\
echo "Running migrations..."\n\
python manage.py migrate --noinput\n\
\n\
echo "Collecting static files..."\n\
python manage.py collectstatic --noinput\n\
\n\
echo "Creating superuser if needed..."\n\
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username=\"admin\").exists() or User.objects.create_superuser(\"admin\", \"admin@example.com\", \"admin\")" || true\n\
\n\
exec "$@"' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["gunicorn", "taxbudget.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
