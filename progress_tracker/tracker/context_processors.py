"""
Context processors for making common data available in templates
"""
from .models import UserNotification, FriendRequest
import pytz


def unread_notifications_count(request):
    """Add unread notification count to template context"""
    if request.user.is_authenticated:
        unread_count = UserNotification.objects.filter(
            user=request.user,
            read=False
        ).count()
        return {'unread_notifications_count': unread_count}
    return {'unread_notifications_count': 0}


def user_timezone(request):
    """Add user's timezone to template context"""
    if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
        user_tz = request.user.userprofile.timezone
        return {
            'user_timezone': user_tz,
            'user_timezone_obj': pytz.timezone(user_tz)
        }
    return {
        'user_timezone': 'UTC',
        'user_timezone_obj': pytz.UTC
    }


def pending_friend_requests_count(request):
    if not request.user.is_authenticated:
        return {'pending_friend_requests_count': 0}
    count = FriendRequest.objects.filter(to_user=request.user, status='pending').count()
    return {'pending_friend_requests_count': count}
