from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Category(models.Model):
    """Categories can be global (shared) or user-specific (custom)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='categories')
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#3498db')
    is_global = models.BooleanField(default=False, help_text="Global categories are available to all users")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['-is_global', 'name']  # Global categories first, then alphabetical
    
    def __str__(self):
        if self.is_global:
            return f"🌐 {self.name}"
        return f"{self.user.username} - {self.name}" if self.user else self.name


class Task(models.Model):
    """Study tasks or activities to track"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks', db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Global task flags
    is_global = models.BooleanField(default=False, help_text="Global tasks are shared across all users")
    is_editable = models.BooleanField(default=True, help_text="Whether the task can be edited by users")
    is_deletable = models.BooleanField(default=True, help_text="Whether the task can be deleted by users")
    
    # Time tracking
    estimated_duration = models.IntegerField(help_text="Estimated time in minutes", null=True, blank=True)
    actual_duration = models.IntegerField(help_text="Actual time spent in minutes", null=True, blank=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', '-created_at']),
            models.Index(fields=['user', 'due_date']),
            models.Index(fields=['status', 'completed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_completed(self):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()

# models.py - FIXED
class DailyLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_logs', db_index=True)
    date = models.DateField(db_index=True)  # ✅ NO DEFAULT HERE
    activity = models.TextField(max_length=500)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='logs')  # Link to task
    duration = models.PositiveIntegerField(help_text="Duration in minutes", default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['user', 'date', 'category']),
            models.Index(fields=['task', '-date']),
        ]


class DailySummary(models.Model):
    """Summary of each day's progress"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_summaries')
    date = models.DateField(default=timezone.now)
    total_tasks_completed = models.IntegerField(default=0)
    total_time_spent = models.IntegerField(default=0)  # in minutes
    notes = models.TextField(blank=True)
    productivity_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Daily Summaries"
        ordering = ['-date']
        unique_together = ['user', 'date']
    
    def __str__(self):
        return f"{self.user.username} - Summary for {self.date}"



class FriendRequest(models.Model):
    """Friend request between users"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    from_user = models.ForeignKey(User, related_name='sent_friend_requests', on_delete=models.CASCADE, db_index=True)
    to_user = models.ForeignKey(User, related_name='received_friend_requests', on_delete=models.CASCADE, db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['to_user', 'status', '-created_at']),
            models.Index(fields=['from_user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"
    
    def accept(self):
        """Accept friend request and create friendship"""
        self.status = 'accepted'
        self.save()
        # Create bidirectional friendship
        Friendship.objects.get_or_create(user=self.from_user, friend=self.to_user)
        Friendship.objects.get_or_create(user=self.to_user, friend=self.from_user)
    
    def reject(self):
        """Reject friend request"""
        self.status = 'rejected'
        self.save()

class Friendship(models.Model):
    """Represents a friendship between two users"""
    user = models.ForeignKey(User, related_name='friendships', on_delete=models.CASCADE)
    friend = models.ForeignKey(User, related_name='friends_of', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'friend')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} is friends with {self.friend.username}"


class ActivityReaction(models.Model):
    """Reactions (stars) to friends' activities"""
    REACTION_TYPES = [
        ('star', 'Star'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_reactions')
    # Can react to either a task completion, a daily log, or a habit completion
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='reactions')
    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, null=True, blank=True, related_name='reactions')
    habit_completion = models.ForeignKey('HabitCompletion', on_delete=models.CASCADE, null=True, blank=True, related_name='reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES, default='star')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'task', 'daily_log', 'habit_completion')  # One reaction per user per activity
        ordering = ['-created_at']
    
    def __str__(self):
        if self.task:
            activity_type = "task"
            activity_id = self.task.id
        elif self.daily_log:
            activity_type = "log"
            activity_id = self.daily_log.id
        else:
            activity_type = "habit"
            activity_id = self.habit_completion.id if self.habit_completion else None
        return f"{self.user.username} starred {activity_type} {activity_id}"

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q

class Conversation(models.Model):
    """
    1-to-1 conversation between two users.
    Enforced unique pair via unique_together on (user1, user2) with ordering.
    """
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations_as_user1")
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations_as_user2")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user1", "user2"], name="unique_conversation_pair"),
            models.CheckConstraint(condition=~Q(user1=models.F("user2")), name="conversation_users_must_differ"),
        ]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Chat: {self.user1.username} ↔ {self.user2.username}"

    @staticmethod
    def normalize_pair(a: User, b: User) -> tuple[User, User]:
        """Store pairs in deterministic order so uniqueness works reliably."""
        return (a, b) if a.id < b.id else (b, a)

    @classmethod
    def get_or_create_between(cls, a: User, b: User):
        u1, u2 = cls.normalize_pair(a, b)
        return cls.objects.get_or_create(user1=u1, user2=u2)

    def other_user(self, me: User) -> User:
        return self.user2 if self.user1_id == me.id else self.user1

    def last_message(self):
        return self.messages.order_by("-created_at").first()


