from django import forms
from django.db import models
from django.contrib.auth.models import User
from .models import Task, DailyLog, Category, DailySummary, Plan, PlanNode, Habit, BlogPost, Project, ProjectTask, ProjectPlan, ProjectResource, ProjectProgress

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


# ===== PROJECT FORMS =====

class ProjectForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Enter tags separated by commas (e.g., web, design, urgent)',
        }),
        label="Tags"
    )

    class Meta:
        model = Project
        fields = [
            'title', 'description', 'status', 'priority', 'start_date', 'due_date',
            'estimated_hours', 'budget', 'category', 'is_public'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter project title',
                'maxlength': '255'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'Describe your project goals and scope',
            }),
            'status': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'priority': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
            'estimated_hours': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '1',
                'placeholder': 'Estimated total hours'
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Budget amount (optional)'
            }),
            'category': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
        }
        help_texts = {
            'title': 'Give your project a clear, descriptive name',
            'description': 'Explain what this project is about and what you hope to achieve',
            'status': 'Current state of the project',
            'priority': 'How important is this project?',
            'start_date': 'When do you plan to start working on this project?',
            'due_date': 'When should this project be completed?',
            'estimated_hours': 'Rough estimate of total hours needed',
            'budget': 'Optional: Budget allocated for this project',
            'category': 'Choose a category to organize your projects',
            'is_public': 'Allow others to view this project (read-only)',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(is_global=True) | Q(user=user)
            )
            self.fields['category'].required = False
            self.fields['category'].empty_label = "🤖 Auto-detect (recommended)"

        # Set default dates for new projects
        if not self.instance.pk:
            from django.utils import timezone
            today = timezone.localdate()
            self.initial['start_date'] = today
            self.initial['due_date'] = today + timezone.timedelta(days=30)  # 30 days default

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        due_date = cleaned_data.get('due_date')

        if start_date and due_date and due_date < start_date:
            raise forms.ValidationError("Due date cannot be before start date.")

        return cleaned_data

    def clean_tags_input(self):
        tags_input = self.cleaned_data.get('tags_input', '')
        if tags_input:
            # Split by comma, strip whitespace, remove empty tags
            tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            return tags
        return []

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.tags = self.cleaned_data.get('tags_input', [])
        if commit:
            instance.save()
        return instance


class ProjectTaskForm(forms.ModelForm):
    class Meta:
        model = ProjectTask
        fields = ['task', 'weight', 'notes', 'assigned_to', 'order']
        widgets = {
            'task': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'weight': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '1',
                'max': '10',
                'value': '1'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Project-specific notes for this task'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '0',
                'value': '0'
            }),
        }
        help_texts = {
            'task': 'Select an existing task to add to this project',
            'weight': 'Relative importance for progress calculation (1-10)',
            'notes': 'Any project-specific context or requirements',
            'assigned_to': 'Assign this task to a team member',
            'order': 'Order within the project (lower numbers appear first)',
        }

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # Show user's tasks that aren't already in this project
            existing_task_ids = []
            if project:
                existing_task_ids = list(project.project_tasks.values_list('task_id', flat=True))

            self.fields['task'].queryset = Task.objects.filter(
                user=user
            ).exclude(id__in=existing_task_ids)

            # Collaborators for assignment
            collaborators = [user]
            if project:
                collaborators.extend(list(project.collaborators.all()))
            self.fields['assigned_to'].queryset = User.objects.filter(id__in=[u.id for u in collaborators])


class ProjectPlanForm(forms.ModelForm):
    class Meta:
        model = ProjectPlan
        fields = ['plan', 'weight', 'notes', 'order']
        widgets = {
            'plan': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'weight': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '1',
                'max': '10',
                'value': '1'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Project-specific notes for this plan'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '0',
                'value': '0'
            }),
        }
        help_texts = {
            'plan': 'Select an existing plan to add to this project',
            'weight': 'Relative importance for progress calculation (1-10)',
            'notes': 'Any project-specific context or requirements',
            'order': 'Order within the project (lower numbers appear first)',
        }

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # Show user's plans that aren't already in this project
            existing_plan_ids = []
            if project:
                existing_plan_ids = list(project.project_plans.values_list('plan_id', flat=True))

            self.fields['plan'].queryset = Plan.objects.filter(
                user=user
            ).exclude(id__in=existing_plan_ids)


class ProjectResourceForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Enter tags separated by commas',
        }),
        label="Tags"
    )

    class Meta:
        model = ProjectResource
        fields = ['title', 'resource_type', 'url', 'content', 'is_important']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Resource title or name',
                'maxlength': '255'
            }),
            'resource_type': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'url': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://example.com (for links)'
            }),
            'content': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'Notes, content, or description'
            }),
            'is_important': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
        }
        help_texts = {
            'title': 'Give this resource a descriptive name',
            'resource_type': 'What type of resource is this?',
            'url': 'Web link (required for link type)',
            'content': 'Additional notes or content',
            'is_important': 'Mark as important to highlight this resource',
        }

    def clean_tags_input(self):
        tags_input = self.cleaned_data.get('tags_input', '')
        if tags_input:
            tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            return tags
        return []

    def clean(self):
        cleaned_data = super().clean()
        resource_type = cleaned_data.get('resource_type')
        url = cleaned_data.get('url')

        if resource_type == 'link' and not url:
            raise forms.ValidationError("URL is required for link resources.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.tags = self.cleaned_data.get('tags_input', [])
        if commit:
            instance.save()
        return instance


class ProjectProgressForm(forms.ModelForm):
    class Meta:
        model = ProjectProgress
        fields = ['title', 'progress_type', 'description', 'progress_percentage', 'hours_spent', 'new_status']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Progress update title',
                'maxlength': '255'
            }),
            'progress_type': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'Describe what was accomplished or what changed'
            }),
            'progress_percentage': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '0',
                'max': '100',
                'placeholder': 'Current progress (0-100%)'
            }),
            'hours_spent': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '0',
                'placeholder': 'Hours spent on this update'
            }),
            'new_status': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
        }
        help_texts = {
            'title': 'Brief title for this progress update',
            'progress_type': 'Type of progress update',
            'description': 'Detailed description of what happened',
            'progress_percentage': 'Current overall project progress',
            'hours_spent': 'Time spent on this specific update',
            'new_status': 'Update project status (optional)',
        }

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

        # Set current status as old_status for tracking
        if project and not self.instance.pk:
            self.instance.old_status = project.status
            self.initial['progress_percentage'] = project.progress_percentage
