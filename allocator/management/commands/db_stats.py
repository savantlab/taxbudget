"""
Management command to display database statistics
Usage: python manage.py db_stats
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from allocator.models import (
    BudgetCategory,
    UserAllocation,
    AllocationSubmission,
    CategoryAggregate
)


class Command(BaseCommand):
    help = 'Display database statistics for Tax Budget Allocator'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to include in recent activity (default: 7)'
        )
        parser.add_argument(
            '--us-only',
            action='store_true',
            help='Filter to US IP addresses only (TODO: requires geolocation)'
        )

    def handle(self, *args, **options):
        days = options['days']
        us_only = options['us_only']
        
        if us_only:
            self.stdout.write(self.style.WARNING(
                '⚠️  US-only filtering not yet implemented (requires geolocation setup)'
            ))
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('TAX BUDGET ALLOCATOR - DATABASE STATISTICS'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        # Overall Stats
        self.print_overall_stats()
        
        # Recent Activity
        self.print_recent_activity(days)
        
        # Category Aggregates
        self.print_category_aggregates()
        
        # User Engagement
        self.print_user_engagement()
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60 + '\n'))

    def print_overall_stats(self):
        """Overall database statistics"""
        total_submissions = AllocationSubmission.objects.count()
        total_allocations = UserAllocation.objects.count()
        unique_users = UserAllocation.objects.values('user_id').distinct().count()
        unique_sessions = UserAllocation.objects.values('session_key').distinct().count()
        
        self.stdout.write(self.style.HTTP_INFO('📊 OVERALL STATISTICS'))
        self.stdout.write(f'  Total Submissions: {total_submissions:,}')
        self.stdout.write(f'  Total Allocations: {total_allocations:,}')
        self.stdout.write(f'  Unique Users (cookie): {unique_users:,}')
        self.stdout.write(f'  Unique Sessions: {unique_sessions:,}')
        self.stdout.write('')

    def print_recent_activity(self, days):
        """Recent submission activity"""
        cutoff = timezone.now() - timedelta(days=days)
        
        recent_submissions = AllocationSubmission.objects.filter(
            submitted_at__gte=cutoff
        ).count()
        
        recent_allocations = UserAllocation.objects.filter(
            created_at__gte=cutoff
        ).count()
        
        self.stdout.write(self.style.HTTP_INFO(f'📈 RECENT ACTIVITY (Last {days} days)'))
        self.stdout.write(f'  Submissions: {recent_submissions:,}')
        self.stdout.write(f'  Allocations: {recent_allocations:,}')
        
        # Daily breakdown
        daily_counts = AllocationSubmission.objects.filter(
            submitted_at__gte=cutoff
        ).extra(
            select={'day': 'DATE(submitted_at)'}
        ).values('day').annotate(count=Count('id')).order_by('-day')
        
        if daily_counts:
            self.stdout.write('\n  Daily Breakdown:')
            for day_data in daily_counts[:10]:  # Show last 10 days
                self.stdout.write(f'    {day_data["day"]}: {day_data["count"]} submissions')
        
        self.stdout.write('')

    def print_category_aggregates(self):
        """Category-level aggregate statistics"""
        self.stdout.write(self.style.HTTP_INFO('💰 CATEGORY AGGREGATES'))
        
        aggregates = CategoryAggregate.objects.select_related('category').order_by(
            '-avg_percentage'
        )
        
        if not aggregates.exists():
            self.stdout.write(self.style.WARNING('  No aggregate data available'))
            self.stdout.write('')
            return
        
        self.stdout.write(f'  {"Category":<30} {"Avg %":>10} {"Submissions":>15}')
        self.stdout.write('  ' + '-'*58)
        
        for agg in aggregates:
            self.stdout.write(
                f'  {agg.category.name:<30} '
                f'{float(agg.avg_percentage):>9.2f}% '
                f'{agg.submission_count:>14,}'
            )
        
        self.stdout.write('')

    def print_user_engagement(self):
        """User engagement patterns"""
        self.stdout.write(self.style.HTTP_INFO('👥 USER ENGAGEMENT'))
        
        # Repeat users (by user_id)
        repeat_users = UserAllocation.objects.filter(
            user_id__isnull=False
        ).values('user_id').annotate(
            submission_count=Count('id')
        ).filter(submission_count__gt=1).count()
        
        total_users = UserAllocation.objects.filter(
            user_id__isnull=False
        ).values('user_id').distinct().count()
        
        if total_users > 0:
            repeat_rate = (repeat_users / total_users) * 100
            self.stdout.write(f'  Repeat Users: {repeat_users:,} / {total_users:,} ({repeat_rate:.1f}%)')
        else:
            self.stdout.write('  No user data available')
        
        # Most common submission counts
        submission_patterns = UserAllocation.objects.filter(
            user_id__isnull=False
        ).values('user_id').annotate(
            submissions=Count('id')
        ).values('submissions').annotate(
            user_count=Count('user_id')
        ).order_by('-submissions')[:5]
        
        if submission_patterns:
            self.stdout.write('\n  Submission Patterns:')
            for pattern in submission_patterns:
                self.stdout.write(
                    f'    {pattern["user_count"]:,} users with '
                    f'{pattern["submissions"]} submission(s)'
                )
        
        self.stdout.write('')
