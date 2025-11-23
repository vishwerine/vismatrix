from django.contrib import admin
from .models import Category, Task, DailyLog, DailySummary

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'is_global', 'user', 'created_at']
    list_filter = ['is_global', 'user']
    search_fields = ['name']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Non-superusers only see their own categories
        return qs.filter(user=request.user)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'status', 'priority', 'created_at']
    list_filter = ['user', 'status', 'priority']
    search_fields = ['title', 'description']

@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = ['activity', 'user', 'date', 'duration']
    list_filter = ['user', 'date']

@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'total_tasks_completed', 'total_time_spent']
    list_filter = ['user', 'date']
