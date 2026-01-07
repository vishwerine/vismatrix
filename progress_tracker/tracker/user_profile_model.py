from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import pytz


class UserProfile(models.Model):
    """Extended user profile with timezone preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    timezone = models.CharField(
        max_length=63,
        default='UTC',
        choices=[(tz, tz) for tz in pytz.common_timezones],
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


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Ensure profile exists for existing users
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()