class ConversationMember(models.Model):
    """
    Per-user state for a conversation (unread counts, last read pointer).
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversation_memberships")

    last_read_at = models.DateTimeField(null=True, blank=True)
    last_read_message = models.ForeignKey(
        "Message", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        unique_together = ("conversation", "user")

    def __str__(self):
        return f"{self.user.username} in {self.conversation_id}"

    def unread_count(self) -> int:
        qs = self.conversation.messages.all()
        if self.last_read_message_id:
            qs = qs.filter(id__gt=self.last_read_message_id)
        elif self.last_read_at:
            qs = qs.filter(created_at__gt=self.last_read_at)
        return qs.exclude(sender=self.user).count()


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: allow soft-delete per side
    deleted_for_sender = models.BooleanField(default=False)
    deleted_for_recipient = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Msg {self.id} in conv {self.conversation_id} by {self.sender.username}"


class Plan(models.Model):
    """A plan is a directed acyclic graph of tasks"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plans')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False, help_text="Whether this plan can be shared publicly")
    share_token = models.CharField(max_length=64, blank=True, unique=True, null=True, help_text="Unique token for sharing")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def generate_share_token(self):
        """Generate a unique share token for this plan"""
        import secrets
        if not self.share_token:
            self.share_token = secrets.token_urlsafe(32)
            self.save()
        return self.share_token
    
    def get_share_url(self, request=None):
        """Get the full sharing URL for this plan"""
        if not self.share_token:
            return None
        from django.urls import reverse
        path = reverse('shared_plan', kwargs={'token': self.share_token})
        return f"https://vismatrix.space{path}"
    
    def get_root_nodes(self):
        """Get all nodes that have no dependencies (root nodes)"""
        return self.nodes.filter(dependencies__isnull=True)
    
    def validate_dag(self):
        """Validate that the plan forms a valid DAG (no cycles)"""
        from collections import defaultdict, deque
        
        # Build adjacency list
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        for node in self.nodes.all():
            if node.id not in in_degree:
                in_degree[node.id] = 0
            for dep in node.dependencies.all():
                graph[dep.id].append(node.id)
                in_degree[node.id] += 1
        
        # Topological sort using Kahn's algorithm
        queue = deque([node_id for node_id in in_degree if in_degree[node_id] == 0])
        sorted_count = 0
        
        while queue:
            node_id = queue.popleft()
            sorted_count += 1
            
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # If sorted_count doesn't equal total nodes, there's a cycle
        return sorted_count == len(in_degree)


