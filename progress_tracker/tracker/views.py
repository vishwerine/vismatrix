from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from .models import Task, DailyLog, Category, DailySummary, FriendRequest, Friendship
from .forms import TaskForm, DailyLogForm, CategoryForm, DailySummaryForm

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
@login_required
def log_list(request):
    """List daily logs"""
    date_filter = request.GET.get('date')
    
    logs = DailyLog.objects.filter(user=request.user)
    if date_filter:
        logs = logs.filter(date=date_filter)
    
    # Group by date
    logs_by_date = {}
    for log in logs:
        if log.date not in logs_by_date:
            logs_by_date[log.date] = []
        logs_by_date[log.date].append(log)
    
    context = {
        'logs_by_date': logs_by_date,
        'date_filter': date_filter,
    }
    return render(request, 'tracker/log_list.html', context)

@login_required
def log_create(request):
    """Create a new daily log entry"""
    if request.method == 'POST':
        form = DailyLogForm(request.POST, user=request.user)
        if form.is_valid():
            log = form.save(commit=False)
            log.user = request.user
            log.save()
            return redirect('log_list')
    else:
        form = DailyLogForm(initial={'date': timezone.now().date()}, user=request.user)
    
    return render(request, 'tracker/log_form.html', {'form': form, 'title': 'Log Activity'})

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
    """List all users except the current user, with friendship status"""
    users = User.objects.exclude(id=request.user.id)
    # Get current user's friends IDs for quick lookup
    current_friends = request.user.friendships.values_list('friend_id', flat=True)
    context = {
        'users': users,
        'current_friends': current_friends,
    }
    return render(request, 'tracker/user_list.html', context)

@login_required
def add_friend(request, user_id):
    """Send friend request immediately by creating friendship"""
    if user_id == request.user.id:
        messages.error(request, "You cannot add yourself as a friend.")
        return redirect('user_list')

    friend_user = get_object_or_404(User, pk=user_id)

    # Check if already friends
    if request.user.friendships.filter(friend=friend_user).exists():
        messages.info(request, f"You are already friends with {friend_user.username}")
    else:
        Friendship.objects.create(user=request.user, friend=friend_user)
        messages.success(request, f"You are now friends with {friend_user.username}")

    return redirect('user_list')

@login_required
def remove_friend(request, user_id):
    friend_user = get_object_or_404(User, pk=user_id)
    friendship = request.user.friendships.filter(friend=friend_user).first()
    if friendship:
        friendship.delete()
        messages.success(request, f"You are no longer friends with {friend_user.username}")
    else:
        messages.info(request, f"You were not friends with {friend_user.username}")
    return redirect('user_list')

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

# Send Friend Request
@login_required
def send_friend_request(request, user_id):
    """Send a friend request to another user"""
    if user_id == request.user.id:
        messages.error(request, "You cannot send a friend request to yourself.")
        return redirect('user_list')
    
    to_user = get_object_or_404(User, pk=user_id)
    
    # Check if already friends
    if request.user.friendships.filter(friend=to_user).exists():
        messages.info(request, f"You are already friends with {to_user.username}")
        return redirect('user_list')
    
    # Check if request already exists
    existing_request = FriendRequest.objects.filter(
        from_user=request.user, 
        to_user=to_user, 
        status='pending'
    ).first()
    
    if existing_request:
        messages.info(request, f"Friend request already sent to {to_user.username}")
    else:
        FriendRequest.objects.create(from_user=request.user, to_user=to_user)
        messages.success(request, f"Friend request sent to {to_user.username}")
    
    return redirect('user_list')

# Accept Friend Request
@login_required
def accept_friend_request(request, request_id):
    """Accept a friend request"""
    friend_request = get_object_or_404(
        FriendRequest, 
        pk=request_id, 
        to_user=request.user, 
        status='pending'
    )
    
    friend_request.accept()
    messages.success(request, f"You are now friends with {friend_request.from_user.username}")
    
    return redirect('friend_requests')

# Reject Friend Request
@login_required
def reject_friend_request(request, request_id):
    """Reject a friend request"""
    friend_request = get_object_or_404(
        FriendRequest, 
        pk=request_id, 
        to_user=request.user, 
        status='pending'
    )
    
    friend_request.reject()
    messages.info(request, f"Friend request from {friend_request.from_user.username} rejected")
    
    return redirect('friend_requests')

# Cancel Sent Request
@login_required
def cancel_friend_request(request, user_id):
    """Cancel a sent friend request"""
    to_user = get_object_or_404(User, pk=user_id)
    friend_request = FriendRequest.objects.filter(
        from_user=request.user, 
        to_user=to_user, 
        status='pending'
    ).first()
    
    if friend_request:
        friend_request.delete()
        messages.success(request, f"Friend request to {to_user.username} cancelled")
    
    return redirect('user_list')

# Remove Friend
@login_required
def remove_friend(request, user_id):
    """Remove a friend"""
    friend_user = get_object_or_404(User, pk=user_id)
    
    # Delete both directions of friendship
    Friendship.objects.filter(user=request.user, friend=friend_user).delete()
    Friendship.objects.filter(user=friend_user, friend=request.user).delete()
    
    messages.success(request, f"You are no longer friends with {friend_user.username}")
    return redirect('user_list')

# Friend Requests Page
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

# Friends List and Progress
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
    
    context = {
        'friends_data': friends_data,
    }
    return render(request, 'tracker/friends_list.html', context)

# View Friend Profile
@login_required
def view_friend_profile(request, friend_id):
    """View detailed progress for a specific friend"""
    friend = get_object_or_404(User, pk=friend_id)
    
    # Confirm friendship
    if not request.user.friendships.filter(friend=friend).exists():
        messages.error(request, "You can only view progress of your friends.")
        return redirect('friends_list')
    
    # Get friend's recent data
    tasks = Task.objects.filter(user=friend, status='completed').order_by('-completed_at')[:20]
    logs = DailyLog.objects.filter(user=friend).order_by('-date')[:20]
    
    # Weekly stats
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    weekly_completed = Task.objects.filter(
        user=friend, 
        status='completed', 
        completed_at__date__gte=week_ago
    ).count()
    weekly_time = DailyLog.objects.filter(
        user=friend, 
        date__gte=week_ago
    ).aggregate(total=Sum('duration'))['total'] or 0
    
    context = {
        'friend': friend,
        'tasks': tasks,
        'logs': logs,
        'weekly_completed': weekly_completed,
        'weekly_time': weekly_time,
    }
    return render(request, 'tracker/friend_profile.html', context)

