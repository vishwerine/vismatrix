from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from .models import Task, DailyLog, Category, DailySummary, FriendRequest, Friendship
from .forms import TaskForm, DailyLogForm, CategoryForm, DailySummaryForm
from django.views.decorators.http import require_http_methods

import json

# Dashboard
@login_required
def dashboard(request):
    """Main dashboard showing today's overview"""
    today = timezone.now().date()
    
    # Today's stats
    today_tasks = Task.objects.filter(user=request.user, created_at__date=today)
    today_completed = today_tasks.filter(status='completed').count()
    today_logs = DailyLog.objects.filter(user=request.user, date=today)
    today_time = today_logs.aggregate(total=Sum('duration'))['total'] or 0
    
    # Pending tasks
    pending_tasks = Task.objects.filter(
        user=request.user, 
        status__in=['pending', 'in_progress']
    ).order_by('priority', 'due_date')[:5]
    
    # Recent activities
    recent_logs = DailyLog.objects.filter(user=request.user)[:5]

    # Friends list
    friends_qs = Friendship.objects.filter(user=request.user).select_related('friend')
    total_friends = friends_qs.count()

    # Friends activity as you already have
    friends_activity = []
    for f in friends_qs[:5]:
        friend = f.friend
        completed = Task.objects.filter(
            user=friend,
            status='completed',
            completed_at__date__gte=week_ago
        ).count()
        time_spent = DailyLog.objects.filter(
            user=friend,
            date__gte=week_ago
        ).aggregate(total=Sum('duration'))['total'] or 0

        friends_activity.append({
            'friend': friend,
            'completed_tasks': completed,
            'time_spent': time_spent,
        })

    # Suggested users (non-friends)
    friend_ids = [f.friend_id for f in friends_qs]
    suggested_users = User.objects.exclude(
        Q(id=request.user.id) | Q(id__in=friend_ids)
    )[:5]  # limit to 5

    
    context = {
        'today': today,
        'today_completed': today_completed,
        'today_time': today_time,
        'pending_tasks': pending_tasks,
        'recent_logs': recent_logs,
                'friends': friends_activity,
        'total_friends': total_friends,
        'suggested_users': suggested_users,
    }
    return render(request, 'tracker/dashboard.html', context)

# Task views
@login_required
def task_list(request):
    """List all tasks with filtering"""
    status_filter = request.GET.get('status', 'all')
    
    tasks = Task.objects.filter(user=request.user)
    if status_filter != 'all':
        tasks = tasks.filter(status=status_filter)
    
    context = {
        'tasks': tasks,
        'status_filter': status_filter,
    }
    return render(request, 'tracker/task_list.html', context)

@login_required
def task_create(request):
    """Create a new task"""
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            return redirect('task_list')
    else:
        form = TaskForm(user=request.user)
    
    return render(request, 'tracker/task_form.html', {'form': form, 'title': 'Add New Task'})

