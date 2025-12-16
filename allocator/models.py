from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class BudgetCategory(models.Model):
    """Budget categories for tax allocation"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')  # Hex color for charts
    display_order = models.IntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Budget Categories"
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['display_order', 'name']),
        ]
    
    def __str__(self):
        return self.name


class UserAllocation(models.Model):
    """Individual user's tax allocation submission"""
    session_key = models.CharField(max_length=255, db_index=True)  # Anonymous user tracking
    user_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)  # Cookie-based user tracking
    category = models.ForeignKey(BudgetCategory, on_delete=models.CASCADE, related_name='allocations')
    percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_key', 'created_at']),
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['category', 'created_at']),
            models.Index(fields=['-created_at']),
        ]
        # Ensure one allocation per category per submission
        unique_together = [['session_key', 'category', 'created_at']]
    
    def __str__(self):
        return f"{self.session_key[:8]} - {self.category.name}: {self.percentage}%"


class AllocationSubmission(models.Model):
    """Tracks complete submissions for aggregate statistics"""
    session_key = models.CharField(max_length=255, db_index=True)
    user_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)  # Cookie-based user tracking
    submitted_at = models.DateTimeField(default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['user_id', '-submitted_at']),
            models.Index(fields=['-submitted_at']),
        ]
    
    def __str__(self):
        return f"Submission {self.session_key[:8]} at {self.submitted_at}"


class CategoryAggregate(models.Model):
    """Pre-calculated aggregate statistics for each category (for millions of users)"""
    category = models.OneToOneField(BudgetCategory, on_delete=models.CASCADE, related_name='aggregate', primary_key=True)
    total_percentage = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Sum of all percentages for this category"
    )
    submission_count = models.BigIntegerField(
        default=0,
        help_text="Number of submissions for this category"
    )
    avg_percentage = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Calculated average: total_percentage / submission_count"
    )
    last_updated = models.DateTimeField(auto_now=True, db_index=True)
    
    class Meta:
        verbose_name = "Category Aggregate"
        verbose_name_plural = "Category Aggregates"
        ordering = ['category__display_order']
    
    def __str__(self):
        return f"{self.category.name}: {self.avg_percentage}% (n={self.submission_count})"
    
    def update_average(self):
        """Recalculate average from total and count"""
        if self.submission_count > 0:
            self.avg_percentage = self.total_percentage / self.submission_count
        else:
            self.avg_percentage = 0
    
    def add_submission(self, percentage):
        """Incrementally update aggregate with new submission"""
        from decimal import Decimal
        self.total_percentage += Decimal(str(percentage))
        self.submission_count += 1
        self.update_average()
        self.save()
