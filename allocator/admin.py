from django.contrib import admin
from .models import BudgetCategory, UserAllocation, AllocationSubmission


@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_order', 'color', 'created_at']
    list_editable = ['display_order', 'color']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']


@admin.register(UserAllocation)
class UserAllocationAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'category', 'percentage', 'created_at', 'ip_address']
    list_filter = ['category', 'created_at']
    search_fields = ['session_key', 'ip_address']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']


@admin.register(AllocationSubmission)
class AllocationSubmissionAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'submitted_at', 'ip_address']
    list_filter = ['submitted_at']
    search_fields = ['session_key', 'ip_address']
    date_hierarchy = 'submitted_at'
    readonly_fields = ['submitted_at']