@login_required
def task_update(request, pk):
    """Update an existing task"""
    task = get_object_or_404(Task, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('task_list')
    else:
        form = TaskForm(instance=task, user=request.user)
    
    return render(request, 'tracker/task_form.html', {'form': form, 'title': 'Edit Task'})

@login_required
def task_complete(request, pk):
    """Mark task as completed"""
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.mark_completed()
    return redirect('task_list')

@login_required
def task_delete(request, pk):
    """Delete a task"""
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        task.delete()
        return redirect('task_list')
    return render(request, 'tracker/task_confirm_delete.html', {'task': task})


# Daily log views
import pytz
from django.utils import timezone

from django.core.paginator import Paginator

@login_required
def log_list(request):
    """List logs for the current user, with category filter, stats, and pagination."""
    
    # Get all logs for current user
    logs = DailyLog.objects.filter(user=request.user).select_related("category").order_by("-date", "-id")

    # Filter by category if provided
    category_id = request.GET.get("category")
    if category_id:
        logs = logs.filter(category_id=category_id)

    # Calculate statistics
    total_logs = logs.count()
    total_minutes = logs.aggregate(total=Sum("duration"))["total"] or 0

    # Week statistics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    week_logs = logs.filter(date__gte=week_ago).count()

    # Pagination - 10 logs per page
    paginator = Paginator(logs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get all categories for filter dropdown
    categories = Category.objects.filter(user=request.user).order_by("name")

    context = {
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "categories": categories,
        "category_id": int(category_id) if category_id else None,
        "total_logs": total_logs,
        "total_minutes": total_minutes,
        "week_logs": week_logs,
    }
    
    return render(request, "tracker/log_list.html", context)

@login_required
def log_create(request):
    if request.method == "POST":
        form = DailyLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.user = request.user
            log.save()
            return redirect("log_list")
    else:
        form = DailyLogForm()
    return render(request, "tracker/log_form.html", {"form": form})


@login_required
def log_update(request, pk):
    log = get_object_or_404(DailyLog, pk=pk, user=request.user)
    if request.method == "POST":
        form = DailyLogForm(request.POST, instance=log)
        if form.is_valid():
            form.save()
            return redirect("log_list")
    else:
        form = DailyLogForm(instance=log)
    return render(request, "tracker/log_form.html", {"form": form})


@login_required
def log_delete(request, pk):
    log = get_object_or_404(DailyLog, pk=pk, user=request.user)
    if request.method == "POST":
        log.delete()
        return redirect("log_list")
    return render(request, "tracker/log_confirm_delete.html", {"log": log})




# Progress view
@login_required
def progress_view(request):
    """View progress over time"""
    today = timezone.now().date()
    
    daily_stats = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        tasks_completed = Task.objects.filter(
            user=request.user, 
            completed_at__date=date
        ).count()
        time_spent = DailyLog.objects.filter(
            user=request.user, 
            date=date
        ).aggregate(total=Sum('duration'))['total'] or 0
        
        daily_stats.append({
            'date': date,
            'tasks_completed': tasks_completed,
            'time_spent': time_spent,
        })
    
    context = {
        'daily_stats': daily_stats,
    }
    return render(request, 'tracker/progress.html', context)


# Category views
from django.db.models import Q

@login_required
def category_list(request):
    """List global and user's custom categories"""
    global_categories = Category.objects.filter(is_global=True)
    user_categories = Category.objects.filter(user=request.user)
    
    context = {
        'global_categories': global_categories,
        'user_categories': user_categories,
    }
    return render(request, 'tracker/category_list.html', context)

@login_required
def category_create(request):
    """Create a new custom category (user-specific only)"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.is_global = False  # User categories are never global
            category.save()
            return redirect('category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'tracker/category_form.html', {'form': form, 'title': 'Add Custom Category'})

@login_required
def category_edit(request, pk):
    """Edit user's custom category (cannot edit global categories)"""
    category = get_object_or_404(Category, pk=pk, user=request.user, is_global=False)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'tracker/category_form.html', {'form': form, 'title': 'Edit Custom Category'})

@login_required
def category_delete(request, pk):
    """Delete user's custom category (cannot delete global categories)"""
    category = get_object_or_404(Category, pk=pk, user=request.user, is_global=False)
    
    if request.method == 'POST':
        category.delete()
        return redirect('category_list')
    
    return render(request, 'tracker/category_confirm_delete.html', {'category': category})


from django.contrib.auth.models import User
from django.contrib import messages

@login_required
def user_list(request):
    """Search and browse all users to find and add as friends."""
    
    # Get search query
    search_query = request.GET.get('search', '').strip()
    
    # Start with all users except current user
    users = User.objects.exclude(id=request.user.id)
    
    # Apply search filter
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(userprofile__bio__icontains=search_query)
        ).distinct()
    
    # Order by username
    users = users.order_by('username').select_related('userprofile')
    
    # Limit results for performance
    users = users[:50]
    
    context = {
        'users': users,
        'search_query': search_query,
    }
    
    return render(request, 'tracker/user_list.html', context)







