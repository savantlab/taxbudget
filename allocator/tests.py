from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from decimal import Decimal
import uuid

from .models import BudgetCategory, UserAllocation, AllocationSubmission, CategoryAggregate
from .forms import TaxAllocationForm


class BudgetCategoryModelTest(TestCase):
    """Test BudgetCategory model"""

    def setUp(self):
        self.category = BudgetCategory.objects.create(
            name="Healthcare",
            description="Healthcare services",
            color="#ff0000",
            display_order=1
        )

    def test_category_creation(self):
        """Test category is created correctly"""
        self.assertEqual(self.category.name, "Healthcare")
        self.assertEqual(self.category.color, "#ff0000")
        self.assertEqual(self.category.display_order, 1)

    def test_category_str(self):
        """Test string representation"""
        self.assertEqual(str(self.category), "Healthcare")

    def test_category_ordering(self):
        """Test categories are ordered by display_order"""
        BudgetCategory.objects.create(name="Education", display_order=2)
        BudgetCategory.objects.create(name="Defense", display_order=0)
        
        categories = list(BudgetCategory.objects.all())
        self.assertEqual(categories[0].name, "Defense")
        self.assertEqual(categories[1].name, "Healthcare")
        self.assertEqual(categories[2].name, "Education")


class UserAllocationModelTest(TestCase):
    """Test UserAllocation model"""

    def setUp(self):
        self.category = BudgetCategory.objects.create(name="Healthcare")
        self.session_key = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())

    def test_allocation_creation(self):
        """Test allocation is created correctly"""
        allocation = UserAllocation.objects.create(
            session_key=self.session_key,
            user_id=self.user_id,
            category=self.category,
            percentage=Decimal('25.50'),
            ip_address='127.0.0.1'
        )
        
        self.assertEqual(allocation.percentage, Decimal('25.50'))
        self.assertEqual(allocation.category, self.category)
        self.assertEqual(allocation.user_id, self.user_id)

    def test_percentage_validators(self):
        """Test percentage is between 0 and 100"""
        # Valid percentage
        allocation = UserAllocation(session_key=self.session_key, category=self.category, percentage=50)
        allocation.full_clean()  # Should not raise
        
        # Invalid percentages should raise during validation
        from django.core.exceptions import ValidationError
        
        invalid_allocation = UserAllocation(session_key=self.session_key, category=self.category, percentage=150)
        with self.assertRaises(ValidationError):
            invalid_allocation.full_clean()


class AllocationSubmissionModelTest(TestCase):
    """Test AllocationSubmission model"""

    def setUp(self):
        self.session_key = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())

    def test_submission_creation(self):
        """Test submission is created correctly"""
        submission = AllocationSubmission.objects.create(
            session_key=self.session_key,
            user_id=self.user_id,
            ip_address='127.0.0.1'
        )
        
        self.assertEqual(submission.session_key, self.session_key)
        self.assertEqual(submission.user_id, self.user_id)
        self.assertIsNotNone(submission.submitted_at)

    def test_submission_ordering(self):
        """Test submissions are ordered by date descending"""
        submission1 = AllocationSubmission.objects.create(session_key=str(uuid.uuid4()))
        submission2 = AllocationSubmission.objects.create(session_key=str(uuid.uuid4()))
        
        submissions = list(AllocationSubmission.objects.all())
        self.assertEqual(submissions[0], submission2)  # Most recent first
        self.assertEqual(submissions[1], submission1)


class CategoryAggregateModelTest(TestCase):
    """Test CategoryAggregate model"""

    def setUp(self):
        self.category = BudgetCategory.objects.create(name="Healthcare")
        self.aggregate = CategoryAggregate.objects.create(
            category=self.category,
            total_percentage=Decimal('250.00'),
            submission_count=10
        )

    def test_aggregate_creation(self):
        """Test aggregate is created correctly"""
        self.assertEqual(self.aggregate.category, self.category)
        self.assertEqual(self.aggregate.total_percentage, Decimal('250.00'))
        self.assertEqual(self.aggregate.submission_count, 10)

    def test_update_average(self):
        """Test average calculation"""
        self.aggregate.update_average()
        self.assertEqual(self.aggregate.avg_percentage, Decimal('25.00'))

    def test_add_submission(self):
        """Test incrementally adding submissions"""
        self.aggregate.add_submission(30)
        
        self.assertEqual(self.aggregate.total_percentage, Decimal('280.00'))
        self.assertEqual(self.aggregate.submission_count, 11)
        self.assertAlmostEqual(float(self.aggregate.avg_percentage), 25.45, places=2)

    def test_add_submission_with_zero_count(self):
        """Test adding submission when count is zero"""
        new_category = BudgetCategory.objects.create(name="Education")
        new_aggregate = CategoryAggregate.objects.create(
            category=new_category,
            total_percentage=Decimal('0'),
            submission_count=0
        )
        
        new_aggregate.add_submission(25)
        self.assertEqual(new_aggregate.total_percentage, Decimal('25'))
        self.assertEqual(new_aggregate.submission_count, 1)
        self.assertEqual(new_aggregate.avg_percentage, Decimal('25'))


