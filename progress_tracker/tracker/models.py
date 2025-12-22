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
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Time tracking
    estimated_duration = models.IntegerField(help_text="Estimated time in minutes", null=True, blank=True)
    actual_duration = models.IntegerField(help_text="Actual time spent in minutes", null=True, blank=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_completed(self):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()

# models.py - FIXED
class DailyLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_logs')
    date = models.DateField()  # ✅ NO DEFAULT HERE
    activity = models.TextField(max_length=500)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='logs')  # Link to task
    duration = models.PositiveIntegerField(help_text="Duration in minutes", default=0)
    created_at = models.DateTimeField(auto_now_add=True)


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
    
    from_user = models.ForeignKey(User, related_name='sent_friend_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_friend_requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user')
        ordering = ['-created_at']
    
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
