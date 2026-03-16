"""
Template tags and filters for timezone conversion
"""
from django import template
from django.utils import timezone as django_timezone
import pytz

register = template.Library()


@register.filter
def to_user_timezone(datetime_obj, user=None):
    """Convert a datetime to user's timezone"""
    if not datetime_obj:
        return None
    
    # Make sure datetime is aware
    if django_timezone.is_naive(datetime_obj):
        datetime_obj = django_timezone.make_aware(datetime_obj, pytz.UTC)
    
    # Get user's timezone
    if user and hasattr(user, 'userprofile'):
        user_tz = pytz.timezone(user.userprofile.timezone)
        return datetime_obj.astimezone(user_tz)
    
    # Fall back to current timezone (set by middleware)
    return django_timezone.localtime(datetime_obj)


@register.filter
def format_user_datetime(datetime_obj, format_string="M d, Y g:i A"):
    """Format datetime in user's timezone"""
    if not datetime_obj:
        return ""
    
    local_dt = django_timezone.localtime(datetime_obj)
    return local_dt.strftime(format_string.replace("M", "%b").replace("d", "%d").replace("Y", "%Y").replace("g", "%-I").replace("i", "%M").replace("A", "%p"))
