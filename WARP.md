# Warp AI Instructions - Tax Budget Allocator

## Project Overview
Tax Budget Allocator (tadpollster.com) is a Django application that allows users to allocate their hypothetical tax dollars across 10 budget categories and visualize aggregate results.

## Tech Stack
- **Backend**: Django 6.0
- **Database**: SQLite (production), PostgreSQL (optional)
- **Cache**: Redis (manual droplet at 159.65.255.161:6379)
- **Task Queue**: Celery + Celery Beat
- **Frontend**: Bootstrap 5, Chart.js
- **Deployment**: DigitalOcean App Platform
- **Server**: Gunicorn with 4 workers

## Project Structure
```
taxbudget/
├── allocator/              # Main Django app
│   ├── models.py          # BudgetCategory, UserAllocation, AllocationSubmission, CategoryAggregate
│   ├── views.py           # Form submission, results, aggregate views
│   ├── forms.py           # TaxAllocationForm with 100% validation
│   ├── tasks.py           # Celery tasks for async processing
│   ├── templates/         # HTML templates
│   └── management/commands/
├── taxbudget/             # Project settings
│   ├── settings.py        # Cache & database configuration
│   ├── celery.py          # Celery configuration
│   └── urls.py
└── manage.py
```

## Key Architecture Decisions

### 1. Scalability (O(1) Complexity)
The app uses a 3-tier system for aggregate calculations:
- **Tier 1**: Redis cache (instant - O(1))
- **Tier 2**: CategoryAggregate summary table (fast - O(10))
- **Tier 3**: Raw calculation fallback (slower - O(n))

**Never** implement features that require scanning all UserAllocation records on every request. Always use:
1. CategoryAggregate for pre-calculated totals
2. Celery tasks for async updates
3. Redis for caching

### 2. User Tracking
- **Cookie-based**: No authentication required
- **Cookie name**: `tax_allocator_user_id` (UUID)
- **GDPR/CCPA compliant**: Cookie consent banner required
- **Never** implement password-based authentication unless explicitly requested

### 3. Form Validation
- All allocations must sum to exactly 100%
- Client-side AND server-side validation required
- Real-time feedback in the UI

### 4. Background Processing
All aggregate updates MUST be async:
```python
# Good - async update
from allocator.tasks import update_category_aggregates
update_category_aggregates.delay(allocations_data)

# Bad - synchronous database scan
UserAllocation.objects.aggregate(Avg('percentage'))
```

## Development Workflow

### Starting Development
```bash
cd /Users/savantlab/Savantlab/taxbudget
source venv/bin/activate
python manage.py runserver
```

### Required Services
```bash
# Redis (required for caching)
redis-cli ping  # Verify it's running

# Celery Worker (required for async tasks)
celery -A taxbudget worker --loglevel=info

# Celery Beat (optional - for scheduled tasks)
celery -A taxbudget beat --loglevel=info
```

### Testing
```bash
# Run all tests (29 tests)
python manage.py test allocator

# Run specific test
python manage.py test allocator.tests.TestAggregateView
```

## Deployment

### CI/CD
- **Platform**: DigitalOcean App Platform
- **Trigger**: Auto-deploy on push to `main` branch
- **Config**: `do-app-spec.yaml`
- **Deployment time**: ~2 minutes

### To Deploy Changes
```bash
git add .
git commit -m "Description"
git push origin main
# DigitalOcean automatically deploys
```

### Manual Deployment
```bash
doctl apps update 3b89d417-366d-43eb-908b-eacbb4f519dc --spec do-app-spec.yaml
```

### Check Deployment Status
```bash
doctl apps list-deployments 3b89d417-366d-43eb-908b-eacbb4f519dc
doctl apps logs 3b89d417-366d-43eb-908b-eacbb4f519dc --type run --follow
```

## Business Logic Guidelines

### Adding New Features

#### 1. New Budget Categories
```bash
# Edit allocator/management/commands/populate_categories.py
# Then run:
python manage.py populate_categories
```

#### 2. New Aggregate Calculations
**Always use CategoryAggregate model**:
```python
# Good
from allocator.models import CategoryAggregate
aggregates = CategoryAggregate.objects.all()

# Bad - scans all records
from allocator.models import UserAllocation
UserAllocation.objects.filter(category=cat).aggregate(Avg('percentage'))
```

#### 3. New Background Tasks
Add to `allocator/tasks.py`:
```python
from celery import shared_task

@shared_task
def your_task_name(data):
    # Your logic here
    pass
```