# ===== SEND FRIEND REQUEST (AUTO-ACCEPT) =====
@login_required
@require_http_methods(["POST"])
def send_friend_request(request, user_id):
    """Send a friend request that automatically creates mutual friendship (AJAX & redirect support)"""
    
    # Prevent self-requests
    if user_id == request.user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Cannot add yourself'}, status=400)
        messages.error(request, "You cannot send a friend request to yourself.")
        return redirect('user_list')
    
    try:
        to_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
        messages.error(request, "User not found")
        return redirect('user_list')
    
    # Check if already friends
    if Friendship.objects.filter(user=request.user, friend=to_user).exists():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'warning', 'message': f'Already friends with {to_user.username}'}, status=400)
        messages.info(request, f"You are already friends with {to_user.username}")
        return redirect('user_list')
    
    # Check if reverse friendship exists (they added you first)
    reverse_friendship = Friendship.objects.filter(user=to_user, friend=request.user).exists()
    
    if reverse_friendship:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'warning', 'message': f'{to_user.username} already has you as a friend'}, status=400)
        messages.info(request, f"{to_user.username} already has you as a friend")
        return redirect('user_list')
    
    # ===== AUTO-ACCEPT: Create mutual friendship =====
    # Create friendship from current user to target user
    friendship1, created1 = Friendship.objects.get_or_create(
        user=request.user,
        friend=to_user
    )
    
    # Create reverse friendship from target user to current user
    friendship2, created2 = Friendship.objects.get_or_create(
        user=to_user,
        friend=request.user
    )
    
    # Delete any pending friend requests between them
    FriendRequest.objects.filter(
        from_user__in=[request.user, to_user],
        to_user__in=[request.user, to_user],
        status='pending'
    ).delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': f'You are now friends with {to_user.username}!'}, status=201)
    messages.success(request, f"You are now friends with {to_user.username}!")
    
    return redirect('user_list')

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods



# ===== ACCEPT FRIEND REQUEST =====
@login_required
@require_http_methods(["POST"])
def accept_friend_request(request, request_id):
    """Accept a friend request (AJAX enabled)"""
    
    try:
        friend_request = FriendRequest.objects.get(
            pk=request_id,
            to_user=request.user,
            status='pending'
        )
    except FriendRequest.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Request not found'}, status=404)
    
    try:
        # Mark as accepted
        friend_request.status = 'accepted'
        friend_request.save()
        
        from_user = friend_request.from_user
        return JsonResponse({
            'status': 'success',
            'message': f'You are now friends with {from_user.username}'
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ===== REJECT FRIEND REQUEST =====
@login_required
@require_http_methods(["POST"])
def reject_friend_request(request, request_id):
    """Reject a friend request (AJAX enabled)"""
    
    try:
        friend_request = FriendRequest.objects.get(
            pk=request_id,
            to_user=request.user,
            status='pending'
        )
    except FriendRequest.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Request not found'}, status=404)
    
    try:
        from_user = friend_request.from_user
        
        # Mark as rejected
        friend_request.status = 'rejected'
        friend_request.save()
        
        # DELETE friendships if rejected
        Friendship.objects.filter(user=request.user, friend=from_user).delete()
        Friendship.objects.filter(user=from_user, friend=request.user).delete()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Rejected friend request from {from_user.username}'
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ===== CANCEL SENT REQUEST =====
@login_required
@require_http_methods(["POST"])
def cancel_friend_request(request, user_id):
    """Cancel a sent friend request (AJAX enabled)"""
    
    try:
        to_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
    
    try:
        friend_request = FriendRequest.objects.get(
            from_user=request.user,
            to_user=to_user,
            status='pending'
        )
        
        friend_request.delete()
        
        # DELETE friendships if cancelled
        Friendship.objects.filter(user=request.user, friend=to_user).delete()
        Friendship.objects.filter(user=to_user, friend=request.user).delete()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Cancelled friend request to {to_user.username}'
        }, status=200)
        
    except FriendRequest.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Request not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ===== REMOVE FRIEND =====
