#!/bin/bash

# ChromeDriver Service - Startup Script
# Starts Django server and ChromeDriver together with graceful shutdown

echo "🚀 Starting Tax Budget Allocator with ChromeDriver Service..."
echo ""

# Activate virtual environment
if [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Warning: Virtual environment not found at ../venv/"
    echo "   Continuing without virtual environment..."
fi

echo ""
echo "📊 Services will be available at:"
echo "   Django App:    http://127.0.0.1:8000/"
echo "   ChromeDriver:  http://127.0.0.1:9515/"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Run the Django management command
python manage.py chromedriver_service "$@"
