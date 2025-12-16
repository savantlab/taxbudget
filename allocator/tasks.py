"""
Celery tasks for Tax Budget Allocator.
Handles background aggregate calculations for scalability.
"""
from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from decimal import Decimal
import json


@shared_task(name='allocator.update_category_aggregates')
def update_category_aggregates(allocations_data):
    """
    Update CategoryAggregate summary table and Redis cache.
    
    Args:
        allocations_data: List of dicts with 'category_id' and 'percentage'
    
    This runs asynchronously after each submission to update aggregates.
    """
    from allocator.models import CategoryAggregate, BudgetCategory
    
    with transaction.atomic():
        for alloc in allocations_data:
            category_id = alloc['category_id']
            percentage = Decimal(str(alloc['percentage']))
            
            # Get or create aggregate record
            aggregate, created = CategoryAggregate.objects.get_or_create(
                category_id=category_id,
                defaults={
                    'total_percentage': 0,
                    'submission_count': 0,
                    'avg_percentage': 0
                }
            )
            
            # Incrementally update
            aggregate.add_submission(percentage)
    
    # After updating DB, refresh Redis cache
    refresh_redis_cache.delay()
    
    return {'status': 'success', 'categories_updated': len(allocations_data)}


@shared_task(name='allocator.refresh_redis_cache')
def refresh_redis_cache():
    """
    Refresh Redis cache with latest aggregate data from summary table.
    Falls back to live calculation if summary table is empty.
    """
    from allocator.models import CategoryAggregate, BudgetCategory, UserAllocation, AllocationSubmission
    from django.db.models import Avg
    
    # Try to get from summary table first
    aggregates = CategoryAggregate.objects.select_related('category').all()
    
    if aggregates.exists():
        # Use pre-calculated summary table
        aggregate_data = []
        for agg in aggregates:
            aggregate_data.append({
                'category': agg.category.name,
                'avg_percentage': float(agg.avg_percentage),
                'color': agg.category.color,
            })
    else:
        # Fallback: Calculate from raw data (slower)
        categories = BudgetCategory.objects.all().order_by('display_order', 'name')
        aggregate_data = []
        
        for category in categories:
            avg_percentage = UserAllocation.objects.filter(
                category=category
            ).aggregate(avg=Avg('percentage'))['avg'] or 0
            
            aggregate_data.append({
                'category': category.name,
                'avg_percentage': round(float(avg_percentage), 2),
                'color': category.color,
            })
    
    # Store in Redis
    cache_key = 'aggregate_allocations_v2'
    cache.set(cache_key, aggregate_data, timeout=None)  # Never expire
    
    # Also store metadata
    total_submissions = AllocationSubmission.objects.count()
    cache.set('aggregate_total_submissions', total_submissions, timeout=None)
    
    return {'status': 'success', 'cached_categories': len(aggregate_data)}


@shared_task(name='allocator.rebuild_aggregates_from_scratch')
def rebuild_aggregates_from_scratch():
    """
    Completely rebuild CategoryAggregate summary table from raw data.
    Use this for initial setup or when data needs to be recalculated.
    """
    from allocator.models import CategoryAggregate, BudgetCategory, UserAllocation
    from django.db.models import Sum, Count, Avg
    
    categories = BudgetCategory.objects.all()
    
    with transaction.atomic():
        # Clear existing aggregates
        CategoryAggregate.objects.all().delete()
        
        # Rebuild from raw data
        for category in categories:
            stats = UserAllocation.objects.filter(
                category=category
            ).aggregate(
                total=Sum('percentage'),
                count=Count('id'),
                avg=Avg('percentage')
            )
            
            total_percentage = stats['total'] or 0
            submission_count = stats['count'] or 0
            avg_percentage = stats['avg'] or 0
            
            CategoryAggregate.objects.create(
                category=category,
                total_percentage=total_percentage,
                submission_count=submission_count,
                avg_percentage=avg_percentage
            )
    
    # Refresh Redis cache
    refresh_redis_cache.delay()
    
    return {
        'status': 'success',
        'categories_rebuilt': categories.count(),
        'message': 'Summary table rebuilt from scratch'
    }