#### 4. New API Endpoints
- Add view to `allocator/views.py`
- Add URL to `allocator/urls.py`
- Use POST for mutations, GET for reads
- Always include CSRF protection

### Data Integrity

#### Rebuilding Aggregates
```bash
# If aggregates become out of sync
python manage.py rebuild_aggregates

# Or async (for production)
python manage.py rebuild_aggregates --async
```

#### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## Performance Requirements

### Response Time Targets
- Homepage: < 100ms
- Form submission: < 200ms
- Aggregate page: < 50ms (with Redis)
- Individual results: < 100ms

### Optimization Checklist
- [ ] Use `select_related()` for foreign keys
- [ ] Use `prefetch_related()` for reverse foreign keys
- [ ] Cache expensive queries in Redis
- [ ] Use Celery for slow operations
- [ ] Add database indexes for frequently queried fields

## Security Guidelines

### Environment Variables
**Never hardcode secrets**. Current production secrets in `do-app-spec.yaml`:
- `SECRET_KEY` - Django secret (rotate periodically)
- `REDIS_URL` - Redis connection string
- `ALLOWED_HOSTS` - Whitelist of domains

### CSRF Protection
- All POST requests must include CSRF token
- Forms use `{% csrf_token %}` template tag
- AJAX requests must include CSRF header

### Input Validation
- Always validate on both client and server
- Use Django forms for automatic validation
- Sanitize user input (Django templates auto-escape)

## Common Tasks

### Adding a New View
1. Create view function in `allocator/views.py`
2. Add URL pattern in `allocator/urls.py`
3. Create template in `allocator/templates/allocator/`
4. Add tests in `allocator/tests.py`

### Modifying Form Fields
1. Update `allocator/forms.py`
2. Update template with new fields
3. Update model if storing new data
4. Create migration: `python manage.py makemigrations`
5. Run tests

### Adding Celery Task
1. Define task in `allocator/tasks.py`
2. Call with `.delay()` or `.apply_async()`
3. Test with Celery worker running
4. Monitor via Flower: `celery -A taxbudget flower`

## Monitoring & Debugging

### Check Redis Cache
```bash
redis-cli
GET aggregate_allocations_v2
GET aggregate_total_submissions
KEYS aggregate*
```

### Check Celery Tasks
```bash
celery -A taxbudget inspect active
celery -A taxbudget inspect scheduled
celery -A taxbudget inspect stats
```

### Check Logs
```bash
# Local
python manage.py runserver  # Console output

# Production
doctl apps logs 3b89d417-366d-43eb-908b-eacbb4f519dc --type run --follow
```

## Scaling Considerations

### Current Configuration
- Web: 2× basic-s (2GB RAM each)
- Celery Worker: 1× basic-s (2GB RAM)
- Celery Beat: 1× basic-xs (1GB RAM)
- Redis: Manual droplet (2GB)

### When to Scale Up
- **Web**: Response times > 200ms consistently
- **Celery**: Task queue backlog > 1000 tasks
- **Redis**: Memory usage > 80%

### How to Scale
Edit `do-app-spec.yaml`:
- Increase `instance_count` for horizontal scaling
- Increase `instance_size_slug` for vertical scaling
- Deploy: `doctl apps update 3b89d417-366d-43eb-908b-eacbb4f519dc --spec do-app-spec.yaml`

## Documentation Reference

For detailed information, see:
- `README.md` - General overview and quick start
- `SCALABILITY.md` - Performance architecture
- `COST_ANALYSIS_BY_PROVIDER.md` - Infrastructure costs
- `DOCKER.md` - Docker deployment
- `COOKIES_FEATURE.md` - Cookie tracking implementation
- `COOKIE_CONSENT.md` - GDPR/CCPA compliance
- `CHROMEDRIVER_SERVICE.md` - Automated testing setup

## Important Rules

1. **Never commit without testing**: Run `python manage.py test` first
2. **Never bypass Celery for aggregates**: Use async tasks for updates
3. **Never hardcode secrets**: Use environment variables
4. **Never skip migrations**: Always run after model changes
5. **Always maintain O(1) complexity**: Use summary tables and caching
6. **Always validate 100% allocation**: Client-side AND server-side
7. **Always use cookie-based tracking**: No passwords unless explicitly requested
8. **Always include co-author line in commits**: `Co-Authored-By: Warp <agent@warp.dev>`

## Contact & Context

- **App URL**: https://tadpollster.com
- **App ID**: 3b89d417-366d-43eb-908b-eacbb4f519dc
- **Region**: NYC
- **Repository**: savantlab/taxbudget (GitHub)
- **Redis IP**: 159.65.255.161:6379
