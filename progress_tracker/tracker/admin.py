from django.contrib import admin
from .models import Category, Task, DailyLog, DailySummary, Plan, PlanNode, GoogleCalendarIntegration, ICloudCalendarIntegration, DaySchedule, MentorProfile, MentorshipRequest, Notification, UserPoints, PointsActivity, UserNotification, TimerSession, Friendship, LandingPageVisitor, Habit, HabitCompletion

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


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ['user', 'friend', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'friend__username']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


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


@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'experience_years', 'max_mentees', 'is_active', 'created_at']
    list_filter = ['is_active', 'experience_years']
    search_fields = ['user__username', 'bio', 'specializations']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(MentorshipRequest)
class MentorshipRequestAdmin(admin.ModelAdmin):
    list_display = ['mentee', 'mentor_profile', 'category', 'status', 'created_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['mentee__username', 'mentor_profile__user__username', 'message']
    readonly_fields = ['created_at', 'updated_at', 'responded_at']
    ordering = ['-created_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']
    ordering = ['-created_at']


@admin.register(UserPoints)
class UserPointsAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_points', 'current_streak', 'longest_streak', 'last_visit_date']
    list_filter = ['last_visit_date']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-total_points']


@admin.register(PointsActivity)
class PointsActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'points', 'reason', 'created_at']
    list_filter = ['created_at', 'reason']
    search_fields = ['user__username', 'reason']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'message_preview', 'is_read', 'created_at']
    list_filter = ['level', 'is_read', 'created_at']
    search_fields = ['user__username', 'message']
    readonly_fields = ['created_at', 'read_at']
    ordering = ['-created_at']
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


@admin.register(TimerSession)
class TimerSessionAdmin(admin.ModelAdmin):
    list_display = ['share_code', 'task', 'host', 'mode', 'duration', 'is_active', 'participant_count', 'created_at']
    list_filter = ['mode', 'is_active', 'is_public', 'created_at']
    search_fields = ['share_code', 'task__title', 'host__username']
    readonly_fields = ['share_code', 'created_at', 'updated_at']
    filter_horizontal = ['participants']
    ordering = ['-created_at']
    
    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Participants'


@admin.register(LandingPageVisitor)
class LandingPageVisitorAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'device', 'browser', 'os', 'referrer_preview', 'utm_source', 'converted_to_user', 'visit_count', 'first_visit', 'last_visit']
    list_filter = ['converted_to_user', 'device', 'browser', 'os', 'utm_source', 'utm_medium', 'utm_campaign', 'first_visit']
    search_fields = ['ip_address', 'session_key', 'referrer', 'user_agent', 'country', 'city']
    readonly_fields = ['first_visit', 'last_visit']
    ordering = ['-last_visit']
    date_hierarchy = 'first_visit'
    
    def referrer_preview(self, obj):
        if obj.referrer:
            return obj.referrer[:50] + '...' if len(obj.referrer) > 50 else obj.referrer
        return '-'
    referrer_preview.short_description = 'Referrer'


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'frequency', 'priority', 'is_active', 'start_date', 'created_at']
    list_filter = ['frequency', 'priority', 'is_active', 'user', 'created_at']
    search_fields = ['title', 'description', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Non-superusers only see their own habits
        return qs.filter(user=request.user)


@admin.register(HabitCompletion)
class HabitCompletionAdmin(admin.ModelAdmin):
    list_display = ['habit', 'user', 'completion_date', 'created_at']
    list_filter = ['completion_date', 'user', 'habit__frequency']
    search_fields = ['habit__title', 'user__username', 'notes']
    readonly_fields = ['created_at']
    ordering = ['-completion_date', '-created_at']
    date_hierarchy = 'completion_date'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Non-superusers only see their own completions
        return qs.filter(user=request.user)
