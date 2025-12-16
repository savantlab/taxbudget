from django import forms
from decimal import Decimal
from .models import BudgetCategory


class TaxAllocationForm(forms.Form):
    """Dynamic form for allocating tax percentages across budget categories"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically create fields for each budget category
        categories = BudgetCategory.objects.all().order_by('display_order', 'name')
        
        for category in categories:
            field_name = f'category_{category.id}'
            self.fields[field_name] = forms.DecimalField(
                label=category.name,
                max_digits=5,
                decimal_places=2,
                min_value=Decimal('0.00'),
                max_value=Decimal('100.00'),
                initial=Decimal('0.00'),
                widget=forms.NumberInput(attrs={
                    'class': 'form-control allocation-input',
                    'step': '0.01',
                    'min': '0',
                    'max': '100',
                    'data-category-id': category.id,
                    'data-category-name': category.name,
                    'data-category-color': category.color,
                })
            )
    
    def clean(self):
        """Validate that all percentages sum to exactly 100%"""
        cleaned_data = super().clean()
        
        # Sum all category allocations
        total = Decimal('0.00')
        for field_name, value in cleaned_data.items():
            if field_name.startswith('category_') and value is not None:
                total += value
        
        # Check if total equals 100%
        if total != Decimal('100.00'):
            raise forms.ValidationError(
                f'Total allocation must equal 100%. Current total: {total}%'
            )
        
        return cleaned_data
    
    def get_allocations(self):
        """Return a dict mapping category IDs to percentages"""
        allocations = {}
        for field_name, value in self.cleaned_data.items():
            if field_name.startswith('category_'):
                category_id = int(field_name.replace('category_', ''))
                allocations[category_id] = value
        return allocations
