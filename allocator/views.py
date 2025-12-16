from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Avg
from django.core.cache import cache
from django.utils import timezone
from .models import BudgetCategory, UserAllocation, AllocationSubmission
from .forms import TaxAllocationForm
import uuid
import json


def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_or_create_user_id(request):
    """Get user_id if consented; otherwise None."""
    consent = request.COOKIES.get('cookie_consent')
    if consent != 'accepted':
        return None
    user_id = request.COOKIES.get('tax_allocator_user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
    return user_id


@require_http_methods(["GET", "POST"])
def allocate_view(request):
    """Main allocation form view - handles both GET and POST"""
    if request.method == 'POST':
        form = TaxAllocationForm(request.POST)
        if form.is_valid():
            # Get or create user_id from cookie
            user_id = get_or_create_user_id(request)
            
            # Generate unique session key for this submission
            session_key = str(uuid.uuid4())
            ip_address = get_client_ip(request)
            submission_time = timezone.now()
            
            # Save all allocations
            allocations = form.get_allocations()
            for category_id, percentage in allocations.items():
                UserAllocation.objects.create(
                    session_key=session_key,
                    user_id=user_id,
                    category_id=category_id,
                    percentage=percentage,
                    created_at=submission_time,
                    ip_address=ip_address
                )
            
            # Track submission
            AllocationSubmission.objects.create(
                session_key=session_key,
                user_id=user_id,
                submitted_at=submission_time,
                ip_address=ip_address
            )
            
            # Queue background task to update aggregates (scalable approach)
            try:
                from allocator.tasks import update_category_aggregates
                allocations_data = [
                    {'category_id': cat_id, 'percentage': float(pct)}
                    for cat_id, pct in allocations.items()
                ]
                update_category_aggregates.delay(allocations_data)
            except Exception as e:
                # Fallback: invalidate old cache if Celery/Redis not available
                cache.delete('aggregate_allocations')
                cache.delete('aggregate_allocations_v2')
            
            messages.success(request, 'Your allocation has been submitted successfully!')
            response = redirect('results', session_key=session_key)
            
            # Set cookie with user_id (expires in 1 year) if consented
            if user_id:
                response.set_cookie(
                    'tax_allocator_user_id',
                    user_id,
                    max_age=365*24*60*60,  # 1 year in seconds
                    httponly=True,  # Prevent JavaScript access
                    samesite='Lax'  # CSRF protection
                )
            
            return response
    else:
        form = TaxAllocationForm()
    
    categories = BudgetCategory.objects.all().order_by('display_order', 'name')
    
    # Check if user has previous submissions
    user_id = request.COOKIES.get('tax_allocator_user_id')
    previous_submissions = None
    if user_id:
        previous_submissions = AllocationSubmission.objects.filter(
            user_id=user_id
        ).order_by('-submitted_at')[:5]  # Last 5 submissions
    
    return render(request, 'allocator/allocate.html', {
        'form': form,
        'categories': categories,
        'previous_submissions': previous_submissions,
    })


def results_view(request, session_key):
    """Display user's submission results with pie chart"""
    allocations = UserAllocation.objects.filter(
        session_key=session_key
    ).select_related('category').order_by('category__display_order', 'category__name')
    
    if not allocations.exists():
        messages.error(request, 'Allocation not found.')
        return redirect('allocate')
    
    # Prepare data for Chart.js
    chart_data = {
        'labels': [alloc.category.name for alloc in allocations],
        'data': [float(alloc.percentage) for alloc in allocations],
        'colors': [alloc.category.color for alloc in allocations],
    }
    
    return render(request, 'allocator/results.html', {
        'allocations': allocations,
        'chart_data': json.dumps(chart_data),
        'session_key': session_key,
    })


def aggregate_view(request):
    """Display aggregate statistics - optimized for millions of users"""
    from allocator.models import CategoryAggregate
    
    # TIER 1: Try Redis cache (fastest - instant for millions of users)
    cache_key = 'aggregate_allocations_v2'
    aggregate_data = cache.get(cache_key)
    total_submissions = cache.get('aggregate_total_submissions')
    
    if aggregate_data is None:
        # TIER 2: Try summary table (fast - pre-calculated)
        aggregates = CategoryAggregate.objects.select_related('category').all()
        
        if aggregates.exists():
            aggregate_data = []
            for agg in aggregates:
                aggregate_data.append({
                    'category': agg.category.name,
                    'avg_percentage': float(agg.avg_percentage),
                    'color': agg.category.color,
                })
            
            # Store in Redis for next time
            cache.set(cache_key, aggregate_data, timeout=None)
        else:
            # TIER 3: Fallback to live calculation (slower - for initial setup)
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
            
            # Cache for 5 minutes (old behavior)
            cache.set(cache_key, aggregate_data, 300)
    
    # Get total submissions
    if total_submissions is None:
        total_submissions = AllocationSubmission.objects.count()
        cache.set('aggregate_total_submissions', total_submissions, timeout=None)
    
    # Prepare chart data
    chart_data = {
        'labels': [item['category'] for item in aggregate_data],
        'data': [item['avg_percentage'] for item in aggregate_data],
        'colors': [item['color'] for item in aggregate_data],
    }
    
    return render(request, 'allocator/aggregate.html', {
        'aggregate_data': aggregate_data,
        'chart_data': json.dumps(chart_data),
        'total_submissions': total_submissions,
    })


def history_view(request):
    """Display user's submission history"""
    user_id = request.COOKIES.get('tax_allocator_user_id')
    
    if not user_id:
        messages.info(request, 'No submission history found. Submit an allocation to start tracking your history.')
        return redirect('allocate')
    
    # Get all submissions for this user
    submissions = AllocationSubmission.objects.filter(
        user_id=user_id
    ).order_by('-submitted_at')
    
    if not submissions.exists():
        messages.info(request, 'No submission history found.')
        return redirect('allocate')
    
    # Get allocations for each submission
    submission_data = []
    for submission in submissions:
        allocations = UserAllocation.objects.filter(
            session_key=submission.session_key
        ).select_related('category').order_by('category__display_order')
        
        submission_data.append({
            'submission': submission,
            'allocations': allocations,
        })
    
    return render(request, 'allocator/history.html', {
        'submission_data': submission_data,
        'total_submissions': submissions.count(),
    })
