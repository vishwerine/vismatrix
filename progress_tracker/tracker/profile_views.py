"""
User profile and timeline views for VisMatrix.
Handles user profiles, activity feeds, and privacy settings.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import timedelta
import logging

from .models import UserActivity, Task, DailyLog, HabitCompletion, Friendship, FriendRequest


@login_required
def my_profile(request):
    """Display logged-in user's own profile with their latest activities."""
    user = request.user
    
    # Get user's recent activities (their own posts/activities)
    activities = UserActivity.objects.filter(user=user).select_related(
        'task', 'daily_log', 'habit_completion', 'blog_post'
    ).prefetch_related('task__category', 'daily_log__category')
    
    # Paginate activities
    paginator = Paginator(activities, 20)
    page_number = request.GET.get('page', 1)
    activities_page = paginator.get_page(page_number)
    
    # Get stats
    total_activities = activities.count()
    today = timezone.now().date()
    today_activities = activities.filter(activity_date=today).count()
    
    # Get recent tasks completed (last 7 days)
    recent_tasks = Task.objects.filter(
        user=user,
        completed_at__isnull=False,
        completed_at__date__gte=today - timedelta(days=7)
    ).order_by('-completed_at')[:5]
    
    # Get recent logs (last 7 days)
    recent_logs = DailyLog.objects.filter(
        user=user,
        date__gte=today - timedelta(days=7)
    ).order_by('-created_at')[:5]
    
    # Get recent habit completions (last 7 days)
    recent_habits = HabitCompletion.objects.filter(
        user=user,
        completion_date__gte=today - timedelta(days=7)
    ).select_related('habit').order_by('-completion_date')[:5]
    
    # Get friends count
    friendships = Friendship.objects.filter(
        Q(user=user) | Q(friend=user)
    ).count()
    
    # Get pending friend requests count
    pending_requests = FriendRequest.objects.filter(
        to_user=user,
        status='pending'
    ).count()
    
    context = {
        'profile_user': user,
        'activities': activities_page,
        'total_activities': total_activities,
        'today_activities': today_activities,
        'recent_tasks': recent_tasks,
        'recent_logs': recent_logs,
        'recent_habits': recent_habits,
        'friends_count': friendships,
        'pending_requests': pending_requests,
        'is_own_profile': True,
    }
    
    return render(request, 'tracker/my_profile.html', context)


@login_required
def toggle_activity_privacy(request, activity_id):
    """Toggle privacy settings for an activity via AJAX."""
    activity = get_object_or_404(UserActivity, id=activity_id, user=request.user)
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        new_visibility = request.POST.get('visibility')
        
        # Validate visibility choice
        valid_choices = ['private', 'friends', 'public']
        if new_visibility not in valid_choices:
            return JsonResponse({'success': False, 'error': 'Invalid visibility option'}, status=400)
        
        activity.visibility = new_visibility
        activity.save()
        # Propagate visibility to linked objects used by friends feed
        try:
            if getattr(activity, 'task', None):
                try:
                    activity.task.visibility = new_visibility
                    activity.task.save(update_fields=['visibility'])
                except Exception as e:
                    logger.warning(f"Failed to update task visibility for activity {activity.id}: {e}")

            if getattr(activity, 'daily_log', None):
                try:
                    activity.daily_log.visibility = new_visibility
                    activity.daily_log.save(update_fields=['visibility'])
                except Exception as e:
                    logger.warning(f"Failed to update daily_log visibility for activity {activity.id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error propagating visibility for activity {activity.id}: {e}")
        
        return JsonResponse({
            'success': True,
            'message': f'Activity set to {new_visibility}',
            'new_visibility': new_visibility,
            'visibility_display': activity.get_visibility_display()
        })
    
    return JsonResponse({'success': False, 'error': 'POST required'}, status=405)


@login_required
def user_timeline(request, user_id):
    """Display timeline/feed of a specific user's activities (respecting privacy settings)."""
    profile_user = get_object_or_404(User, id=user_id)
    current_user = request.user
    is_own_profile = (profile_user == current_user)
    is_friend = False
    
    # Check if users are friends
    if not is_own_profile:
        is_friend = Friendship.objects.filter(
            Q(user=current_user, friend=profile_user) |
            Q(user=profile_user, friend=current_user)
        ).exists()
    
    # Build visibility query based on relationship
    if is_own_profile:
        # Users see all their own activities
        activities = UserActivity.objects.filter(
            user=profile_user
        ).select_related(
            'task', 'daily_log', 'habit_completion', 'blog_post'
        ).prefetch_related(
            'task__category', 'daily_log__category'
        ).order_by('-created_at')
    elif is_friend:
        # Friends can see 'friends' and 'public' activities (NOT 'private')
        activities = UserActivity.objects.filter(
            user=profile_user,
            visibility__in=['friends', 'public']
        ).select_related(
            'task', 'daily_log', 'habit_completion', 'blog_post'
        ).prefetch_related(
            'task__category', 'daily_log__category'
        ).order_by('-created_at')
    else:
        # Strangers can only see 'public' activities (NOT 'friends' or 'private')
        activities = UserActivity.objects.filter(
            user=profile_user,
            visibility='public'
        ).select_related(
            'task', 'daily_log', 'habit_completion', 'blog_post'
        ).prefetch_related(
            'task__category', 'daily_log__category'
        ).order_by('-created_at')
    
    # Paginate
    paginator = Paginator(activities, 20)
    page_number = request.GET.get('page', 1)
    activities_page = paginator.get_page(page_number)
    
    # Get friendship info for display
    friend_request_sent = False
    friendship = None
    if not is_own_profile:
        friendship = Friendship.objects.filter(
            Q(user=current_user, friend=profile_user) |
            Q(user=profile_user, friend=current_user)
        ).first()
        
        friend_request_sent = FriendRequest.objects.filter(
            from_user=current_user,
            to_user=profile_user,
            status='pending'
        ).exists()
    
    context = {
        'profile_user': profile_user,
        'activities': activities_page,
        'is_own_profile': is_own_profile,
        'is_friend': is_friend,
        'friendship': friendship,
        'friend_request_sent': friend_request_sent,
    }
    
    return render(request, 'tracker/user_timeline.html', context)


def create_user_activity(user, activity_type, task=None, daily_log=None, habit_completion=None, blog_post=None, visibility='friends'):
    """
    Helper function to create a UserActivity entry.
    Call this whenever a user completes an action.
    """
    try:
        activity = UserActivity.objects.create(
            user=user,
            activity_type=activity_type,
            task=task,
            daily_log=daily_log,
            habit_completion=habit_completion,
            blog_post=blog_post,
            visibility=visibility,
        )
        return activity
    except Exception as e:
        print(f"Error creating user activity: {e}")
        return None
