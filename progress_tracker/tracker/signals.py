from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added
from .models import Task, Category

@receiver(user_signed_up)
def handle_user_signup(sender, request, user, **kwargs):
    """Handle actions when user signs up with username/password"""
    create_default_task(user)

@receiver(social_account_added)
def handle_social_signup(sender, request, sociallogin, **kwargs):
    """Handle actions when user signs up with Google"""
    create_default_task(sociallogin.user)

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