class PlanNode(models.Model):
    """A node in a plan DAG, representing a task"""
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='nodes')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='plan_nodes')
    dependencies = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='dependents',
        blank=True,
        help_text="Tasks that must be completed before this one"
    )
    position_x = models.IntegerField(default=0, help_text="X position for visualization")
    position_y = models.IntegerField(default=0, help_text="Y position for visualization")
    order = models.IntegerField(default=0, help_text="Order in the plan")
    
    class Meta:
        ordering = ['order', 'id']
        unique_together = ['plan', 'task']
    
    def __str__(self):
        return f"{self.plan.title} - {self.task.title}"
    
    def can_start(self):
        """Check if all dependencies are completed"""
        return all(dep.task.status == 'completed' for dep in self.dependencies.all())
    
    def get_dependents(self):
        """Get all tasks that depend on this one"""
        return self.dependents.all()


class GoogleCalendarIntegration(models.Model):
    """Store Google Calendar OAuth tokens and sync preferences for each user"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='google_calendar')
    
    # OAuth tokens
    access_token = models.TextField(help_text="OAuth2 access token")
    refresh_token = models.TextField(help_text="OAuth2 refresh token")
    token_uri = models.CharField(max_length=255, default='https://oauth2.googleapis.com/token')
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    scopes = models.TextField(default='https://www.googleapis.com/auth/calendar.readonly', help_text="Space-separated scopes")
    
    # Sync settings
    is_active = models.BooleanField(default=True, help_text="Enable/disable sync")
    auto_sync = models.BooleanField(default=True, help_text="Automatically sync calendar events")
    sync_interval_hours = models.IntegerField(default=1, help_text="How often to sync (in hours)")
    
    # Sync state
    last_sync_at = models.DateTimeField(null=True, blank=True, help_text="Last successful sync")
    last_sync_token = models.TextField(blank=True, help_text="Sync token for incremental sync")
    sync_error = models.TextField(blank=True, help_text="Last sync error message")
    
    # Filtering preferences
    sync_calendars = models.TextField(blank=True, help_text="Comma-separated calendar IDs to sync (empty = all)")
    min_event_duration = models.IntegerField(default=15, help_text="Minimum event duration in minutes to sync")
    exclude_all_day_events = models.BooleanField(default=False, help_text="Skip all-day events")
    
    # Default category for synced events
    default_category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, help_text="Default category for calendar events")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Google Calendar Integration"
        verbose_name_plural = "Google Calendar Integrations"
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.user.username} - Google Calendar ({status})"
    
    def get_credentials_dict(self):
        """Convert stored data to credentials dictionary for Google API"""
        return {
            'token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_uri': self.token_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scopes': self.scopes.split()
        }
    
    def should_sync(self):
        """Check if it's time to sync based on interval"""
        if not self.is_active or not self.auto_sync:
            return False
        if not self.last_sync_at:
            return True
        
        from datetime import timedelta
        next_sync = self.last_sync_at + timedelta(hours=self.sync_interval_hours)
        return timezone.now() >= next_sync
    
    def mark_sync_success(self, sync_token=None):
        """Update last sync timestamp and token"""
        self.last_sync_at = timezone.now()
        if sync_token:
            self.last_sync_token = sync_token
        self.sync_error = ''
        self.save()
    
    def mark_sync_error(self, error_message):
        """Record sync error"""
        self.sync_error = error_message
        self.save()


