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
    # Can react to either a task completion or a daily log
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='reactions')
    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, null=True, blank=True, related_name='reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES, default='star')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'task', 'daily_log')  # One reaction per user per activity
        ordering = ['-created_at']
    
    def __str__(self):
        activity_type = "task" if self.task else "log"
        activity_id = self.task.id if self.task else self.daily_log.id
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




