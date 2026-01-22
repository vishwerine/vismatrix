from django import forms
from django.db import models
from django.contrib.auth.models import User
from .models import Task, DailyLog, Category, DailySummary, Plan, PlanNode, Habit, BlogPost

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'category', 'priority', 'estimated_duration', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'estimated_duration': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '1440'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        
        # Set defaults for new tasks only (not when editing)
        if 'instance' not in kwargs or not kwargs['instance'].pk:
            initial = kwargs.get('initial', {})
            if 'estimated_duration' not in initial:
                from django.utils import timezone
                initial['estimated_duration'] = 60  # 60 minutes default
                initial['due_date'] = timezone.localdate()  # Today
                kwargs['initial'] = initial
        
        super(TaskForm, self).__init__(*args, **kwargs)
        if user:
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(is_global=True) | Q(user=user)
            )
            self.fields['category'].label_from_instance = self.label_from_instance
            # Make category optional - will auto-classify if not selected
            self.fields['category'].required = False
            self.fields['category'].empty_label = "🤖 Auto-detect (recommended)"
    
    def label_from_instance(self, obj):
        if obj.is_global:
            return f"🌐 {obj.name}"
        return obj.name
    
    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Title cannot be empty.")
        if len(title) < 3:
            raise forms.ValidationError("Title must be at least 3 characters long.")
        return title
    
    def clean_estimated_duration(self):
        duration = self.cleaned_data.get('estimated_duration')
        if duration is not None:
            if duration < 1:
                raise forms.ValidationError("Duration must be at least 1 minute.")
            if duration > 1440:  # 24 hours
                raise forms.ValidationError("Duration cannot exceed 24 hours (1440 minutes).")
        return duration
    
    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date:
            from django.utils import timezone
            # Allow today and future dates only
            if due_date < timezone.now().date():
                raise forms.ValidationError("Due date cannot be in the past.")
        return due_date

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
        
        # ✅ Default duration to 10 minutes if not already set
        if 'duration' not in initial:
            initial['duration'] = 10
            kwargs['initial'] = initial
        
        super().__init__(*args, **kwargs)
    
        if user:
            # Filter categories first
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(is_global=True) | Q(user=user)
            )
            self.fields['category'].label_from_instance = self.label_from_instance
            
            # Filter tasks to user's tasks AND global tasks from system_global user
            try:
                from django.contrib.auth.models import User
                system_user = User.objects.get(username='system_global')
                self.fields['task'].queryset = Task.objects.filter(
                    Q(user=user) | Q(user=system_user, is_global=True)
                )
            except User.DoesNotExist:
                self.fields['task'].queryset = Task.objects.filter(user=user)
            self.fields['task'].required = True  # Make task selection required

    def label_from_instance(self, obj):
        if obj.is_global:
            return f"🌐 {obj.name}"
        return obj.name
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Auto-set category from task if task is selected
        if instance.task and instance.task.category:
            instance.category = instance.task.category
        
        if commit:
            instance.save()
        return instance


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


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ['title', 'description', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter plan title...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Describe your plan...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
        }
        labels = {
            'is_active': 'Active Plan',
        }
        help_texts = {
            'is_active': 'Uncheck to archive this plan (it will be hidden from dashboard and analytics)',
        }


class PlanNodeForm(forms.ModelForm):
    class Meta:
        model = PlanNode
        fields = ['task', 'dependencies', 'order']
        widgets = {
            'task': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'dependencies': forms.SelectMultiple(attrs={
                'class': 'select select-bordered w-full',
                'size': '5'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '0'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        plan = kwargs.pop('plan', None)
        super(PlanNodeForm, self).__init__(*args, **kwargs)
        
        if user:
            # Show user's tasks AND global tasks from system_global user
            from django.db.models import Q
            try:
                from django.contrib.auth.models import User
                system_user = User.objects.get(username='system_global')
                self.fields['task'].queryset = Task.objects.filter(
                    Q(user=user) | Q(user=system_user, is_global=True)
                )
            except User.DoesNotExist:
                self.fields['task'].queryset = Task.objects.filter(user=user)
        
        if plan:
            # Only show nodes from the same plan as dependencies
            self.fields['dependencies'].queryset = PlanNode.objects.filter(plan=plan)
            # Exclude self from dependencies if editing
            if self.instance.pk:
                self.fields['dependencies'].queryset = self.fields['dependencies'].queryset.exclude(pk=self.instance.pk)


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile information (display name)"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter your last name'
            }),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
        }
        help_texts = {
            'first_name': 'This will be displayed as your name across the site',
            'last_name': 'Optional',
        }

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if first_name and len(first_name) > 30:
            raise forms.ValidationError("First name cannot exceed 30 characters.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if last_name and len(last_name) > 150:
            raise forms.ValidationError("Last name cannot exceed 150 characters.")
        return last_name


class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = ['title', 'description', 'category', 'frequency', 'priority', 'start_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Morning Exercise'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional: Add details about this habit...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        
        # Set defaults for new habits only
        if 'instance' not in kwargs or not kwargs['instance'].pk:
            initial = kwargs.get('initial', {})
            if 'start_date' not in initial:
                from django.utils import timezone
                initial['start_date'] = timezone.localdate()  # Today
                kwargs['initial'] = initial
        
        super(HabitForm, self).__init__(*args, **kwargs)
        
        if user:
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(is_global=True) | Q(user=user)
            )
            self.fields['category'].label_from_instance = self.label_from_instance
            self.fields['category'].required = False
            self.fields['category'].empty_label = "🤖 Auto-detect (recommended)"
    
    def label_from_instance(self, obj):
        if obj.is_global:
            return f"🌐 {obj.name}"
        return obj.name
    
    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Title cannot be empty.")
        if len(title) < 3:
            raise forms.ValidationError("Title must be at least 3 characters long.")
        return title
    
    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if start_date:
            from django.utils import timezone
            # Allow past and future dates (habits can be started anytime)
            pass
        return start_date


class BlogPostForm(forms.ModelForm):
    """Form for creating and editing user blog posts"""
    class Meta:
        model = BlogPost
        fields = ['title', 'excerpt', 'content', 'category', 'status', 'featured_image', 'meta_description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter a catchy title for your post...',
                'maxlength': '200'
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Brief summary of your post (optional)...',
                'maxlength': '300'
            }),
            'content': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 20,
                'placeholder': 'Write your article content here... (Markdown supported)'
            }),
            'category': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'status': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'featured_image': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://example.com/image.jpg (optional)'
            }),
            'meta_description': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'SEO description (optional)',
                'maxlength': '160'
            }),
        }
        help_texts = {
            'title': 'Make it catchy and descriptive',
            'excerpt': 'Optional: Brief summary for the blog list page',
            'content': 'Use Markdown formatting for rich text',
            'category': 'Choose the most relevant category',
            'status': 'Draft = only you can see it, Published = public',
        }
    
    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError("Title is required.")
        if len(title) < 10:
            raise forms.ValidationError("Title should be at least 10 characters long.")
        return title
    
    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if not content:
            raise forms.ValidationError("Content is required.")
        return content