class TaxAllocationFormTest(TestCase):
    """Test TaxAllocationForm"""

    def setUp(self):
        # Create 10 categories
        for i in range(10):
            BudgetCategory.objects.create(
                name=f"Category {i}",
                display_order=i
            )

    def test_form_valid_data(self):
        """Test form with valid data totaling 100%"""
        categories = BudgetCategory.objects.all()
        form_data = {}
        
        # Allocate 10% to each category
        for cat in categories:
            form_data[f'category_{cat.id}'] = '10'
        
        form = TaxAllocationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_not_100_percent(self):
        """Test form rejects data not totaling 100%"""
        categories = BudgetCategory.objects.all()
        form_data = {}
        
        # Allocate 5% to each (total = 50%)
        for cat in categories:
            form_data[f'category_{cat.id}'] = '5'
        
        form = TaxAllocationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Total allocation must equal 100%', str(form.errors))

    def test_form_negative_values(self):
        """Test form rejects negative values"""
        categories = list(BudgetCategory.objects.all())
        form_data = {}
        
        form_data[f'category_{categories[0].id}'] = '-10'
        for cat in categories[1:]:
            form_data[f'category_{cat.id}'] = str(110 / 9)  # Make it total 100
        
        form = TaxAllocationForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_form_over_100_percent(self):
        """Test form rejects over 100%"""
        categories = BudgetCategory.objects.all()
        form_data = {}
        
        for cat in categories:
            form_data[f'category_{cat.id}'] = '15'  # Total = 150%
        
        form = TaxAllocationForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_get_allocations(self):
        """Test get_allocations method returns correct dict"""
        categories = BudgetCategory.objects.all()
        form_data = {}
        
        for cat in categories:
            form_data[f'category_{cat.id}'] = '10'
        
        form = TaxAllocationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        allocations = form.get_allocations()
        self.assertEqual(len(allocations), 10)
        for cat_id, percentage in allocations.items():
            self.assertEqual(percentage, Decimal('10'))


class AllocateViewTest(TestCase):
    """Test allocate_view"""

    def setUp(self):
        self.client = Client()
        # Simulate user accepting cookies
        self.client.cookies['cookie_consent'] = 'accepted'
        # Create 10 categories
        for i in range(10):
            BudgetCategory.objects.create(
                name=f"Category {i}",
                display_order=i
            )

    def test_get_allocate_view(self):
        """Test GET request to allocate view"""
        response = self.client.get(reverse('allocate'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'allocator/allocate.html')
        self.assertIn('form', response.context)
        self.assertIn('categories', response.context)

    def test_post_valid_allocation(self):
        """Test POST with valid allocation"""
        categories = BudgetCategory.objects.all()
        post_data = {}
        
        for cat in categories:
            post_data[f'category_{cat.id}'] = '10'
        
        response = self.client.post(reverse('allocate'), post_data)
        
        # Should redirect to results
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/results/'))
        
        # Should create allocations
        self.assertEqual(UserAllocation.objects.count(), 10)
        self.assertEqual(AllocationSubmission.objects.count(), 1)
        
        # Should set cookie
        self.assertIn('tax_allocator_user_id', response.cookies)

    def test_post_invalid_allocation(self):
        """Test POST with invalid allocation"""
        categories = BudgetCategory.objects.all()
        post_data = {}
        
        # Only allocate 50%
        for cat in categories:
            post_data[f'category_{cat.id}'] = '5'
        
        response = self.client.post(reverse('allocate'), post_data)
        
        # Should not redirect
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], None, 'Total allocation must equal 100%. Current total: 50.00%')
        
        # Should not create allocations
        self.assertEqual(UserAllocation.objects.count(), 0)

    def test_cookie_persistence(self):
        """Test user_id cookie persists across submissions"""
        categories = BudgetCategory.objects.all()
        post_data = {f'category_{cat.id}': '10' for cat in categories}
        
        # First submission
        response1 = self.client.post(reverse('allocate'), post_data)
        user_id_1 = response1.cookies['tax_allocator_user_id'].value
        
        # Second submission (cookie should be reused)
        response2 = self.client.post(reverse('allocate'), post_data)
        user_id_2 = response2.cookies['tax_allocator_user_id'].value
        
        self.assertEqual(user_id_1, user_id_2)
        
        # Both submissions should have same user_id
        submissions = AllocationSubmission.objects.all()
        self.assertEqual(submissions[0].user_id, submissions[1].user_id)


