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