@login_required
@require_http_methods(["POST"])
def remove_friend(request, friendship_id):
    """Remove a friend (AJAX enabled)"""
    
    try:
        friendship = Friendship.objects.get(pk=friendship_id, user=request.user)
    except Friendship.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Friendship not found'}, status=404)
    
    try:
        friend = friendship.friend
        
        # Delete both directions
        Friendship.objects.filter(user=request.user, friend=friend).delete()
        Friendship.objects.filter(user=friend, friend=request.user).delete()
        
        # Delete associated friend requests
        FriendRequest.objects.filter(
            from_user__in=[request.user, friend],
            to_user__in=[request.user, friend]
        ).delete()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Removed {friend.username} from friends'
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ===== FRIEND REQUESTS VIEW (unchanged) =====
@login_required
def friend_requests(request):
    """View all pending friend requests"""
    received_requests = request.user.received_friend_requests.filter(
        status='pending'
    ).select_related('from_user')
    
    sent_requests = request.user.sent_friend_requests.filter(
        status='pending'
    ).select_related('to_user')
    
    context = {
        'received_requests': received_requests,
        'sent_requests': sent_requests,
    }
    return render(request, 'tracker/friend_requests.html', context)




# ===== FRIENDS LIST (unchanged) =====
@login_required
def friends_list(request):
    """View all friends with their recent progress"""
    friends = Friendship.objects.filter(user=request.user).select_related('friend')
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    friends_data = []
    for friendship in friends:
        friend = friendship.friend
        completed_tasks = Task.objects.filter(
            user=friend,
            status='completed',
            completed_at__date__gte=week_ago
        ).count()
        
        total_time = DailyLog.objects.filter(
            user=friend,
            date__gte=week_ago
        ).aggregate(total=Sum('duration'))['total'] or 0
        
        friends_data.append({
            'friend': friend,
            'friendship': friendship,
            'completed_tasks': completed_tasks,
            'total_time': total_time,
        })
    
    context = {'friends_data': friends_data}
    return render(request, 'tracker/friends_list.html', context)







@login_required
def friend_progress_list(request):
    """View progress summary of all friends"""
    friends = request.user.friendships.select_related('friend')
    friend_users = [f.friend for f in friends]

    # Gather progress summary: completed tasks count and total time spent in last 7 days
    from django.db.models import Sum, Count
    from django.utils.timezone import now
    from datetime import timedelta
    
    today = now().date()
    week_ago = today - timedelta(days=7)
    
    progress_data = []

    for friend in friend_users:
        completed_tasks = friend.tasks.filter(status='completed', completed_at__date__gte=week_ago).count()
        total_time = friend.daily_logs.filter(date__gte=week_ago).aggregate(total=Sum('duration'))['total'] or 0
        
        progress_data.append({
            'friend': friend,
            'completed_tasks': completed_tasks,
            'total_time': total_time,
        })

    context = {
        'progress_data': progress_data,
    }
    return render(request, 'tracker/friend_progress_list.html', context)

@login_required
def view_friend_progress(request, friend_id):
    """View detailed progress for a specific friend"""
    friend = get_object_or_404(User, pk=friend_id)
    # Confirm friendship
    if not request.user.friendships.filter(friend=friend).exists():
        messages.error(request, "You can only view progress of your friends.")
        return redirect('friend_progress_list')

    tasks = friend.tasks.filter(status='completed').order_by('-completed_at')[:20]
    logs = friend.daily_logs.order_by('-date')[:20]

    context = {
        'friend': friend,
        'tasks': tasks,
        'logs': logs,
    }
    return render(request, 'tracker/friend_progress_detail.html', context)

