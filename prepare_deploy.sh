#!/bin/bash
# prepare_deploy.sh
# Prepare Tax Budget Allocator for DigitalOcean deployment

set -e

echo "========================================"
echo "Tax Budget Allocator - Deployment Prep"
echo "Domain: tadpollster.com"
echo "========================================"
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "⚠️  Git repository not initialized"
    read -p "Initialize git repository? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git init
        echo "✓ Git initialized"
    fi
else
    echo "✓ Git repository found"
fi

# Check for GitHub remote
if ! git remote | grep -q origin; then
    echo "⚠️  No GitHub remote configured"
    echo "You'll need to add a remote later:"
    echo "  git remote add origin https://github.com/YOUR_USERNAME/taxbudget.git"
else
    echo "✓ GitHub remote configured: $(git remote get-url origin)"
fi

# Check for doctl
if ! command -v doctl &> /dev/null; then
    echo "⚠️  doctl not found"
    echo "Install with: brew install doctl"
    echo "Then authenticate: doctl auth init"
else
    echo "✓ doctl installed"
    
    # Check authentication
    if doctl account get &> /dev/null; then
        echo "✓ doctl authenticated"
        ACCOUNT=$(doctl account get --format Email --no-header)
        echo "  Account: $ACCOUNT"
    else
        echo "⚠️  doctl not authenticated"
        echo "Run: doctl auth init"
    fi
fi

# Generate .env.production if it doesn't exist
if [ ! -f .env.production ]; then
    echo ""
    echo "Creating .env.production..."
    
    # Generate secret key
    SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    
    cat > .env.production << EOF
# Production Environment Configuration
# Generated on $(date)

# Django Settings
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=tadpollster.com,www.tadpollster.com

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Database (will be set by DigitalOcean)
# DATABASE_URL=postgresql://user:password@host:port/database

# Redis (will be set by DigitalOcean)
# REDIS_URL=redis://host:port

# Celery
# CELERY_BROKER_URL=\${REDIS_URL}
# CELERY_RESULT_BACKEND=\${REDIS_URL}

# Email (configure if needed)
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.example.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=
# EMAIL_HOST_PASSWORD=
EOF
    
    echo "✓ Created .env.production"
    echo "  ⚠️  Keep this file secure! It's in .gitignore"
else
    echo "✓ .env.production exists"
fi

# Check if files are staged
echo ""
echo "Checking repository status..."
if git diff --quiet && git diff --cached --quiet; then
    echo "⚠️  No changes to commit"
else
    echo "✓ Changes detected"
    git status --short
fi

# Summary
echo ""
echo "========================================"
echo "Pre-deployment Checklist"
echo "========================================"
echo ""
echo "Repository:"
echo "  [ ] Initialize git repository"
echo "  [ ] Add GitHub remote"
echo "  [ ] Commit all changes"
echo "  [ ] Push to GitHub"
echo ""
echo "DigitalOcean:"
echo "  [ ] Install doctl (brew install doctl)"
echo "  [ ] Authenticate doctl (doctl auth init)"
echo "  [ ] Review do-app-spec.yaml"
echo "  [ ] Update GitHub repo in do-app-spec.yaml"
echo ""
echo "Domain:"
echo "  [ ] Add domain to DigitalOcean (doctl compute domain create tadpollster.com)"
echo "  [ ] Configure DNS records at registrar"
echo "  [ ] Point nameservers to DigitalOcean:"
echo "      ns1.digitalocean.com"
echo "      ns2.digitalocean.com"
echo "      ns3.digitalocean.com"
echo ""
echo "Deployment:"
echo "  [ ] Review .env.production"
echo "  [ ] Deploy: doctl apps create --spec do-app-spec.yaml"
echo "  [ ] Configure SSL certificate"
echo "  [ ] Run initial migrations"
echo "  [ ] Populate categories"
echo ""
echo "Next steps:"
echo "1. Review DIGITALOCEAN_DEPLOYMENT.md for detailed instructions"
echo "2. Update YOUR_USERNAME in do-app-spec.yaml"
echo "3. Commit and push to GitHub"
echo "4. Deploy to DigitalOcean"
echo ""
echo "Quick deploy command:"
echo "  doctl apps create --spec do-app-spec.yaml"
echo ""
echo "========================================"