class ICloudCalendarIntegration(models.Model):
    """Store iCloud Calendar credentials and sync preferences for each user"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='icloud_calendar')
    
    # iCloud credentials (uses app-specific password)
    apple_id = models.EmailField(help_text="Apple ID email address")
    app_specific_password = models.CharField(max_length=255, help_text="App-specific password generated from appleid.apple.com")
    
    # CalDAV server details
    caldav_url = models.CharField(max_length=500, default='https://caldav.icloud.com', help_text="CalDAV server URL")
    principal_url = models.CharField(max_length=500, blank=True, help_text="Principal URL for calendar access")
    
    # Sync settings
    is_active = models.BooleanField(default=True, help_text="Enable/disable sync")
    auto_sync = models.BooleanField(default=True, help_text="Automatically sync calendar events")
    sync_interval_hours = models.IntegerField(default=1, help_text="How often to sync (in hours)")
    sync_days_back = models.IntegerField(default=7, help_text="Number of days in the past to sync")
    sync_days_forward = models.IntegerField(default=0, help_text="Number of days in the future to sync")
    
    # Sync state
    last_sync_at = models.DateTimeField(null=True, blank=True, help_text="Last successful sync")
    sync_error = models.TextField(blank=True, help_text="Last sync error message")
    
    # Filtering preferences
    sync_calendars = models.TextField(blank=True, help_text="Comma-separated calendar names to sync (empty = all)")
    min_event_duration = models.IntegerField(default=15, help_text="Minimum event duration in minutes to sync")
    exclude_all_day_events = models.BooleanField(default=False, help_text="Skip all-day events")
    
    # Default category for synced events
    default_category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, help_text="Default category for calendar events")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "iCloud Calendar Integration"
        verbose_name_plural = "iCloud Calendar Integrations"
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.user.username} - iCloud Calendar ({status})"
    
    def should_sync(self):
        """Check if it's time to sync based on interval"""
        if not self.is_active or not self.auto_sync:
            return False
        if not self.last_sync_at:
            return True
        
        from datetime import timedelta
        next_sync = self.last_sync_at + timedelta(hours=self.sync_interval_hours)
        return timezone.now() >= next_sync
    
    def mark_sync_success(self):
        """Update last sync timestamp"""
        self.last_sync_at = timezone.now()
        self.sync_error = ''
        self.save()
    
    def mark_sync_error(self, error_message):
        """Record sync error"""
        self.sync_error = error_message
        self.save()


class DaySchedule(models.Model):
    """Store day planner schedules for users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='day_schedules', db_index=True)
    date = models.DateField(db_index=True)
    title = models.CharField(max_length=255, blank=True, default='')
    events_data = models.JSONField(default=list, help_text="List of event dictionaries with id, title, startMin, endMin, logged, planNames")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['user', 'date']]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', 'date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"


class MentorProfile(models.Model):
    """Profile for users who volunteer as mentors"""
    CATEGORY_CHOICES = [
        ('health', 'Health & Fitness'),
        ('work', 'Work & Career'),
        ('study', 'Study & Education'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mentor_profile')
    categories = models.JSONField(default=list, help_text="List of categories: health, work, study")
    bio = models.TextField(help_text="Tell mentees about your expertise and experience")
    experience_years = models.PositiveIntegerField(default=0, help_text="Years of experience in your field")
    specializations = models.TextField(blank=True, help_text="Specific areas of expertise")
    max_mentees = models.PositiveIntegerField(default=5, help_text="Maximum number of active mentees")
    is_active = models.BooleanField(default=True, help_text="Whether actively accepting new mentees")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - Mentor"
    
    def get_categories_display(self):
        """Return human-readable category names"""
        category_map = dict(self.CATEGORY_CHOICES)
        return [category_map.get(cat, cat) for cat in self.categories]
    
    def active_mentees_count(self):
        """Count current active mentees"""
        return self.mentorship_requests.filter(status='accepted').count()
    
    def can_accept_more_mentees(self):
        """Check if mentor can accept more mentees"""
        return self.is_active and self.active_mentees_count() < self.max_mentees


class MentorshipRequest(models.Model):
    """Mentorship applications from users to mentors"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    mentee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentorship_requests')
    mentor_profile = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name='mentorship_requests')
    category = models.CharField(max_length=20, choices=MentorProfile.CATEGORY_CHOICES)
    message = models.TextField(help_text="Why do you want this mentorship?")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Response from mentor
    response_message = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [['mentee', 'mentor_profile', 'category']]
    
    def __str__(self):
        return f"{self.mentee.username} -> {self.mentor_profile.user.username} ({self.category})"


