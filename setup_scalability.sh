#!/bin/bash

# Setup script for scalability features (Redis + Celery)

echo "🚀 Setting up Tax Budget Allocator for millions of users..."
echo ""

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo "❌ Virtual environment not found at ../venv/"
    echo "Please create one first: python3 -m venv ../venv"
    exit 1
fi

# Activate virtual environment
source ../venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install celery>=5.3.0
pip install redis>=5.0.0
pip install django-redis>=5.4.0
pip install flower>=2.0.1

echo ""
echo "✅ Dependencies installed!"
echo ""

# Check if Redis is running
echo "🔍 Checking Redis..."
if redis-cli ping &> /dev/null; then
    echo "✅ Redis is running"
else
    echo "⚠️  Redis is not running"
    echo ""
    echo "To install and start Redis:"
    echo "  macOS:  brew install redis && brew services start redis"
    echo "  Linux:  sudo apt-get install redis-server && sudo systemctl start redis"
    echo ""
fi

# Create migrations
echo ""
echo "🔄 Creating database migrations..."
python manage.py makemigrations allocator

# Apply migrations
echo ""
echo "🔄 Applying migrations..."
python manage.py migrate

# Build initial aggregates
echo ""
echo "📊 Building initial aggregate statistics..."
python manage.py rebuild_aggregates

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo ""
echo "1. Start Celery worker (in a separate terminal):"
echo "   celery -A taxbudget worker --loglevel=info"
echo ""
echo "2. Start Django server:"
echo "   python manage.py runserver"
echo ""
echo "3. (Optional) Start Flower monitoring dashboard:"
echo "   celery -A taxbudget flower"
echo "   Access at: http://localhost:5555"
echo ""
echo "📚 See SCALABILITY.md for detailed documentation"