# Enhanced Dashboard with Friends Info
@login_required
def dashboard(request):
    """Main dashboard showing today's overview + friends activity"""
    today = timezone.now().date()
    
    # Today's stats
    today_tasks = Task.objects.filter(user=request.user, created_at__date=today)
    today_completed = today_tasks.filter(status='completed').count()
    today_logs = DailyLog.objects.filter(user=request.user, date=today)
    today_time = today_logs.aggregate(total=Sum('duration'))['total'] or 0
    
    # Pending tasks
    pending_tasks = Task.objects.filter(
        user=request.user, 
        status__in=['pending', 'in_progress']
    ).order_by('priority', 'due_date')[:5]
    
    # Recent activities
    recent_logs = DailyLog.objects.filter(user=request.user).order_by('-date')[:5]
    
    # Friend requests
    pending_requests = request.user.received_friend_requests.filter(status='pending')
    pending_count = pending_requests.count()
    
    # Friends list
    friends = Friendship.objects.filter(user=request.user).select_related('friend')[:5]
    total_friends = Friendship.objects.filter(user=request.user).count()
    
    # Friends' recent activity (last 7 days)
    week_ago = today - timedelta(days=7)
    friend_ids = [f.friend.id for f in friends]
    
    friends_activity = []
    for friend_obj in friends:
        friend = friend_obj.friend
        completed = Task.objects.filter(
            user=friend, 
            status='completed', 
            completed_at__date__gte=week_ago
        ).count()
        time_spent = DailyLog.objects.filter(
            user=friend, 
            date__gte=week_ago
        ).aggregate(total=Sum('duration'))['total'] or 0
        
        friends_activity.append({
            'friend': friend,
            'completed_tasks': completed,
            'time_spent': time_spent,
        })
    
    context = {
        'today': today,
        'today_completed': today_completed,
        'today_time': today_time,
        'pending_tasks': pending_tasks,
        'recent_logs': recent_logs,
        'pending_requests': pending_requests,
        'pending_count': pending_count,
        'friends': friends_activity,
        'total_friends': total_friends,
    }
    return render(request, 'tracker/dashboard.html', context)

# User List with Request Status
@login_required
def user_list(request):
    """List all users with friendship/request status"""
    search_query = request.GET.get('search', '')
    
    users = User.objects.exclude(id=request.user.id)
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query)
        )
    
    # Get current user's friends
    current_friends = request.user.friendships.values_list('friend_id', flat=True)
    
    # Get sent requests
    sent_requests = request.user.sent_friend_requests.filter(
        status='pending'
    ).values_list('to_user_id', flat=True)
    
    # Get received requests
    received_requests = request.user.received_friend_requests.filter(
        status='pending'
    ).values_list('from_user_id', flat=True)
    
    context = {
        'users': users,
        'current_friends': current_friends,
        'sent_requests': sent_requests,
        'received_requests': received_requests,
        'search_query': search_query,
    }
    return render(request, 'tracker/user_list.html', context)




# ===== VIEW USER PROFILE (PUBLIC) =====
@login_required
def view_user_profile(request, user_id):
    """View any user's public profile"""
    
    # Get the user
    user = get_object_or_404(User, pk=user_id)
    
    # Can't view your own profile this way
    if user == request.user:
        return redirect('dashboard')
    
    # Get user's recent data
    tasks = Task.objects.filter(user=user, status='completed').order_by('-completed_at')[:20]
    logs = DailyLog.objects.filter(user=user).order_by('-date')[:20]
    
    # Weekly stats
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    weekly_completed = Task.objects.filter(
        user=user,
        status='completed',
        completed_at__date__gte=week_ago
    ).count()
    
    weekly_time = DailyLog.objects.filter(
        user=user,
        date__gte=week_ago
    ).aggregate(total=Sum('duration'))['total'] or 0
    
    # Check friendship status
    is_friend = Friendship.objects.filter(user=request.user, friend=user).exists()
    
    # Check if friend request exists
    friend_request = FriendRequest.objects.filter(
        from_user=request.user,
        to_user=user,
        status='pending'
    ).first()
    
    # Check if received friend request from this user
    received_request = FriendRequest.objects.filter(
        from_user=user,
        to_user=request.user,
        status='pending'
    ).first()
    
    context = {
        'user': user,
        'tasks': tasks,
        'logs': logs,
        'weekly_completed': weekly_completed,
        'weekly_time': weekly_time,
        'is_friend': is_friend,
        'friend_request': friend_request,  # Sent request
        'received_request': received_request,  # Received request
    }
    return render(request, 'tracker/user_profile.html', context)


from django.db.models import Sum
from datetime import timedelta

