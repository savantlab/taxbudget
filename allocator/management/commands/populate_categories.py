from django.core.management.base import BaseCommand
from allocator.models import BudgetCategory


class Command(BaseCommand):
    help = 'Populate initial budget categories'

    def handle(self, *args, **options):
        categories = [
            {'name': 'Healthcare', 'description': 'Public health services, Medicare, Medicaid', 'color': '#e74c3c', 'display_order': 1},
            {'name': 'Education', 'description': 'Public schools, universities, student aid', 'color': '#3498db', 'display_order': 2},
            {'name': 'Defense & Military', 'description': 'Armed forces, veterans affairs, national security', 'color': '#2c3e50', 'display_order': 3},
            {'name': 'Infrastructure', 'description': 'Roads, bridges, public transit, utilities', 'color': '#95a5a6', 'display_order': 4},
            {'name': 'Social Security', 'description': 'Retirement benefits, disability insurance', 'color': '#9b59b6', 'display_order': 5},
            {'name': 'Environment', 'description': 'Climate action, conservation, renewable energy', 'color': '#27ae60', 'display_order': 6},
            {'name': 'Science & Research', 'description': 'Scientific research, space exploration, innovation', 'color': '#16a085', 'display_order': 7},
            {'name': 'Public Safety', 'description': 'Police, fire departments, emergency services', 'color': '#e67e22', 'display_order': 8},
            {'name': 'Housing & Community', 'description': 'Affordable housing, urban development', 'color': '#f39c12', 'display_order': 9},
            {'name': 'Other', 'description': 'All other government services', 'color': '#34495e', 'display_order': 10},
        ]

        created_count = 0
        for cat_data in categories:
            category, created = BudgetCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'color': cat_data['color'],
                    'display_order': cat_data['display_order'],
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
            else:
                self.stdout.write(f'Category already exists: {category.name}')

        self.stdout.write(self.style.SUCCESS(f'\nTotal: {created_count} new categories created'))
