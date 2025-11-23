from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added

@receiver(user_signed_up)
def handle_user_signup(sender, request, user, **kwargs):
    """Handle actions when user signs up with username/password"""
    # No longer creating default categories - users will use global ones
    pass

@receiver(social_account_added)
def handle_social_signup(sender, request, sociallogin, **kwargs):
    """Handle actions when user signs up with Google"""
    # No longer creating default categories - users will use global ones
    pass
