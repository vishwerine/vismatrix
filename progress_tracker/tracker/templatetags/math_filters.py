# myapp/templatetags/math_filters.py
from django import template

register = template.Library()

@register.filter
def div(value, arg):
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError):
        return None


@register.filter
def mod(value, arg):
    try:
        return int(value) % int(arg)
    except (ValueError, ZeroDivisionError):
        return None

@register.filter
def mul(value, arg):
    """Multiply two values"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def sub(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def available_users_count(users, current_friends):
    """Calculate available users (total - friends)"""
    try:
        total = len(users)
        friends_count = len(current_friends)
        return max(0, total - friends_count - 1)  # -1 excludes current user
    except (TypeError, ValueError):
        return 0

@register.inclusion_tag('tracker/stats_card.html')
def render_user_stats(users, current_friends):
    """Render user stats cards"""
    total_users = len(users)
    friends_count = len(current_friends)
    available_count = max(0, total_users - friends_count - 1)
    
    return {
        'total_users': total_users,
        'friends_count': friends_count,
        'available_count': available_count,
    }
