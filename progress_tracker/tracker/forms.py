from django import forms
from django.db import models
from .models import Task, DailyLog, Category, DailySummary

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'category', 'priority', 'estimated_duration', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'estimated_duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(TaskForm, self).__init__(*args, **kwargs)
        if user:
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(is_global=True) | Q(user=user)
            )
            self.fields['category'].label_from_instance = self.label_from_instance
    
    def label_from_instance(self, obj):
        if obj.is_global:
            return f"🌐 {obj.name}"
        return obj.name

# forms.py - Complete working form

from django.utils import timezone

from django.db.models import Q

class DailyLogForm(forms.ModelForm):
    class Meta:
        model = DailyLog
        fields = ['date', 'activity', 'description', 'category', 'task', 'duration']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 rounded-2xl border-2 border-slate-200 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100/50',
                'max': timezone.localdate().strftime('%Y-%m-%d'),  # ✅ FIXED
            }),
            # ... rest of widgets
        }
    
    # forms.py - Default to today in form
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        initial = kwargs.get('initial', {})
        
        # ✅ Default to TODAY in form (not model) - only if not already set
        if 'date' not in initial:
            initial['date'] = timezone.localdate()
            kwargs['initial'] = initial
        
        super().__init__(*args, **kwargs)
    
        if user:
            # Filter categories first
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(is_global=True) | Q(user=user)
            )
            self.fields['category'].label_from_instance = self.label_from_instance
            
            # Filter tasks to user's tasks only - do this before setting initial
            self.fields['task'].queryset = Task.objects.filter(user=user)
            self.fields['task'].required = True  # Make task selection required

    def label_from_instance(self, obj):
        if obj.is_global:
            return f"🌐 {obj.name}"
        return obj.name


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }
        help_texts = {
            'name': 'Create your own custom category (separate from global categories)',
        }

class DailySummaryForm(forms.ModelForm):
    class Meta:
        model = DailySummary
        fields = ['date', 'notes', 'productivity_rating']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'productivity_rating': forms.Select(attrs={'class': 'form-select'}),
        }