@login_required
def view_friend_profile(request, friendship_id):
    """View detailed progress for a specific friend with charts"""
    friendship = get_object_or_404(Friendship, pk=friendship_id, user=request.user)
    friend = friendship.friend
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    # ===== STATS =====
    total_time = DailyLog.objects.filter(user=friend).aggregate(
        total=Sum('duration')
    )['total'] or 0
    
    total_tasks = Task.objects.filter(user=friend, status='completed').count()
    
    week_time = DailyLog.objects.filter(
        user=friend,
        date__gte=week_ago
    ).aggregate(total=Sum('duration'))['total'] or 0
    
    week_tasks = Task.objects.filter(
        user=friend,
        status='completed',
        completed_at__date__gte=week_ago
    ).count()
    
    # Activity streak
    activity_streak = 0
    check_date = today
    while True:
        has_activity = DailyLog.objects.filter(
            user=friend,
            date=check_date
        ).exists()
        if has_activity:
            activity_streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    
    # ===== WEEKLY DATA FOR CHART =====
    weekly_labels = []
    weekly_values = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        daily_time = DailyLog.objects.filter(
            user=friend,
            date=date
        ).aggregate(total=Sum('duration'))['total'] or 0
        weekly_labels.append(date.strftime('%a'))
        weekly_values.append(daily_time)
    
    weekly_data = {
        'labels': weekly_labels,
        'data': weekly_values
    }
    
    # ===== CATEGORY DATA FOR CHART =====
    category_data_qs = DailyLog.objects.filter(
        user=friend,
        date__gte=week_ago
    ).values('category__name').annotate(
        total=Sum('duration')
    ).order_by('-total')[:5]
    
    category_labels = []
    category_values = []
    category_colors = [
        'rgba(59, 130, 246, 0.8)',
        'rgba(139, 92, 246, 0.8)',
        'rgba(34, 197, 94, 0.8)',
        'rgba(251, 146, 60, 0.8)',
        'rgba(244, 63, 94, 0.8)',
    ]
    
    for idx, item in enumerate(category_data_qs):
        category_labels.append(item['category__name'] or 'Uncategorized')
        category_values.append(item['total'])
    
    category_data = {
        'labels': category_labels,
        'data': category_values,
        'colors': category_colors[:len(category_labels)]
    }
    
    # ===== HEATMAP DATA =====
    heatmap_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        daily_time = DailyLog.objects.filter(
            user=friend,
            date=date
        ).aggregate(total=Sum('duration'))['total'] or 0
    
        # Color intensity based on activity
        if daily_time == 0:
            color = 'bg-slate-100'
            border = 'border-slate-200'
        elif daily_time < 30:
            color = 'bg-green-200'
            border = 'border-green-300'
        elif daily_time < 60:
            color = 'bg-green-400'
            border = 'border-green-500'
        elif daily_time < 120:
            color = 'bg-green-600'
            border = 'border-green-700'
        else:
            color = 'bg-green-800'
            border = 'border-green-900'
    
        heatmap_data.append({
            'label': date.strftime('%a, %b %d'),
            'minutes': daily_time,
            'color': color,
            'border': border,
            'day_label': date.strftime('%a')  # ✅ ADD THIS LINE
        })
    
    # ===== RECENT TASKS & LOGS =====
    recent_tasks = Task.objects.filter(
        user=friend,
        status='completed',
        completed_at__date__gte=week_ago
    ).order_by('-completed_at')[:10]
    
    recent_logs = DailyLog.objects.filter(
        user=friend,
        date__gte=week_ago
    ).select_related('category').order_by('-date')[:10]
    
    context = {
        'friend': friend,
        'friendship': friendship,
        'total_time': total_time,
        'total_tasks': total_tasks,
        'week_time': week_time,
        'week_tasks': week_tasks,
        'activity_streak': activity_streak,
        'weekly_data': json.dumps(weekly_data),
        'category_data': json.dumps(category_data),
        'heatmap_data': heatmap_data,
        'recent_tasks': recent_tasks,
        'recent_logs': recent_logs,
    }
    return render(request, 'tracker/friend_profile.html', context)
