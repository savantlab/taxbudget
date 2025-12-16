"""
Management command to rebuild aggregate statistics.
Use this for initial setup or data migration.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum, Count, Avg
from allocator.models import CategoryAggregate, BudgetCategory, UserAllocation
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Rebuild CategoryAggregate summary table from existing data (for scalability)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run rebuild as background Celery task'
        )

    def handle(self, *args, **options):
        use_async = options['async']
        
        if use_async:
            self.stdout.write('🚀 Queuing background task to rebuild aggregates...')
            try:
                from allocator.tasks import rebuild_aggregates_from_scratch
                result = rebuild_aggregates_from_scratch.delay()
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Task queued: {result.id}\n'
                    f'Check Celery worker logs for progress.'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'❌ Failed to queue task: {e}\n'
                    f'Make sure Redis and Celery are running.'
                ))
        else:
            self.stdout.write('🔄 Rebuilding aggregates synchronously...')
            self._rebuild_sync()

    def _rebuild_sync(self):
        """Synchronous rebuild of aggregate data"""
        categories = BudgetCategory.objects.all()
        
        self.stdout.write(f'Found {categories.count()} categories')
        
        with transaction.atomic():
            # Clear existing aggregates
            deleted_count = CategoryAggregate.objects.all().delete()[0]
            if deleted_count > 0:
                self.stdout.write(f'Cleared {deleted_count} existing aggregate records')
            
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
                
                self.stdout.write(
                    f'  ✓ {category.name}: {avg_percentage:.2f}% '
                    f'(n={submission_count})'
                )
        
        # Clear and rebuild Redis cache
        self.stdout.write('\n🔄 Refreshing Redis cache...')
        cache.delete('aggregate_allocations')  # Old cache
        cache.delete('aggregate_allocations_v2')
        cache.delete('aggregate_total_submissions')
        
        # Manually rebuild cache
        aggregates = CategoryAggregate.objects.select_related('category').all()
        aggregate_data = []
        for agg in aggregates:
            aggregate_data.append({
                'category': agg.category.name,
                'avg_percentage': float(agg.avg_percentage),
                'color': agg.category.color,
            })
        
        cache.set('aggregate_allocations_v2', aggregate_data, timeout=None)
        
        from allocator.models import AllocationSubmission
        total_submissions = AllocationSubmission.objects.count()
        cache.set('aggregate_total_submissions', total_submissions, timeout=None)
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Successfully rebuilt aggregates for {categories.count()} categories'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'✅ Redis cache refreshed'
        ))
