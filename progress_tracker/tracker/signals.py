from django.dispatch import receiver
from django.db.models.signals import post_save
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added
from django.contrib.auth.models import User
from .models import Task, Category, UserProfile, DailyLog, HabitCompletion

@receiver(user_signed_up)
def handle_user_signup(sender, request, user, **kwargs):
    """Handle actions when user signs up with username/password"""
    create_default_task(user)
    create_user_profile(user, request)
    track_visitor_conversion(request, user)

@receiver(social_account_added)
def handle_social_signup(sender, request, sociallogin, **kwargs):
    """Handle actions when user signs up with Google"""
    create_user_profile(sociallogin.user, request)
    create_default_task(sociallogin.user)
    track_visitor_conversion(request, sociallogin.user)

@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    """Ensure UserProfile exists for all users"""
    if created:
        UserProfile.objects.get_or_create(user=instance)

def create_user_profile(user, request=None):
    """Create user profile with timezone detection from request"""
    # Try to detect timezone from request session if available
    detected_tz = 'UTC'
    if request and hasattr(request, 'session'):
        detected_tz = request.session.get('detected_timezone', 'UTC')
    
    UserProfile.objects.get_or_create(
        user=user,
        defaults={'timezone': detected_tz}
    )

def create_default_task(user):
    """Create a default 'General Activity' task for a user"""
    # Try to get a general category
    general_category = Category.objects.filter(name__iexact='General', is_global=True).first()
    if not general_category:
        general_category = Category.objects.filter(is_global=True).first()
    
    # Create default task
    Task.objects.get_or_create(
        user=user,
        title='General Activity',
        defaults={
            'description': 'Default task for general activities and time tracking',
            'category': general_category,
            'status': 'in_progress',
            'priority': 'medium',
        }
    )

def track_visitor_conversion(request, user):
    """Track when a landing page visitor converts to a user"""
    try:
        from .visitor_tracking import mark_visitor_converted
        mark_visitor_converted(request, user)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error tracking visitor conversion: {e}")


# User Activity Signals
@receiver(post_save, sender=Task)
def create_activity_on_task_completion(sender, instance, created, **kwargs):
    """Create UserActivity when a task is marked as completed."""
    from .models import UserActivity
    
    if instance.completed_at and not created:
        # Check if activity already exists
        if not UserActivity.objects.filter(task=instance, activity_type='task_completed').exists():
            UserActivity.objects.create(
                user=instance.user,
                activity_type='task_completed',
                task=instance,
                visibility=instance.visibility,
            )


@receiver(post_save, sender=DailyLog)
def create_activity_on_daily_log(sender, instance, created, **kwargs):
    """Create UserActivity when a daily log is created."""
    from .models import UserActivity
    
    if created:
        UserActivity.objects.create(
            user=instance.user,
            activity_type='log_created',
            daily_log=instance,
            visibility=instance.visibility,
        )


@receiver(post_save, sender=HabitCompletion)
def create_activity_on_habit_completion(sender, instance, created, **kwargs):
    """Create UserActivity when a habit is completed."""
    from .models import UserActivity
    
    if created:
        UserActivity.objects.create(
            user=instance.user,
            activity_type='habit_completed',
            habit_completion=instance,
            visibility='friends',  # Default visibility for habits
        )