class ResultsViewTest(TestCase):
    """Test results_view"""

    def setUp(self):
        self.client = Client()
        self.category = BudgetCategory.objects.create(name="Healthcare")
        self.session_key = str(uuid.uuid4())

    def test_results_view_with_valid_session(self):
        """Test results view with valid session key"""
        UserAllocation.objects.create(
            session_key=self.session_key,
            category=self.category,
            percentage=Decimal('100')
        )
        
        response = self.client.get(reverse('results', args=[self.session_key]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'allocator/results.html')
        self.assertIn('allocations', response.context)
        self.assertIn('chart_data', response.context)

    def test_results_view_with_invalid_session(self):
        """Test results view with invalid session key"""
        response = self.client.get(reverse('results', args=['invalid-key']))
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertEqual(response.url, reverse('allocate'))


class AggregateViewTest(TestCase):
    """Test aggregate_view with 3-tier caching"""

    def setUp(self):
        self.client = Client()
        cache.clear()  # Clear cache before each test
        
        # Create categories
        self.healthcare = BudgetCategory.objects.create(name="Healthcare", display_order=1)
        self.education = BudgetCategory.objects.create(name="Education", display_order=2)

    def tearDown(self):
        cache.clear()

    def test_aggregate_view_tier3_live_calculation(self):
        """Test Tier 3: Live calculation when no cache or aggregates"""
        # Create some allocations
        session_key = str(uuid.uuid4())
        UserAllocation.objects.create(session_key=session_key, category=self.healthcare, percentage=30)
        UserAllocation.objects.create(session_key=session_key, category=self.education, percentage=70)
        
        response = self.client.get(reverse('aggregate'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'allocator/aggregate.html')
        self.assertIn('aggregate_data', response.context)

    def test_aggregate_view_tier2_summary_table(self):
        """Test Tier 2: Pre-calculated summary table"""
        # Create aggregates with calculated averages
        agg1 = CategoryAggregate.objects.create(
            category=self.healthcare,
            total_percentage=Decimal('300'),
            submission_count=10
        )
        agg1.update_average()
        agg1.save()
        
        agg2 = CategoryAggregate.objects.create(
            category=self.education,
            total_percentage=Decimal('700'),
            submission_count=10
        )
        agg2.update_average()
        agg2.save()
        
        response = self.client.get(reverse('aggregate'))
        self.assertEqual(response.status_code, 200)
        
        aggregate_data = response.context['aggregate_data']
        self.assertEqual(len(aggregate_data), 2)
        self.assertEqual(aggregate_data[0]['avg_percentage'], 30.0)
        self.assertEqual(aggregate_data[1]['avg_percentage'], 70.0)

    def test_aggregate_view_tier1_redis_cache(self):
        """Test Tier 1: Redis cache (fastest)"""
        # Manually set cache
        cached_data = [
            {'category': 'Healthcare', 'avg_percentage': 25.0, 'color': '#ff0000'},
            {'category': 'Education', 'avg_percentage': 75.0, 'color': '#00ff00'},
        ]
        cache.set('aggregate_allocations_v2', cached_data)
        cache.set('aggregate_total_submissions', 100)
        
        response = self.client.get(reverse('aggregate'))
        self.assertEqual(response.status_code, 200)
        
        aggregate_data = response.context['aggregate_data']
        self.assertEqual(aggregate_data, cached_data)
        self.assertEqual(response.context['total_submissions'], 100)


class HistoryViewTest(TestCase):
    """Test history_view"""

    def setUp(self):
        self.client = Client()
        self.user_id = str(uuid.uuid4())

    def test_history_view_with_submissions(self):
        """Test history view shows user's submissions"""
        # Create submissions
        for i in range(3):
            AllocationSubmission.objects.create(
                session_key=str(uuid.uuid4()),
                user_id=self.user_id
            )
        
        # Set cookie
        self.client.cookies['tax_allocator_user_id'] = self.user_id
        
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'allocator/history.html')
        self.assertEqual(len(response.context['submission_data']), 3)

    def test_history_view_without_cookie(self):
        """Test history view without user_id cookie redirects"""
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 302)  # Redirects to allocate
        self.assertEqual(response.url, reverse('allocate'))


class IntegrationTest(TestCase):
    """Integration tests for complete user flow"""

    def setUp(self):
        self.client = Client()
        # Simulate user accepting cookies
        self.client.cookies['cookie_consent'] = 'accepted'
        # Create 10 categories
        for i in range(10):
            BudgetCategory.objects.create(name=f"Category {i}", display_order=i)

    def test_complete_submission_flow(self):
        """Test complete flow: submit → results → aggregate"""
        categories = BudgetCategory.objects.all()
        post_data = {f'category_{cat.id}': '10' for cat in categories}
        
        # 1. Submit allocation
        response = self.client.post(reverse('allocate'), post_data)
        self.assertEqual(response.status_code, 302)
        
        # Extract session_key from redirect URL
        session_key = response.url.split('/')[-2]
        
        # 2. View results
        response = self.client.get(reverse('results', args=[session_key]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['allocations']), 10)
        
        # 3. View aggregate
        response = self.client.get(reverse('aggregate'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['aggregate_data']), 10)

    def test_multiple_submissions_same_user(self):
        """Test multiple submissions from same user"""
        categories = BudgetCategory.objects.all()
        post_data = {f'category_{cat.id}': '10' for cat in categories}
        
        # Submit 3 times
        for _ in range(3):
            self.client.post(reverse('allocate'), post_data)
        
        # Check all submissions have same user_id
        submissions = AllocationSubmission.objects.all()
        user_ids = set(s.user_id for s in submissions)
        self.assertEqual(len(user_ids), 1)  # All same user
        
        # Check total allocations
        self.assertEqual(UserAllocation.objects.count(), 30)  # 3 submissions × 10 categories