class Notification(models.Model):
    """System notifications for users"""
    NOTIFICATION_TYPES = [
        ('friend_request', 'Friend Request'),
        ('friend_accepted', 'Friend Request Accepted'),
        ('mentorship_request', 'New Mentorship Request'),
        ('mentorship_accepted', 'Mentorship Accepted'),
        ('mentorship_rejected', 'Mentorship Rejected'),
        ('mentorship_completed', 'Mentorship Completed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    
    # Optional link to related objects
    mentorship_request = models.ForeignKey(MentorshipRequest, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    friend_request = models.ForeignKey(FriendRequest, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class UserPoints(models.Model):
    """Track points and streaks for gamification"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='points_profile')
    total_points = models.IntegerField(default=0)
    
    # Streak tracking
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_visit_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-total_points']
        verbose_name = "User Points"
        verbose_name_plural = "User Points"
        indexes = [
            models.Index(fields=['-total_points']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.total_points} points"
    
    def add_points(self, points, reason=""):
        """Add points to user's total"""
        self.total_points += points
        self.save()
        
        # Create activity log
        PointsActivity.objects.create(
            user=self.user,
            points=points,
            reason=reason
        )
    
    def update_daily_visit(self):
        """Update streak for daily visits and award points"""
        today = timezone.now().date()
        
        # If this is the first visit ever
        if not self.last_visit_date:
            self.current_streak = 1
            self.longest_streak = 1
            self.last_visit_date = today
            self.add_points(50, "Daily visit")
            self.save()
            return
        
        # If already visited today, do nothing
        if self.last_visit_date == today:
            return
        
        # Check if consecutive day
        yesterday = today - timezone.timedelta(days=1)
        if self.last_visit_date == yesterday:
            self.current_streak += 1
            self.add_points(50, "Daily visit")
            
            # Update longest streak
            if self.current_streak > self.longest_streak:
                self.longest_streak = self.current_streak
            
            # Bonus for 3-day streak
            if self.current_streak == 3:
                self.add_points(500, "3-day streak bonus!")
            # Continue giving streak bonuses at multiples of 3
            elif self.current_streak > 3 and self.current_streak % 3 == 0:
                self.add_points(500, f"{self.current_streak}-day streak bonus!")
        else:
            # Streak broken
            self.current_streak = 1
            self.add_points(50, "Daily visit")
        
        self.last_visit_date = today
        self.save()


class PointsActivity(models.Model):
    """Log of points earned by users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='points_activities')
    points = models.IntegerField()
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Points Activity"
        verbose_name_plural = "Points Activities"
    
    def __str__(self):
        return f"{self.user.username} +{self.points} - {self.reason}"


class UserNotification(models.Model):
    """Store app notifications for users (separate from mentorship notifications)"""
    LEVEL_CHOICES = [
        ('success', 'Success'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_notifications')
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "User Notification"
        verbose_name_plural = "User Notifications"
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.level}: {self.message[:50]}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class TimerSession(models.Model):
    """Collaborative timer sessions for group work"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='timer_sessions')
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_timer_sessions')
    participants = models.ManyToManyField(User, related_name='timer_sessions', blank=True)
    
    # Session details
    mode = models.CharField(max_length=20, default='work', choices=[
        ('work', 'Work Session'),
        ('break', 'Short Break'),
        ('longBreak', 'Long Break'),
    ])
    duration = models.IntegerField(help_text="Duration in minutes")
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Sharing
    share_code = models.CharField(max_length=20, unique=True, db_index=True)
    is_public = models.BooleanField(default=False, help_text="Allow anyone with the link to join")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['share_code']),
            models.Index(fields=['host', '-created_at']),
        ]
    
    def __str__(self):
        return f"Timer: {self.task.title} by {self.host.username} ({self.share_code})"
    
    def generate_share_code(self):
        """Generate a unique share code for the session"""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not TimerSession.objects.filter(share_code=code).exists():
                return code


class UserProfile(models.Model):
    """Extended user profile with timezone preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    timezone = models.CharField(
        max_length=63,
        default='UTC',
        help_text="User's preferred timezone"
    )
    bio = models.TextField(blank=True, help_text="User biography")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"{self.user.username} - {self.timezone}"


class LandingPageVisitor(models.Model):
    """Track visitors to the landing page for analytics"""
    # Visit information
    ip_address = models.GenericIPAddressField(help_text="Visitor's IP address")
    session_key = models.CharField(max_length=40, blank=True, help_text="Django session key")
    
    # Browser and device information
    user_agent = models.TextField(help_text="Full user agent string")
    browser = models.CharField(max_length=100, blank=True, help_text="Browser name")
    browser_version = models.CharField(max_length=50, blank=True, help_text="Browser version")
    os = models.CharField(max_length=100, blank=True, help_text="Operating system")
    device = models.CharField(max_length=50, blank=True, help_text="Device type (mobile, tablet, desktop)")
    
    # Traffic source
    referrer = models.URLField(max_length=500, blank=True, help_text="Referring URL")
    utm_source = models.CharField(max_length=100, blank=True, help_text="UTM source parameter")
    utm_medium = models.CharField(max_length=100, blank=True, help_text="UTM medium parameter")
    utm_campaign = models.CharField(max_length=100, blank=True, help_text="UTM campaign parameter")
    utm_term = models.CharField(max_length=100, blank=True, help_text="UTM term parameter")
    utm_content = models.CharField(max_length=100, blank=True, help_text="UTM content parameter")
    
    # Geographic information (can be enriched later with IP geolocation)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True, help_text="Geographic latitude coordinate")
    longitude = models.FloatField(null=True, blank=True, help_text="Geographic longitude coordinate")
    
    # Visit details
    landing_page_url = models.URLField(max_length=500, help_text="Full landing page URL visited")
    language = models.CharField(max_length=10, blank=True, help_text="Browser language")
    
    # Timestamps
    first_visit = models.DateTimeField(auto_now_add=True, help_text="First visit timestamp")
    last_visit = models.DateTimeField(auto_now=True, help_text="Last visit timestamp")
    visit_count = models.IntegerField(default=1, help_text="Number of times visited")
    
    # Conversion tracking
    converted_to_user = models.BooleanField(default=False, help_text="Whether visitor signed up")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                            related_name='landing_visits', help_text="User if converted")
    
    class Meta:
        verbose_name = "Landing Page Visitor"
        verbose_name_plural = "Landing Page Visitors"
        ordering = ['-last_visit']
        indexes = [
            models.Index(fields=['ip_address', '-last_visit']),
            models.Index(fields=['session_key']),
            models.Index(fields=['-first_visit']),
            models.Index(fields=['converted_to_user']),
        ]
    
    def __str__(self):
        return f"{self.ip_address} - {self.first_visit.strftime('%Y-%m-%d %H:%M')}"


class Habit(models.Model):
    """Recurring tasks/habits with specific frequencies"""
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habits', db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='daily', db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_active = models.BooleanField(default=True, db_index=True, help_text="Whether this habit is currently being tracked")
    start_date = models.DateField(default=timezone.now, help_text="When this habit starts/started")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active', '-created_at']),
            models.Index(fields=['user', 'frequency', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.get_frequency_display()})"
    
    def is_completed_today(self):
        """Check if habit was completed today"""
        today = timezone.now().date()
        return self.completions.filter(completion_date=today).exists()
    
    def is_completed_this_week(self):
        """Check if habit was completed this week"""
        from datetime import timedelta
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        return self.completions.filter(completion_date__gte=week_start, completion_date__lte=today).exists()
    
    def is_completed_this_month(self):
        """Check if habit was completed this month"""
        today = timezone.now().date()
        return self.completions.filter(
            completion_date__year=today.year,
            completion_date__month=today.month
        ).exists()
    
    def is_due_today(self):
        """Check if habit is due based on frequency"""
        if not self.is_active:
            return False
        
        if self.frequency == 'daily':
            return not self.is_completed_today()
        elif self.frequency == 'weekly':
            return not self.is_completed_this_week()
        elif self.frequency == 'monthly':
            return not self.is_completed_this_month()
        return False
    
    def get_current_streak(self):
        """Calculate current streak for daily habits"""
        if self.frequency != 'daily':
            return 0
        
        from datetime import timedelta
        today = timezone.now().date()
        streak = 0
        check_date = today
        
        # Check backwards from today
        while True:
            if self.completions.filter(completion_date=check_date).exists():
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        return streak
    
    def get_completion_count(self, days=30):
        """Get number of completions in last N days"""
        from datetime import timedelta
        today = timezone.now().date()
        start_date = today - timedelta(days=days)
        return self.completions.filter(completion_date__gte=start_date).count()


class HabitCompletion(models.Model):
    """Track when habits are completed"""
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='completions', db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habit_completions')
    completion_date = models.DateField(default=timezone.now, db_index=True)
    notes = models.TextField(blank=True, help_text="Optional notes about this completion")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-completion_date', '-created_at']
        unique_together = ('habit', 'completion_date')  # One completion per habit per day
        indexes = [
            models.Index(fields=['habit', '-completion_date']),
            models.Index(fields=['user', '-completion_date']),
        ]
    
    def __str__(self):
        return f"{self.habit.title} - {self.completion_date}"


class BlogPost(models.Model):
    """User-generated blog posts for the public blog section"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    CATEGORY_CHOICES = [
        ('personal-development', 'Personal Development'),
        ('productivity', 'Productivity'),
        ('habits', 'Habits & Routines'),
        ('self-improvement', 'Self-Improvement'),
        ('motivation', 'Motivation'),
        ('mindfulness', 'Mindfulness'),
        ('goal-setting', 'Goal Setting'),
        ('time-management', 'Time Management'),
    ]
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts', db_index=True)
    title = models.CharField(max_length=200, help_text="Catchy, descriptive title for your post")
    slug = models.SlugField(max_length=250, unique=True, db_index=True, help_text="URL-friendly version of title (auto-generated)")
    excerpt = models.TextField(max_length=300, help_text="Brief summary (150-300 characters) for the blog list")
    content = models.TextField(help_text="Full article content (Markdown supported)")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='personal-development', db_index=True)
    
    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    featured_image = models.URLField(blank=True, help_text="Optional featured image URL")
    read_time = models.IntegerField(default=5, help_text="Estimated reading time in minutes")
    views = models.IntegerField(default=0)
    
    # SEO
    meta_description = models.CharField(max_length=160, blank=True, help_text="SEO meta description")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', '-published_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['category', '-published_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Auto-generate slug from title if not provided
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Set published_at when status changes to published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        
        # Calculate read time based on content length (average reading speed: 200 words/min)
        word_count = len(self.content.split())
        self.read_time = max(1, round(word_count / 200))
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('blog_detail', kwargs={'slug': self.slug})


class Subscription(models.Model):
    """User subscription model for Pro features."""
    
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
        ('trialing', 'Trialing'),
        ('incomplete', 'Incomplete'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Stripe integration fields
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_price_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Subscription dates
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tracker_subscription'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['stripe_customer_id']),
            models.Index(fields=['stripe_subscription_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_plan_display()} ({self.status})"
    
    @property
    def is_pro(self):
        """Check if user has active pro subscription."""
        return self.plan == 'pro' and self.status in ['active', 'trialing']
    
    @property
    def is_active(self):
        """Check if subscription is active (includes trial)."""
        return self.status in ['active', 'trialing']
    
    @property
    def days_until_renewal(self):
        """Calculate days until next billing."""
        if self.current_period_end:
            delta = self.current_period_end - timezone.now()
            return delta.days
        return None


class PaymentHistory(models.Model):
    """Track payment transactions."""
    
    STATUS_CHOICES = [
        ('succeeded', 'Succeeded'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, related_name='payments')
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Stripe details
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Metadata
    description = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tracker_payment_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['stripe_payment_intent_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - ${self.amount} ({self.status})"
