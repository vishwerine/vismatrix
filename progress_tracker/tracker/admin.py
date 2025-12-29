from django.contrib import admin
from .models import Category, Task, DailyLog, DailySummary, Plan, PlanNode, GoogleCalendarIntegration, ICloudCalendarIntegration, DaySchedule

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


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'is_active', 'created_at', 'updated_at']
    list_filter = ['user', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    date_hierarchy = 'created_at'


@admin.register(PlanNode)
class PlanNodeAdmin(admin.ModelAdmin):
    list_display = ['plan', 'task', 'order', 'can_start']
    list_filter = ['plan', 'plan__user']
    search_fields = ['task__title', 'plan__title']
    filter_horizontal = ['dependencies']

from .models import Conversation, ConversationMember, Message

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user1", "user2", "updated_at")
    search_fields = ("user1__username", "user2__username")

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "created_at")
    search_fields = ("sender__username", "body")

@admin.register(ConversationMember)
class ConversationMemberAdmin(admin.ModelAdmin):
    list_display = ("conversation", "user", "last_read_at", "last_read_message")


@admin.register(GoogleCalendarIntegration)
class GoogleCalendarIntegrationAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_active', 'auto_sync', 'last_sync_at']
    list_filter = ['is_active', 'auto_sync']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'last_sync_at']


@admin.register(ICloudCalendarIntegration)
class ICloudCalendarIntegrationAdmin(admin.ModelAdmin):
    list_display = ['user', 'apple_id', 'is_active', 'auto_sync', 'last_sync_at']
    list_filter = ['is_active', 'auto_sync']
    search_fields = ['user__username', 'user__email', 'apple_id']
    readonly_fields = ['created_at', 'updated_at', 'last_sync_at']


@admin.register(DaySchedule)
class DayScheduleAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'title', 'created_at', 'updated_at']
    list_filter = ['user', 'date']
    search_fields = ['user__username', 'title']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-date']