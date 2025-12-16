#!/bin/bash

# Tax Budget Allocator - Quick Start Script

echo "🚀 Starting Tax Budget Allocator..."
echo ""

# Activate virtual environment
source ../venv/bin/activate

# Run the development server
echo "📊 Server will be available at:"
echo "   Main form: http://127.0.0.1:8000/"
echo "   Aggregate: http://127.0.0.1:8000/aggregate/"
echo "   Admin:     http://127.0.0.1:8000/admin/"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python manage.py runserver
