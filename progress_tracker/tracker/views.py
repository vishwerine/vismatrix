from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q, Case, When, Value, F, DateField, Prefetch
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import timedelta, date
from .models import Task, DailyLog, Category, DailySummary, FriendRequest, Friendship, ActivityReaction, Plan, PlanNode, DaySchedule
from .forms import TaskForm, DailyLogForm, CategoryForm, DailySummaryForm, PlanForm, PlanNodeForm, UserProfileForm
from django.views.decorators.http import require_http_methods
import logging

from .decorators import rate_limit, validate_ajax, validate_json, log_errors
from .services import ICloudCalendarService

import json
import calendar

logger = logging.getLogger(__name__)

def landing_page(request):
    """Public landing page - accessible without authentication."""
    return render(request, 'tracker/landing_page.html')


@login_required
def day_planner(request):
    """Day planner view showing hourly schedule."""
    today = timezone.now().date()
    
    # Get today's tasks
    pending_tasks_qs = (
        Task.objects.filter(
            user=request.user,
            status__in=["pending", "in_progress"],
        )
        .select_related('category')
        .order_by("due_date", "priority")
    )
    
    # Get plan tasks from active plans and build task->plan mapping
    from .models import Plan, PlanNode
    active_plans = Plan.objects.filter(user=request.user, is_active=True)
    task_to_plans = {}  # Map task_id to list of plan names
    plan_tasks = []
    
    for plan in active_plans:
        nodes = PlanNode.objects.filter(plan=plan).select_related('task')
        for node in nodes:
            if node.task and node.task.status in ["pending", "in_progress"]:
                # Track which tasks belong to which plans
                if node.task.id not in task_to_plans:
                    task_to_plans[node.task.id] = []
                task_to_plans[node.task.id].append(plan.title)
                
                # Add to plan_tasks list (avoiding duplicates)
                if not any(pt['id'] == node.task.id for pt in plan_tasks):
                    plan_tasks.append({
                        'id': node.task.id,
                        'title': node.task.title,
                        'plan_name': plan.title,
                        'category': node.task.category,
                    })
    
    # Annotate pending tasks with plan information
    pending_tasks = []
    for task in pending_tasks_qs:
        task.plan_names = task_to_plans.get(task.id, [])
        pending_tasks.append(task)
    
    # Get today's logs
    today_logs = (
        DailyLog.objects.filter(user=request.user, date=today)
        .select_related("category", "task")
        .order_by("-date", "-id")
    )
    
    context = {
        "today": today,
        "pending_tasks": pending_tasks,
        "plan_tasks": plan_tasks,
        "today_logs": today_logs,
    }
    
    return render(request, "tracker/day_planner.html", context)


@login_required
def dashboard(request):
    """Main dashboard showing today's overview + weekly summary."""

    # --- Dates / ranges ---
    # Use server-local datetime date to avoid timezone mismatches
    today = timezone.now().date()
    # Use the last 7 days from the most recent log date for weekly data
    recent_log = DailyLog.objects.filter(user=request.user).order_by('-date').first()
    if recent_log:
        base_date = recent_log.date
    else:
        base_date = today
    week_ago = base_date - timedelta(days=6)         # last 7 days including today
    month_start = today.replace(day=1)

    # --- Today's stats ---
    today_tasks = Task.objects.filter(user=request.user, created_at__date=today)
    today_tasks_count = today_tasks.count()
    today_completed = today_tasks.filter(status="completed").count()

    today_logs = DailyLog.objects.filter(user=request.user, date=today)
    today_time = today_logs.aggregate(total=Sum("duration"))["total"] or 0

    # --- Pending tasks (for "Today's tasks" card) ---
    # Order by: tasks with due dates first (earliest first), then by priority
    pending_tasks = (
        Task.objects.filter(
            user=request.user,
            status__in=["pending", "in_progress"],
        )
        .select_related('category')  # Optimize query
        .annotate(
            # Treat null due_dates as far future (9999-12-31) so they appear last
            effective_due_date=Coalesce(
                F('due_date'), 
                Value(date(9999, 12, 31)), 
                output_field=DateField()
            )
        )
        .order_by("effective_due_date", "priority")
    )

    # --- Recent activities ---
    recent_logs = (
        DailyLog.objects.filter(user=request.user)
        .select_related("category", "task")
        .order_by("-date", "-id")[:5]
    )

    # --- Friends list & activity (for other parts of the app) ---
    friends_qs = Friendship.objects.filter(user=request.user).select_related("friend")
    total_friends = friends_qs.count()

    friends_activity = []
    for f in friends_qs[:5]:
        friend = f.friend
        completed = Task.objects.filter(
            user=friend,
            status="completed",
            completed_at__date__gte=week_ago,
            completed_at__date__lte=today,
        ).count()
        time_spent = (
            DailyLog.objects.filter(user=friend, date__gte=week_ago, date__lte=today)
            .aggregate(total=Sum("duration"))["total"]
            or 0
        )

        friends_activity.append(
            {
                "friend": friend,
                "completed_tasks": completed,
                "time_spent": time_spent,
            }
        )

    # --- Friends timeline feed (recent tasks and logs from friends) ---
    friend_ids = [f.friend_id for f in friends_qs]
    friends_timeline = []

    # Create a mapping of friend_id to friendship_id for quick lookup
    friendship_map = {f.friend_id: f.id for f in friends_qs}

    # Get recent completed tasks from friends
    if friend_ids:
        recent_friend_tasks = Task.objects.filter(
            user_id__in=friend_ids,
            status="completed",
            completed_at__isnull=False
        ).select_related("user", "category").order_by("-completed_at")[:10]

        for task in recent_friend_tasks:
            # Get reaction info for this task
            star_count = ActivityReaction.objects.filter(task=task).count()
            user_starred = ActivityReaction.objects.filter(task=task, user=request.user).exists()
            
            friends_timeline.append({
                "type": "task",
                "user": task.user,
                "friendship_id": friendship_map.get(task.user_id),
                "title": task.title,
                "category": task.category,
                "timestamp": task.completed_at,
                "duration": None,
                "id": task.id,
                "star_count": star_count,
                "user_starred": user_starred,
            })

        # Get recent logs from friends
        recent_friend_logs = DailyLog.objects.filter(
            user_id__in=friend_ids
        ).select_related("user", "category").order_by("-date", "-id")[:10]

        for log in recent_friend_logs:
            # Get reaction info for this log
            star_count = ActivityReaction.objects.filter(daily_log=log).count()
            user_starred = ActivityReaction.objects.filter(daily_log=log, user=request.user).exists()
            
            # Create a datetime from the date for sorting
            timestamp = timezone.datetime.combine(log.date, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone())
            friends_timeline.append({
                "type": "log",
                "user": log.user,
                "friendship_id": friendship_map.get(log.user_id),
                "title": log.activity,
                "category": log.category,
                "timestamp": timestamp,
                "duration": log.duration,
                "id": log.id,
                "star_count": star_count,
                "user_starred": user_starred,
            })

        # Sort combined timeline by timestamp (most recent first)
        friends_timeline.sort(key=lambda x: x["timestamp"], reverse=True)
        # Limit to 5 most recent items for dashboard preview
        friends_timeline = friends_timeline[:5]

    # --- Suggested users (non-friends) ---
    friend_ids = [f.friend_id for f in friends_qs]
    suggested_users = (
        User.objects.exclude(Q(id=request.user.id) | Q(id__in=friend_ids))[:5]
    )

    # --- Top stat: logs this month & total time overall ---
    logs_this_month = DailyLog.objects.filter(
        user=request.user, date__gte=month_start, date__lte=today
    ).count()

    # --- Mini calendar for current month ---
    import calendar
    cal = calendar.monthcalendar(today.year, today.month)
    logged_dates = set(
        DailyLog.objects.filter(
            user=request.user,
            date__year=today.year,
            date__month=today.month
        ).values_list("date", flat=True)
    )
    calendar_days = []
    for week in cal:
        for day in week:
            if day == 0:
                continue  # Empty day
            date_obj = timezone.datetime(today.year, today.month, day).date()
            calendar_days.append({
                "day": day,
                "logged": date_obj in logged_dates,
            })

    # Day names for calendar header
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # --- Optional: pending friend requests (for the small card on the right) ---
    # Only if you have a FriendRequest model with to_user/from_user and status='pending'
    pending_friend_requests = []
    # pending_friend_requests = (
    #     FriendRequest.objects.filter(to_user=request.user, status="pending")
    #     .select_related("from_user")
    #     .order_by("-created_at")
    # )

    # --- Star notifications count ---
    star_notifications_count = ActivityReaction.objects.filter(
        Q(task__user=request.user) | Q(daily_log__user=request.user)
    ).count()

    # --- Unread message count ---
    from .models import Conversation, ConversationMember, Message
    me = request.user
    conversations = Conversation.objects.filter(
        Q(user1=me) | Q(user2=me)
    ).select_related('user1', 'user2')
    
    unread_message_count = 0
    for conv in conversations:
        try:
            membership = ConversationMember.objects.get(conversation=conv, user=me)
            unread_qs = conv.messages.all()
            if membership.last_read_message_id:
                unread_qs = unread_qs.filter(id__gt=membership.last_read_message_id)
            unread_message_count += unread_qs.count()
        except ConversationMember.DoesNotExist:
            pass
    
    # --- Active plans with progress ---
    active_plans = Plan.objects.filter(user=request.user, is_active=True).order_by('-updated_at')
    
    # Annotate each plan with task counts
    plans_with_stats = []
    for plan in active_plans[:5]:  # Limit to 5 most recent
        total_tasks = plan.nodes.count()
        completed_tasks = plan.nodes.filter(task__status='completed').count()
        
        plan.total_tasks = total_tasks
        plan.completed_tasks = completed_tasks
        plans_with_stats.append(plan)

    context = {
        "today": today,
        "today_tasks_count": today_tasks_count,
        "today_completed": today_completed,
        "today_time": today_time,
        "pending_tasks": pending_tasks,
        "recent_logs": recent_logs,
        "friends": friends_activity,
        "total_friends": total_friends,
        "friends_timeline": friends_timeline,
        "suggested_users": suggested_users,
        "pending_friend_requests": pending_friend_requests,
        "star_notifications_count": star_notifications_count,
        "unread_message_count": unread_message_count,
        "active_plans": plans_with_stats,
        "logs_this_month": logs_this_month,
        "calendar_days": calendar_days,
        "day_names": day_names,
    }
    return render(request, "tracker/dashboard.html", context)

from django.db.models import Sum, Value
from django.db.models.functions import Coalesce

@login_required
def analytics(request):
    """Analytics page showing detailed statistics and charts."""

    # Get month/year from URL parameters or use current
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    # Validate month/year
    if month < 1 or month > 12:
        month = timezone.now().month
    if year < 2000 or year > 2100:
        year = timezone.now().year
    
    # Create date objects
    today = timezone.now().date()
    selected_month_start = timezone.datetime(year, month, 1).date()
    selected_month_end = (selected_month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # Use the last 7 days from today for weekly data (not affected by month selection)
    recent_log = DailyLog.objects.filter(user=request.user).order_by('-date').first()
    if recent_log:
        base_date = recent_log.date
    else:
        base_date = today
    week_ago = base_date - timedelta(days=6)

    # --- Key stats ---
    today_tasks = Task.objects.filter(user=request.user, created_at__date=today)
    today_tasks_count = today_tasks.count()
    completed_today = today_tasks.filter(status="completed").count()

    today_logs = DailyLog.objects.filter(user=request.user, date=today)
    today_time = today_logs.aggregate(total=Sum("duration"))["total"] or 0

    logs_this_month = DailyLog.objects.filter(
        user=request.user, date__gte=selected_month_start, date__lte=selected_month_end
    ).count()

    total_time = (
        DailyLog.objects.filter(user=request.user).aggregate(total=Sum("duration"))[
            "total"
        ]
        or 0
    )

    # --- Trend calculations ---
    # Yesterday's task count for trend
    yesterday = today - timedelta(days=1)
    yesterday_tasks_count = Task.objects.filter(
        user=request.user, created_at__date=yesterday
    ).count()
    
    if yesterday_tasks_count > 0:
        tasks_trend = ((today_tasks_count - yesterday_tasks_count) / yesterday_tasks_count) * 100
    else:
        tasks_trend = 100 if today_tasks_count > 0 else 0
    
    # Last month's log count for trend
    last_month_start = (selected_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = selected_month_start - timedelta(days=1)
    logs_last_month = DailyLog.objects.filter(
        user=request.user, 
        date__gte=last_month_start, 
        date__lte=last_month_end
    ).count()
    
    if logs_last_month > 0:
        month_trend = ((logs_this_month - logs_last_month) / logs_last_month) * 100
    else:
        month_trend = 100 if logs_this_month > 0 else 0
    
    # Average daily minutes
    total_days = DailyLog.objects.filter(user=request.user).values('date').distinct().count()
    avg_daily_minutes = int(total_time / total_days) if total_days > 0 else 0

    # --- Current streak and best streak ---
    log_dates = (
        DailyLog.objects.filter(user=request.user, date__lte=today)
        .values_list("date", flat=True)
        .distinct()
        .order_by("-date")
    )
    log_dates_set = set(log_dates)

    streak = 0
    cursor = today
    while cursor in log_dates_set:
        streak += 1
        cursor = cursor - timedelta(days=1)

    current_streak = streak
    
    # Calculate best streak (all time)
    best_streak = 0
    current_temp_streak = 0
    all_log_dates = sorted(list(log_dates_set))
    
    for i, date_val in enumerate(all_log_dates):
        if i == 0:
            current_temp_streak = 1
        else:
            if (date_val - all_log_dates[i-1]).days == 1:
                current_temp_streak += 1
            else:
                best_streak = max(best_streak, current_temp_streak)
                current_temp_streak = 1
    best_streak = max(best_streak, current_temp_streak)

    # --- Weekly overview for line chart ---
    last_7_days = [base_date - timedelta(days=i) for i in range(6, -1, -1)]
    
    day_minutes = []
    for d in last_7_days:
        minutes = (
            DailyLog.objects.filter(user=request.user, date=d).aggregate(
                total=Sum("duration")
            )["total"]
            or 0
        )
        day_minutes.append((d, minutes))

    max_minutes = max((m for _, m in day_minutes), default=0) or 0

    weekly_overview = []
    if max_minutes > 0:
        for d, minutes in day_minutes:
            weekly_overview.append(
                {
                    "label": d.strftime("%a"),
                    "minutes": minutes,
                    "date": d,
                }
            )

    # --- Mini calendar with intensity levels ---
    import calendar
    cal = calendar.monthcalendar(year, month)
    
    # Get all logs for the month with their durations
    month_logs = DailyLog.objects.filter(
        user=request.user,
        date__year=year,
        date__month=month
    ).values('date').annotate(total_minutes=Sum('duration'))
    
    # Create a dictionary of date -> minutes
    date_minutes_map = {log['date']: log['total_minutes'] for log in month_logs}
    
    # Calculate intensity levels (1-5) based on minutes
    all_minutes = list(date_minutes_map.values())
    if all_minutes:
        max_minutes_month = max(all_minutes)
        min_minutes_month = min(all_minutes)
    else:
        max_minutes_month = 0
        min_minutes_month = 0
    
    calendar_days = []
    for week in cal:
        for day in week:
            if day == 0:
                continue
            date_obj = timezone.datetime(year, month, day).date()
            minutes = date_minutes_map.get(date_obj, 0)
            
            # Calculate intensity (1-5)
            intensity = 0
            if minutes > 0:
                if max_minutes_month > min_minutes_month:
                    normalized = (minutes - min_minutes_month) / (max_minutes_month - min_minutes_month)
                    intensity = max(1, min(5, int(normalized * 5) + 1))
                else:
                    intensity = 3  # Default to medium if all values are the same
            
            calendar_days.append({
                "day": day,
                "date": date_obj,
                "logged": minutes > 0,
                "is_today": date_obj == today,
                "is_future": date_obj > today,
                "minutes": minutes,
                "intensity": intensity,
            })

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    category_queryset = (
        DailyLog.objects.filter(user=request.user, date__gte=week_ago, date__lte=today)
        .values(name=Coalesce('category__name', 'task__category__name', Value('Uncategorized')))
        .annotate(total=Sum('duration'))
        .order_by('-total')
    )
    category_data = [{'name': row['name'], 'value': row['total']} for row in category_queryset]

    # --- Productivity Insights (after category_data is defined) ---
    # Best day of the week (most productive)
    best_day = None
    if log_dates_set:
        # Get last 8 weeks of data
        eight_weeks_ago = today - timedelta(days=56)
        recent_logs = DailyLog.objects.filter(
            user=request.user,
            date__gte=eight_weeks_ago,
            date__lte=today
        ).values('date').annotate(total_minutes=Sum('duration'))
        
        # Group by day of week
        day_totals = {i: [] for i in range(7)}  # 0=Monday, 6=Sunday
        for log in recent_logs:
            day_of_week = log['date'].weekday()
            day_totals[day_of_week].append(log['total_minutes'])
        
        # Calculate average for each day
        day_averages = {}
        for day, minutes_list in day_totals.items():
            if minutes_list:
                day_averages[day] = sum(minutes_list) / len(minutes_list)
        
        if day_averages:
            best_day_num = max(day_averages, key=day_averages.get)
            best_day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            best_day = {
                'name': best_day_names[best_day_num],
                'minutes': int(day_averages[best_day_num])
            }
    
    # Most productive category
    most_productive_category = None
    if category_data:
        most_productive_category = max(category_data, key=lambda x: x['value'])
    
    # Weekly completion rate
    completion_rate_week = 0
    week_tasks = Task.objects.filter(
        user=request.user,
        created_at__date__gte=week_ago,
        created_at__date__lte=today
    )
    week_tasks_count = week_tasks.count()
    week_completed = week_tasks.filter(status="completed").count()
    
    if week_tasks_count > 0:
        completion_rate_week = int((week_completed / week_tasks_count) * 100)

    # --- Task breakdown for weekly period ---
    task_queryset = (
        DailyLog.objects.filter(user=request.user, date__gte=week_ago, date__lte=today)
        .values('task__title')
        .annotate(total=Sum('duration'))
        .order_by('-total')[:10]  # Show top 10 tasks
    )
    task_labels = [item['task__title'] or 'No Task' for item in task_queryset]
    task_values = [item['total'] for item in task_queryset]
    
    # Create combined task data for template
    task_data = [
        {'name': label, 'value': value} 
        for label, value in zip(task_labels, task_values)
    ]

    # --- Plan statistics ---
    total_plans = Plan.objects.filter(user=request.user).count()
    active_plans_count = Plan.objects.filter(user=request.user, is_active=True).count()
    
    # Get plan progress data
    plan_stats = []
    plans = Plan.objects.filter(user=request.user, is_active=True).order_by('-updated_at')[:5]
    
    for plan in plans:
        total_tasks = plan.nodes.count()
        completed_tasks = plan.nodes.filter(task__status='completed').count()
        in_progress_tasks = plan.nodes.filter(task__status='in_progress').count()
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        plan_stats.append({
            'id': plan.pk,
            'title': plan.title,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completion_rate': int(completion_rate),
        })
    
    # --- Week time (total minutes this week) ---
    week_time = DailyLog.objects.filter(
        user=request.user, date__gte=week_ago, date__lte=today
    ).aggregate(total=Sum('duration'))['total'] or 0
    
    # --- Best performing day (highest activity in last 30 days) ---
    best_day_info = None
    thirty_days_ago = today - timedelta(days=30)
    daily_activity = DailyLog.objects.filter(
        user=request.user,
        date__gte=thirty_days_ago,
        date__lte=today
    ).values('date').annotate(total_minutes=Sum('duration')).order_by('-total_minutes').first()
    
    if daily_activity:
        best_day_info = {
            'date': daily_activity['date'],
            'minutes': daily_activity['total_minutes']
        }

    # Handle AJAX requests for calendar updates
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'calendar_days': calendar_days,
            'day_names': day_names,
            'selected_year': year,
            'selected_month': month,
            'month_name': calendar.month_name[month],
            'prev_month': month - 1 if month > 1 else 12,
            'prev_year': year if month > 1 else year - 1,
            'next_month': month + 1 if month < 12 else 1,
            'next_year': year if month < 12 else year + 1,
            'logs_this_month': logs_this_month,
        })

    context = {
        "today": today,
        "today_tasks_count": today_tasks_count,
        "completed_today": completed_today,
        "today_time": today_time,
        "logs_this_month": logs_this_month,
        "total_time": total_time,
        "current_streak": current_streak,
        "weekly_overview": weekly_overview,
        "calendar_days": calendar_days,
        "day_names": day_names,
        "category_data": category_data,
        "task_data": task_data,
        "selected_year": year,
        "selected_month": month,
        "month_name": calendar.month_name[month],
        "prev_month": month - 1 if month > 1 else 12,
        "prev_year": year if month > 1 else year - 1,
        "next_month": month + 1 if month < 12 else 1,
        "next_year": year if month < 12 else year + 1,
        "total_plans": total_plans,
        "active_plans": active_plans_count,
        "plan_stats": plan_stats,
        # New trend and insights data
        "tasks_trend": round(tasks_trend, 1),
        "month_trend": round(month_trend, 1),
        "logs_last_month": logs_last_month,
        "avg_daily_minutes": avg_daily_minutes,
        "best_streak": best_streak,
        "best_day": best_day,
        "most_productive_category": most_productive_category,
        "completion_rate_week": completion_rate_week,
        "week_time": week_time,
        "best_day_info": best_day_info,
    }
    return render(request, "tracker/analytics.html", context)

# Task views
@login_required
def task_list(request):
    """List all tasks with filtering and pagination"""
    status_filter = request.GET.get('status', 'all')
    priority_filter = request.GET.get('priority', '')
    search_query = request.GET.get('search', '').strip()
    
    # Get only user's own tasks (exclude global default tasks)
    tasks = Task.objects.filter(user=request.user).select_related('category')
    
    # Apply status filter
    if status_filter != 'all':
        tasks = tasks.filter(status=status_filter)
    
    # Apply priority filter
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    
    # Apply search filter
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Order by priority and due date
    tasks = tasks.order_by(
        Case(
            When(priority='high', then=Value(1)),
            When(priority='medium', then=Value(2)),
            When(priority='low', then=Value(3)),
            default=Value(4)
        ),
        'due_date',
        '-created_at'
    )
    
    # Pagination - 20 tasks per page
    paginator = Paginator(tasks, 20)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.get_page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.get_page(1)
    
    context = {
        'tasks': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'search_query': search_query,
        'total_tasks': paginator.count,
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
            
            # Check if this is from a plan (AJAX request with plan_id)
            plan_id = request.POST.get('plan_id')
            if plan_id and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                try:
                    plan = Plan.objects.get(pk=plan_id, user=request.user)
                    
                    # Get position from form data
                    position_x = int(request.POST.get('position_x', 0))
                    position_y = int(request.POST.get('position_y', 0))
                    
                    # Create PlanNode with position
                    node = PlanNode.objects.create(
                        plan=plan,
                        task=task,
                        position_x=position_x,
                        position_y=position_y,
                        order=plan.nodes.count()
                    )
                    return JsonResponse({
                        'ok': True,
                        'task_id': task.pk,
                        'node_id': node.pk,
                        'message': 'Task created and added to plan'
                    })
                except Plan.DoesNotExist:
                    return JsonResponse({'ok': False, 'error': 'Plan not found'}, status=404)
            
            return redirect('task_list')
        else:
            # Return form errors for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': False,
                    'errors': form.errors
                }, status=400)
    else:
        form = TaskForm(user=request.user)
    
    return render(request, 'tracker/task_form.html', {'form': form, 'title': 'Add New Task'})

@login_required
def task_update(request, pk):
    """Update an existing task"""
    task = get_object_or_404(Task, pk=pk, user=request.user)
    
    # Prevent editing of global tasks that are marked as non-editable
    if hasattr(task, 'is_global') and task.is_global and not task.is_editable:
        messages.error(request, f"Cannot edit '{task.title}'. This is a global default task that cannot be modified.")
        return redirect('task_list')
    
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
    
    # Prevent deletion of global tasks that are marked as non-deletable
    if hasattr(task, 'is_global') and task.is_global and not task.is_deletable:
        messages.error(request, f"Cannot delete '{task.title}'. This is a global default task that cannot be removed.")
        return redirect('task_list')
    
    # Prevent deletion of the default task (legacy check)
    if task.title == 'General Activity':
        messages.error(request, "Cannot delete the default 'General Activity' task. It's required for time tracking.")
        return redirect('task_list')
    
    if request.method == 'POST':
        task.delete()
        messages.success(request, f"Task '{task.title}' has been deleted.")
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
    logs = DailyLog.objects.filter(user=request.user).select_related("category", "task").order_by("-date", "-id")

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
        form = DailyLogForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                log = form.save(commit=False)
                log.user = request.user
                # Ensure category is set from task if task has a category
                if log.task and log.task.category:
                    log.category = log.task.category
                log.save()
                messages.success(request, "Activity logged successfully!")
                return redirect("log_list")
            except Exception as e:
                logger.error(f"Error saving daily log for user {request.user.id}: {str(e)}")
                messages.error(request, "An error occurred while saving your log. Please try again.")
    else:
        # Check for task parameter to pre-select
        initial_data = {}
        task_id = request.GET.get('task')
        
        if task_id:
            try:
                task = Task.objects.get(id=task_id, user=request.user)
                initial_data['task'] = task.id
                # Also pre-fill category if task has one
                if task.category:
                    initial_data['category'] = task.category.id
            except Task.DoesNotExist:
                messages.warning(request, "The specified task was not found.")
            except ValueError:
                logger.warning(f"Invalid task_id parameter: {task_id}")
        else:
            # If no task specified, use default task
            default_task = Task.objects.filter(
                user=request.user, 
                title='General Activity'
            ).first()
            
            if default_task:
                initial_data['task'] = default_task.id
                if default_task.category:
                    initial_data['category'] = default_task.category.id
        
        form = DailyLogForm(user=request.user, initial=initial_data)
    return render(request, "tracker/log_form.html", {"form": form})

@login_required
def log_update(request, pk):
    log = get_object_or_404(DailyLog, pk=pk, user=request.user)
    if request.method == "POST":
        form = DailyLogForm(request.POST, instance=log, user=request.user)
        if form.is_valid():
            updated_log = form.save(commit=False)
            # Ensure category is set from task if task has a category
            if updated_log.task and updated_log.task.category:
                updated_log.category = updated_log.task.category
            updated_log.save()
            messages.success(request, "Activity updated successfully!")
            return redirect("log_list")
    else:
        form = DailyLogForm(instance=log, user=request.user)
    return render(request, "tracker/log_form.html", {"form": form})

@login_required
def quick_log_activity(request):
    """Quick log activity from day planner via AJAX."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            activity = data.get('activity')
            duration = data.get('duration', 30)  # Default 30 minutes
            
            if not activity:
                return JsonResponse({'success': False, 'error': 'Activity name is required'}, status=400)
            
            # Get or create General Activity task
            general_task, _ = Task.objects.get_or_create(
                user=request.user,
                title='General Activity',
                defaults={'status': 'completed', 'is_global': True}
            )
            
            # Create the daily log
            log = DailyLog.objects.create(
                user=request.user,
                activity=activity,
                duration=duration,
                date=timezone.now().date(),
                task=general_task,
                category=general_task.category if general_task.category else None
            )
            
            return JsonResponse({
                'success': True,
                'log_id': log.id,
                'message': f'Logged: {activity}'
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error in quick_log_activity: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)

@login_required
def save_day_schedule(request):
    """Save day schedule for a specific date via AJAX."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            schedule_date = data.get('date')
            title = data.get('title', '')
            events_data = data.get('events', [])
            
            if not schedule_date:
                return JsonResponse({'success': False, 'error': 'Date is required'}, status=400)
            
            # Update or create the schedule
            schedule, created = DaySchedule.objects.update_or_create(
                user=request.user,
                date=schedule_date,
                defaults={
                    'title': title,
                    'events_data': events_data
                }
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Schedule saved successfully',
                'schedule_id': schedule.id
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error in save_day_schedule: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)

@login_required
def load_day_schedule(request, schedule_date):
    """Load day schedule for a specific date via AJAX."""
    try:
        # Get manually created schedule events
        try:
            schedule = DaySchedule.objects.get(user=request.user, date=schedule_date)
            manual_events = schedule.events_data
            title = schedule.title
        except DaySchedule.DoesNotExist:
            manual_events = []
            title = ''
        
        # Get calendar events from DailyLog for this date (synced from iCloud/Google Calendar)
        calendar_logs = DailyLog.objects.filter(
            user=request.user,
            date=schedule_date,
            description__icontains='Calendar'  # Events synced from calendar have "Calendar" in description
        ).select_related('category', 'task')
        
        # Convert DailyLog entries to event format
        calendar_events = []
        current_time_minutes = 0  # Stack events starting from midnight
        
        for log in calendar_logs:
            # Calculate start and end times (stack them sequentially)
            start_min = current_time_minutes
            end_min = start_min + log.duration
            current_time_minutes = end_min
            
            # Build plan names from task if available
            plan_names = []
            if log.task and hasattr(log.task, 'plan_name'):
                plan_names = [log.task.plan_name] if log.task.plan_name else []
            
            calendar_events.append({
                'id': f'cal_{log.id}',  # Prefix to distinguish from manual events
                'title': f"📅 {log.activity}",  # Add calendar emoji to distinguish
                'startMin': start_min,
                'endMin': end_min,
                'logged': True,  # Calendar events are already logged
                'planNames': plan_names,
                'isCalendarEvent': True,  # Flag to identify calendar events
                'source': 'calendar'
            })
        
        # Combine manual events with calendar events
        all_events = manual_events + calendar_events
        
        return JsonResponse({
            'success': True,
            'date': schedule_date,
            'title': title,
            'events': all_events
        })
        
    except Exception as e:
        logger.error(f"Error in load_day_schedule: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

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
@rate_limit(requests_per_minute=10)  # Limit friend requests to prevent spam
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
@rate_limit(requests_per_minute=20)
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
@rate_limit(requests_per_minute=20)
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
@rate_limit(requests_per_minute=10)
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
        
        # Calculate activity percentage based on logs in the past week
        # Assuming target is at least 1 log per day = 7 logs per week
        logs_count = DailyLog.objects.filter(
            user=friend,
            date__gte=week_ago
        ).count()
        
        # Calculate percentage: logs_count / 7 days * 100, capped at 100%
        activity_percent = min(100, int((logs_count / 7) * 100)) if logs_count > 0 else 0
        
        friends_data.append({
            'friend': friend,
            'friendship': friendship,
            'completed_tasks': completed_tasks,
            'total_time': total_time,
            'activity_percent': activity_percent,
        })
    
    context = {'friends_data': friends_data}
    return render(request, 'tracker/friends_list.html', context)


@login_required
def friends_feed(request):
    """View full friends activity feed"""
    friends_qs = Friendship.objects.filter(user=request.user).select_related('friend')
    friend_ids = [f.friend_id for f in friends_qs]
    friends_timeline = []
    
    # Create a mapping of friend_id to friendship_id for quick lookup
    friendship_map = {f.friend_id: f.id for f in friends_qs}
    
    # Get recent completed tasks from friends
    if friend_ids:
        recent_friend_tasks = Task.objects.filter(
            user_id__in=friend_ids,
            status="completed",
            completed_at__isnull=False
        ).select_related("user", "category").order_by("-completed_at")[:50]
        
        for task in recent_friend_tasks:
            # Get reaction info for this task
            star_count = ActivityReaction.objects.filter(task=task).count()
            user_starred = ActivityReaction.objects.filter(task=task, user=request.user).exists()
            
            friends_timeline.append({
                "type": "task",
                "user": task.user,
                "friendship_id": friendship_map.get(task.user_id),
                "title": task.title,
                "category": task.category,
                "timestamp": task.completed_at,
                "duration": None,
                "id": task.id,
                "star_count": star_count,
                "user_starred": user_starred,
            })
        
        # Get recent logs from friends
        recent_friend_logs = DailyLog.objects.filter(
            user_id__in=friend_ids
        ).select_related("user", "category").order_by("-date", "-id")[:50]
        
        for log in recent_friend_logs:
            # Get reaction info for this log
            star_count = ActivityReaction.objects.filter(daily_log=log).count()
            user_starred = ActivityReaction.objects.filter(daily_log=log, user=request.user).exists()
            
            # Create a datetime from the date for sorting
            timestamp = timezone.datetime.combine(log.date, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone())
            friends_timeline.append({
                "type": "log",
                "user": log.user,
                "friendship_id": friendship_map.get(log.user_id),
                "title": log.activity,
                "category": log.category,
                "timestamp": timestamp,
                "duration": log.duration,
                "id": log.id,
                "star_count": star_count,
                "user_starred": user_starred,
            })
        
        # Sort combined timeline by timestamp (most recent first)
        friends_timeline.sort(key=lambda x: x["timestamp"], reverse=True)
    
    context = {
        'friends_timeline': friends_timeline,
        'friends_count': len(friend_ids),
    }
    return render(request, 'tracker/friends_feed.html', context)


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
    category_queryset = DailyLog.objects.filter(
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

    for idx, item in enumerate(category_queryset):
        category_labels.append(item['category__name'] or 'Uncategorized')
        category_values.append(item['total'])

    category_data = {
        'labels': category_labels,
        'data': category_values,
        'colors': category_colors[:len(category_labels)]
    }

    tasks = friend.tasks.filter(status='completed').order_by('-completed_at')[:20]
    logs = friend.daily_logs.order_by('-date')[:20]

    context = {
        'friend': friend,
        'total_time': total_time,
        'total_tasks': total_tasks,
        'week_time': week_time,
        'week_tasks': week_tasks,
        'activity_streak': activity_streak,
        'weekly_data': json.dumps(weekly_data),
        'category_data': json.dumps(category_data),
        'tasks': tasks,
        'logs': logs,
    }
    return render(request, 'tracker/friend_progress_detail.html', context)

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
    logs = DailyLog.objects.filter(user=user).select_related('category', 'task').order_by('-date')[:20]
    
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

    # Create combined category data for template (consistent with task_data)
    category_data_list = [
        {'name': label, 'value': value} 
        for label, value in zip(category_labels, category_values)
    ]

    # Calculate total time for categories
    category_total_time = sum(category_values)

    # ===== TASK BREAKDOWN FOR WEEKLY PERIOD =====
    task_queryset = (
        DailyLog.objects.filter(user=friend, date__gte=week_ago, date__lte=today)
        .values('task__title')
        .annotate(total=Sum('duration'))
        .order_by('-total')[:10]  # Show top 10 tasks
    )
    task_labels = [item['task__title'] or 'No Task' for item in task_queryset]
    task_values = [item['total'] for item in task_queryset]
    
    # Create combined task data for template
    task_data = [
        {'name': label, 'value': value} 
        for label, value in zip(task_labels, task_values)
    ]

    # Calculate total time for tasks
    task_total_time = sum(task_values)

    # ===== MONTHLY STATS =====
    month_start = today.replace(day=1)
    logs_this_month = DailyLog.objects.filter(
        user=friend, date__gte=month_start, date__lte=today
    ).count()

    # ===== TODAY'S STATS =====
    today_tasks = Task.objects.filter(user=friend, created_at__date=today)
    today_tasks_count = today_tasks.count()
    completed_today = today_tasks.filter(status="completed").count()

    today_logs = DailyLog.objects.filter(user=friend, date=today)
    today_time = today_logs.aggregate(total=Sum("duration"))["total"] or 0

    # ===== CALENDAR DATA =====
    import calendar
    cal = calendar.monthcalendar(today.year, today.month)
    logged_dates = set(
        DailyLog.objects.filter(
            user=friend,
            date__year=today.year,
            date__month=today.month
        ).values_list("date", flat=True)
    )
    calendar_days = []
    for week in cal:
        for day in week:
            if day == 0:
                continue
            date_obj = timezone.datetime(today.year, today.month, day).date()
            calendar_days.append({
                "day": day,
                "date": date_obj,
                "logged": date_obj in logged_dates,
                "is_today": date_obj == today,
                "is_future": date_obj > today,
            })

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # ===== WEEKLY OVERVIEW FOR LINE CHART =====
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    
    labels = []
    data = []
    for d in last_7_days:
        minutes = (
            DailyLog.objects.filter(user=friend, date=d).aggregate(
                total=Sum("duration")
            )["total"]
            or 0
        )
        labels.append(d.strftime("%a"))
        data.append(minutes)

    weekly_overview = {
        'labels': labels,
        'data': data
    } if any(data) else None

    # ===== ACTIVE PLANS =====
    active_plans = Plan.objects.filter(
        user=friend,
        is_active=True
    ).prefetch_related('nodes__task')[:5]  # Show up to 5 active plans
    
    # Calculate progress for each plan
    plans_with_progress = []
    for plan in active_plans:
        nodes = plan.nodes.all()
        total_tasks = nodes.count()
        if total_tasks > 0:
            completed_tasks = sum(1 for node in nodes if node.task.status == 'completed')
            progress_percentage = int((completed_tasks / total_tasks) * 100)
            plans_with_progress.append({
                'plan': plan,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'progress_percentage': progress_percentage,
            })

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
        'category_data_list': category_data_list,
        'task_data': json.dumps(task_data),
        'category_total_time': category_total_time,
        'task_total_time': task_total_time,
        'day_names': day_names,
        'today': today,
        'today_tasks_count': today_tasks_count,
        'completed_today': completed_today,
        'today_time': today_time,
        'logs_this_month': logs_this_month,
        'weekly_overview': weekly_overview,
        'calendar_days': calendar_days,
        'month_name': calendar.month_name[today.month],
        'selected_year': today.year,
        'selected_month': today.month,
        'active_plans': plans_with_progress,
    }
    return render(request, 'tracker/friend_profile.html', context)


@login_required
@require_http_methods(["POST"])
@rate_limit(requests_per_minute=30)
@validate_ajax
@validate_json(required_fields=['activity_type', 'activity_id'])
@log_errors
def toggle_star_reaction(request):
    """Toggle star reaction on a friend's activity (task or log)"""
    data = request.json_data  # Already validated by decorator
    activity_type = data.get('activity_type')
    activity_id = data.get('activity_id')
    
    if activity_type == 'task':
        activity = get_object_or_404(Task, id=activity_id)
    elif activity_type == 'log':
        activity = get_object_or_404(DailyLog, id=activity_id)
    else:
        return JsonResponse({'error': 'Invalid activity type'}, status=400)
    
    # Check if user is friends with the activity owner
    if not Friendship.objects.filter(
        Q(user=request.user, friend=activity.user) | 
        Q(user=activity.user, friend=request.user)
    ).exists():
        return JsonResponse({'error': 'You can only react to friends\' activities'}, status=403)
    
    # Toggle the reaction
    if activity_type == 'task':
        reaction, created = ActivityReaction.objects.get_or_create(
            user=request.user,
            task=activity,
            defaults={'reaction_type': 'star'}
        )
    else:
        reaction, created = ActivityReaction.objects.get_or_create(
            user=request.user,
            daily_log=activity,
            defaults={'reaction_type': 'star'}
        )
    
    if not created:
        # If reaction already exists, remove it (unstar)
        reaction.delete()
        starred = False
    else:
        starred = True
    
    # Get updated star count
    if activity_type == 'task':
        star_count = ActivityReaction.objects.filter(task=activity).count()
    else:
        star_count = ActivityReaction.objects.filter(daily_log=activity).count()
    
    return JsonResponse({
        'starred': starred,
        'star_count': star_count
    })


@login_required
def daily_summary(request, year, month, day):
    """View detailed summary for a specific day"""
    try:
        selected_date = timezone.datetime(int(year), int(month), int(day)).date()
    except ValueError:
        # Invalid date, redirect to analytics
        return redirect('analytics')
    
    # Get all logs for this day
    day_logs = DailyLog.objects.filter(
        user=request.user,
        date=selected_date
    ).select_related('category').order_by('created_at')
    
    # Get tasks completed on this day
    completed_tasks = Task.objects.filter(
        user=request.user,
        status='completed',
        completed_at__date=selected_date
    ).select_related('category').order_by('completed_at')
    
    # Calculate totals
    total_time = day_logs.aggregate(total=Sum('duration'))['total'] or 0
    total_tasks = completed_tasks.count()
    total_logs = day_logs.count()
    
    # Category breakdown for this day
    category_breakdown = day_logs.values('category__name').annotate(
        total_time=Sum('duration'),
        log_count=Count('id')
    ).order_by('-total_time')
    
    # Navigation dates
    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    
    context = {
        'selected_date': selected_date,
        'day_logs': day_logs,
        'completed_tasks': completed_tasks,
        'total_time': total_time,
        'total_tasks': total_tasks,
        'total_logs': total_logs,
        'category_breakdown': category_breakdown,
        'prev_date': prev_date,
        'next_date': next_date,
        'has_prev': DailyLog.objects.filter(user=request.user, date=prev_date).exists() or Task.objects.filter(user=request.user, completed_at__date=prev_date).exists(),
        'has_next': DailyLog.objects.filter(user=request.user, date=next_date).exists() or Task.objects.filter(user=request.user, completed_at__date=next_date).exists(),
    }
    
    return render(request, 'tracker/daily_summary.html', context)


@login_required
def notifications(request):
    """View notifications for stars received and new messages from friends"""
    
    # Get all stars received by the current user
    # Stars on tasks
    task_stars = ActivityReaction.objects.filter(
        task__user=request.user
    ).select_related('user', 'task').order_by('-created_at')
    
    # Stars on daily logs
    log_stars = ActivityReaction.objects.filter(
        daily_log__user=request.user
    ).select_related('user', 'daily_log').order_by('-created_at')
    
    # Combine and sort by creation date
    all_stars = []
    
    for star in task_stars:
        all_stars.append({
            'type': 'task',
            'user': star.user,
            'activity': star.task.title,
            'timestamp': star.created_at,
            'activity_id': star.task.id,
        })
    
    for star in log_stars:
        all_stars.append({
            'type': 'log',
            'user': star.user,
            'activity': star.daily_log.activity,
            'timestamp': star.created_at,
            'activity_id': star.daily_log.id,
        })
    
    # Sort by timestamp (most recent first)
    all_stars.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Get total star count
    total_stars = len(all_stars)
    
    # Get unread messages from conversations
    from .models import Conversation, ConversationMember, Message
    unread_messages = []
    
    me = request.user
    # Get all conversations for the current user
    conversations = Conversation.objects.filter(
        Q(user1=me) | Q(user2=me)
    ).select_related('user1', 'user2').order_by('-updated_at')
    
    for conv in conversations:
        # Get the other user
        other = conv.user2 if conv.user1 == me else conv.user1
        
        # Get the membership record
        try:
            membership = ConversationMember.objects.get(conversation=conv, user=me)
            # Count unread messages
            unread_qs = conv.messages.all()
            if membership.last_read_message_id:
                unread_qs = unread_qs.filter(id__gt=membership.last_read_message_id)
            
            unread_count = unread_qs.count()
            
            if unread_count > 0:
                # Get the latest unread message
                latest_msg = unread_qs.order_by('-created_at').first()
                if latest_msg:
                    unread_messages.append({
                        'conversation_id': conv.id,
                        'other_user': other,
                        'unread_count': unread_count,
                        'latest_message': latest_msg.body,
                        'latest_timestamp': latest_msg.created_at,
                    })
        except ConversationMember.DoesNotExist:
            pass
    
    context = {
        'stars': all_stars,
        'total_stars': total_stars,
        'unread_messages': unread_messages,
        'total_unread_messages': len(unread_messages),
    }
    
    return render(request, 'tracker/notifications.html', context)


def about(request):
    """About page for VisMatrix company information."""
    return render(request, 'tracker/about.html')


def privacy_policy(request):
    """Privacy policy page."""
    return render(request, 'tracker/privacy_policy.html')


def terms_of_service(request):
    """Terms of service page."""
    return render(request, 'tracker/terms_of_service.html')


from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Conversation, ConversationMember, Message, Friendship
from .services import are_friends

@login_required
def inbox(request):
    me = request.user
    conversations = Conversation.objects.filter(Q(user1=me) | Q(user2=me)).order_by("-updated_at")

    memberships = {m.conversation_id: m for m in ConversationMember.objects.filter(user=me, conversation__in=conversations)}

    items = []
    for c in conversations:
        m = memberships.get(c.id)
        other = c.other_user(me)
        last = c.last_message()
        items.append({
            "conversation": c,
            "other": other,
            "last": last,
            "unread": m.unread_count() if m else 0,
        })

    return render(request, "messaging/inbox.html", {"items": items})


@login_required
def start_chat(request, username):
    me = request.user
    other = get_object_or_404(User, username=username)

    if other == me:
        raise Http404("Cannot message yourself.")

    if not are_friends(me, other):
        raise Http404("You can only message friends.")

    conv, created = Conversation.get_or_create_between(me, other)

    # Ensure member rows exist
    ConversationMember.objects.get_or_create(conversation=conv, user=conv.user1)
    ConversationMember.objects.get_or_create(conversation=conv, user=conv.user2)

    return redirect("conversation_detail", conversation_id=conv.id)


@login_required
def conversation_detail(request, conversation_id):
    me = request.user
    conv = get_object_or_404(
        Conversation.objects.select_related("user1", "user2"),
        id=conversation_id
    )

    if me.id not in (conv.user1_id, conv.user2_id):
        raise Http404("Not your conversation.")

    # membership exists
    membership, _ = ConversationMember.objects.get_or_create(conversation=conv, user=me)

    # Handle send
    if request.method == "POST":
        body = (request.POST.get("body") or "").strip()
        if body:
            Message.objects.create(conversation=conv, sender=me, body=body)
            conv.updated_at = timezone.now()
            conv.save(update_fields=["updated_at"])

        return redirect("conversation_detail", conversation_id=conv.id)

    # Mark as read (set last read to latest message)
    latest = conv.messages.order_by("-created_at").first()
    if latest:
        membership.last_read_message = latest
        membership.last_read_at = timezone.now()
        membership.save(update_fields=["last_read_message", "last_read_at"])

    # Fetch messages
    # (optional soft-delete filtering)
    qs = conv.messages.all()
    if conv.user1_id == me.id:
        qs = qs.exclude(deleted_for_sender=True, sender=me)
    else:
        qs = qs.exclude(deleted_for_sender=True, sender=me)

    return render(
        request,
        "messaging/conversation_detail.html",
        {
            "conversation": conv,
            "other": conv.other_user(me),
            "messages": qs,
            "unread": membership.unread_count(),
        },
    )



from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Conversation, ConversationMember, Message, Friendship
from django.contrib.auth.models import User
from .services import are_friends

@login_required
def mini_chat_friends(request):
    """
    Returns a friends list + unread counts for the mini widget.
    """
    me = request.user

    # all friends (bidirectional friendship already stored in your model)
    friends = User.objects.filter(friends_of__user=me).distinct().order_by("username")

    # fetch conversations for unread counts
    convs = Conversation.objects.filter(user1=me) | Conversation.objects.filter(user2=me)
    convs = convs.distinct()

    memberships = {
        m.conversation_id: m
        for m in ConversationMember.objects.filter(user=me, conversation__in=convs)
    }

    # map other_user_id -> conv_id
    conv_map = {}
    for c in convs:
        other = c.other_user(me)
        conv_map[other.id] = c.id

    payload = []
    for f in friends:
        conv_id = conv_map.get(f.id)
        unread = 0
        if conv_id and conv_id in memberships:
            unread = memberships[conv_id].unread_count()

        payload.append({
            "id": f.id,
            "username": f.username,
            "conversation_id": conv_id,  # may be null if never chatted
            "unread": unread,
        })

    return JsonResponse({"friends": payload})


@login_required
def mini_chat_messages(request, conversation_id):
    """
    Returns the last N messages for a conversation and marks as read.
    """
    me = request.user
    conv = get_object_or_404(Conversation.objects.select_related("user1", "user2"), id=conversation_id)

    if me.id not in (conv.user1_id, conv.user2_id):
        raise Http404("Not your conversation.")

    # last 30 messages
    msgs = list(conv.messages.order_by("-created_at")[:30])[::-1]

    # mark read (set pointer to latest)
    membership, _ = ConversationMember.objects.get_or_create(conversation=conv, user=me)
    latest = msgs[-1] if msgs else None
    if latest:
        membership.last_read_message = latest
        membership.last_read_at = timezone.now()
        membership.save(update_fields=["last_read_message", "last_read_at"])

    return JsonResponse({
        "conversation": conv.id,
        "other": conv.other_user(me).username,
        "messages": [
            {
                "id": m.id,
                "sender": m.sender.username,
                "is_me": (m.sender_id == me.id),
                "body": m.body,
                "created_at": m.created_at.strftime("%b %d, %I:%M %p"),
            } for m in msgs
        ]
    })


@login_required
def mini_chat_send(request, conversation_id):
    """
    POST JSON: { "body": "..." }
    Creates a message.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    me = request.user
    conv = get_object_or_404(Conversation.objects.select_related("user1", "user2"), id=conversation_id)

    if me.id not in (conv.user1_id, conv.user2_id):
        raise Http404("Not your conversation.")

    # Basic JSON parsing
    import json
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    body = (data.get("body") or "").strip()
    if not body:
        return JsonResponse({"error": "Empty message"}, status=400)

    msg = Message.objects.create(conversation=conv, sender=me, body=body)
    conv.updated_at = timezone.now()
    conv.save(update_fields=["updated_at"])

    return JsonResponse({
        "ok": True,
        "message": {
            "id": msg.id,
            "sender": msg.sender.username,
            "is_me": True,
            "body": msg.body,
            "created_at": msg.created_at.strftime("%b %d, %I:%M %p"),
        }
    })


@login_required
def mini_chat_start(request, friend_id):
    """
    POST JSON: { "body": "..." }
    Creates a conversation (if needed) with friend_id and sends the first message.
    Returns the conversation_id and message data.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    me = request.user
    friend = get_object_or_404(User, id=friend_id)

    # Verify they're actually friends
    if not are_friends(me, friend):
        return JsonResponse({"error": "Not friends"}, status=403)

    # Get or create conversation
    conv, created = Conversation.get_or_create_between(me, friend)

    # Basic JSON parsing
    import json
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    body = (data.get("body") or "").strip()
    if not body:
        return JsonResponse({"error": "Empty message"}, status=400)

    msg = Message.objects.create(conversation=conv, sender=me, body=body)
    conv.updated_at = timezone.now()
    conv.save(update_fields=["updated_at"])

    return JsonResponse({
        "ok": True,
        "conversation_id": conv.id,
        "message": {
            "id": msg.id,
            "sender": msg.sender.username,
            "is_me": True,
            "body": msg.body,
            "created_at": msg.created_at.strftime("%b %d, %I:%M %p"),
        }
    })


# ===== PLAN VIEWS =====

@login_required
def plan_list(request):
    """Display all plans for the logged-in user"""
    plans = Plan.objects.filter(user=request.user).prefetch_related('nodes__task')
    
    # Add completion statistics to each plan
    plans_with_stats = []
    for plan in plans:
        total_nodes = plan.nodes.count()
        completed_nodes = plan.nodes.filter(task__status='completed').count()
        plan.total_tasks = total_nodes
        plan.completed_tasks = completed_nodes
        plans_with_stats.append(plan)
    
    return render(request, 'tracker/plan_list.html', {'plans': plans_with_stats})


@login_required
def plan_create(request):
    """Create a new plan"""
    if request.method == 'POST':
        form = PlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.user = request.user
            plan.save()
            messages.success(request, f'Plan created successfully! (Active: {plan.is_active})')
            return redirect('plan_detail', pk=plan.pk)
    else:
        form = PlanForm(initial={'is_active': True})
    return render(request, 'tracker/plan_form.html', {'form': form, 'action': 'Create'})


@login_required
def plan_detail(request, pk):
    """Display plan details with DAG visualization"""
    plan = get_object_or_404(Plan, pk=pk, user=request.user)
    nodes = plan.nodes.all().select_related('task').prefetch_related('dependencies', 'dependents')
    
    # Calculate statistics
    total_nodes = nodes.count()
    completed_nodes = nodes.filter(task__status='completed').count()
    in_progress_nodes = nodes.filter(task__status='in_progress').count()
    pending_nodes = nodes.filter(task__status='pending').count()
    
    # Prepare node data for visualization
    nodes_data = []
    for node in nodes:
        nodes_data.append({
            'id': node.id,
            'task_id': node.task.id,
            'task_title': node.task.title,
            'task_description': node.task.description[:100] if node.task.description else '',
            'task_status': node.task.status,
            'task_priority': node.task.priority,
            'can_start': node.can_start(),
            'position_x': node.position_x,
            'position_y': node.position_y,
            'dependencies': [dep.id for dep in node.dependencies.all()],
            'dependents': [dep.id for dep in node.dependents.all()],
        })
    
    # Get user's categories and global categories for the modal
    categories = Category.objects.filter(
        Q(user=request.user) | Q(is_global=True)
    ).order_by('-is_global', 'name')
    
    context = {
        'plan': plan,
        'nodes': nodes,
        'nodes_data': json.dumps(nodes_data),
        'total_nodes': total_nodes,
        'completed_nodes': completed_nodes,
        'in_progress_nodes': in_progress_nodes,
        'pending_nodes': pending_nodes,
        'categories': categories
    }
    return render(request, 'tracker/plan_detail.html', context)


@login_required
def plan_update(request, pk):
    """Update plan details"""
    plan = get_object_or_404(Plan, pk=pk, user=request.user)
    if request.method == 'POST':
        form = PlanForm(request.POST, instance=plan)
        if form.is_valid():
            updated_plan = form.save()
            status_msg = 'active' if updated_plan.is_active else 'inactive'
            messages.success(request, f'Plan updated successfully! (Status: {status_msg})')
            return redirect('plan_detail', pk=plan.pk)
    else:
        form = PlanForm(instance=plan)
    return render(request, 'tracker/plan_form.html', {'form': form, 'action': 'Update', 'plan': plan})


@login_required
def plan_delete(request, pk):
    """Delete a plan"""
    plan = get_object_or_404(Plan, pk=pk, user=request.user)
    if request.method == 'POST':
        plan.delete()
        messages.success(request, 'Plan deleted successfully!')
        return redirect('plan_list')
    return render(request, 'tracker/plan_confirm_delete.html', {'plan': plan})


@login_required
def plan_node_add(request, plan_pk):
    """Add a task node to a plan"""
    plan = get_object_or_404(Plan, pk=plan_pk, user=request.user)
    
    if request.method == 'POST':
        form = PlanNodeForm(request.POST, user=request.user, plan=plan)
        if form.is_valid():
            node = form.save(commit=False)
            node.plan = plan
            
            # Check if task already in plan
            if PlanNode.objects.filter(plan=plan, task=node.task).exists():
                messages.error(request, 'This task is already in the plan!')
                return render(request, 'tracker/plan_node_form.html', {
                    'form': form,
                    'plan': plan,
                    'action': 'Add'
                })
            
            node.save()
            form.save_m2m()  # Save dependencies
            
            # Validate DAG after adding
            if not plan.validate_dag():
                node.delete()
                messages.error(request, 'Adding this node would create a cycle! Please adjust dependencies.')
                return render(request, 'tracker/plan_node_form.html', {
                    'form': form,
                    'plan': plan,
                    'action': 'Add'
                })
            
            messages.success(request, f'Task "{node.task.title}" added to plan!')
            return redirect('plan_detail', pk=plan.pk)
    else:
        form = PlanNodeForm(user=request.user, plan=plan)
    
    return render(request, 'tracker/plan_node_form.html', {
        'form': form,
        'plan': plan,
        'action': 'Add'
    })


@login_required
def plan_node_update(request, pk):
    """Update a plan node's dependencies"""
    node = get_object_or_404(PlanNode, pk=pk, plan__user=request.user)
    plan = node.plan
    
    if request.method == 'POST':
        form = PlanNodeForm(request.POST, instance=node, user=request.user, plan=plan)
        if form.is_valid():
            # Save current dependencies for rollback
            old_deps = list(node.dependencies.all())
            
            form.save()
            
            # Validate DAG after update
            if not plan.validate_dag():
                # Rollback
                node.dependencies.set(old_deps)
                messages.error(request, 'This change would create a cycle! Please adjust dependencies.')
                return render(request, 'tracker/plan_node_form.html', {
                    'form': form,
                    'plan': plan,
                    'node': node,
                    'action': 'Update'
                })
            
            messages.success(request, 'Node updated successfully!')
            return redirect('plan_detail', pk=plan.pk)
    else:
        form = PlanNodeForm(instance=node, user=request.user, plan=plan)
    
    return render(request, 'tracker/plan_node_form.html', {
        'form': form,
        'plan': plan,
        'node': node,
        'action': 'Update'
    })


@login_required
def plan_node_delete(request, pk):
    """Remove a node from a plan"""
    node = get_object_or_404(PlanNode, pk=pk, plan__user=request.user)
    plan = node.plan
    
    if request.method == 'POST':
        node.delete()
        messages.success(request, 'Task removed from plan!')
        return redirect('plan_detail', pk=plan.pk)
    
    return render(request, 'tracker/plan_node_confirm_delete.html', {'node': node, 'plan': plan})


@login_required
def plan_node_add_dependency(request, pk):
    """AJAX endpoint to add a dependency between nodes"""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)
    
    node = get_object_or_404(PlanNode, pk=pk, plan__user=request.user)
    plan = node.plan
    
    try:
        import json
        data = json.loads(request.body)
        dependency_id = data.get('dependency_id')
        
        if not dependency_id:
            return JsonResponse({'ok': False, 'error': 'dependency_id required'})
        
        # Get the dependency node and ensure it's in the same plan
        dep_node = get_object_or_404(PlanNode, pk=dependency_id, plan=plan)
        
        # Check if dependency already exists
        if node.dependencies.filter(pk=dep_node.pk).exists():
            return JsonResponse({'ok': False, 'error': 'Dependency already exists'})
        
        # Check if adding would create a cycle
        if dep_node.dependencies.filter(pk=node.pk).exists():
            return JsonResponse({'ok': False, 'error': 'This would create a circular dependency'})
        
        # Save old dependencies for rollback
        old_deps = list(node.dependencies.all())
        
        # Add the dependency
        node.dependencies.add(dep_node)
        
        # Validate DAG
        if not plan.validate_dag():
            # Rollback
            node.dependencies.set(old_deps)
            return JsonResponse({'ok': False, 'error': 'This would create a cycle in the plan'})
        
        return JsonResponse({'ok': True, 'message': 'Dependency added successfully'})
        
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def plan_node_update_position(request, pk):
    """Update node position for visualization (AJAX)"""
    node = get_object_or_404(PlanNode, pk=pk, plan__user=request.user)
    
    try:
        data = json.loads(request.body)
        node.position_x = data.get('x', node.position_x)
        node.position_y = data.get('y', node.position_y)
        node.save(update_fields=['position_x', 'position_y'])
        
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


# ================= Plan Sharing =================

@login_required
@require_http_methods(["POST"])
def plan_toggle_sharing(request, pk):
    """Toggle plan sharing and generate share token if needed"""
    plan = get_object_or_404(Plan, pk=pk, user=request.user)
    
    try:
        data = json.loads(request.body)
        is_public = data.get('is_public', False)
        
        plan.is_public = is_public
        if is_public and not plan.share_token:
            plan.generate_share_token()
        plan.save()
        
        share_url = plan.get_share_url(request) if plan.is_public else None
        
        return JsonResponse({
            'ok': True,
            'is_public': plan.is_public,
            'share_token': plan.share_token,
            'share_url': share_url
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def plan_regenerate_token(request, pk):
    """Regenerate share token for a plan"""
    plan = get_object_or_404(Plan, pk=pk, user=request.user)
    
    try:
        import secrets
        plan.share_token = secrets.token_urlsafe(32)
        plan.save()
        
        share_url = plan.get_share_url(request) if plan.is_public else None
        
        return JsonResponse({
            'ok': True,
            'share_token': plan.share_token,
            'share_url': share_url
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


def shared_plan_view(request, token):
    """Public view for shared plans (no authentication required)"""
    plan = get_object_or_404(Plan, share_token=token, is_public=True)
    nodes = plan.nodes.all().select_related('task').prefetch_related('dependencies', 'dependents')
    
    # Calculate statistics
    total_nodes = nodes.count()
    completed_nodes = nodes.filter(task__status='completed').count()
    in_progress_nodes = nodes.filter(task__status='in_progress').count()
    pending_nodes = nodes.filter(task__status='pending').count()
    
    # Prepare node data for visualization
    nodes_data = []
    for node in nodes:
        nodes_data.append({
            'id': node.id,
            'task_id': node.task.id,
            'task_title': node.task.title,
            'task_description': node.task.description[:100] if node.task.description else '',
            'task_status': node.task.status,
            'task_priority': node.task.priority,
            'can_start': node.can_start(),
            'position_x': node.position_x,
            'position_y': node.position_y,
            'dependencies': [dep.id for dep in node.dependencies.all()],
            'dependents': [dep.id for dep in node.dependents.all()],
        })
    
    context = {
        'plan': plan,
        'nodes': nodes,
        'nodes_data': json.dumps(nodes_data),
        'total_nodes': total_nodes,
        'completed_nodes': completed_nodes,
        'in_progress_nodes': in_progress_nodes,
        'pending_nodes': pending_nodes,
        'is_shared_view': True,  # Flag to show read-only view
        'owner': plan.user,
    }
    return render(request, 'tracker/shared_plan.html', context)


# ============================================================================
# Google Calendar Integration Views
# ============================================================================

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from .models import GoogleCalendarIntegration, ICloudCalendarIntegration
from .calendar_service import GoogleCalendarService
from django.conf import settings

# OAuth2 Configuration
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


@login_required
def calendar_settings(request):
    """Calendar integration settings page - supports Google and iCloud calendars"""
    try:
        google_integration = GoogleCalendarIntegration.objects.get(user=request.user)
    except GoogleCalendarIntegration.DoesNotExist:
        google_integration = None
    
    try:
        icloud_integration = ICloudCalendarIntegration.objects.get(user=request.user)
    except ICloudCalendarIntegration.DoesNotExist:
        icloud_integration = None
    
    # Get all categories for default category selection
    categories = Category.objects.filter(
        Q(user=request.user) | Q(is_global=True)
    ).order_by('-is_global', 'name')
    
    context = {
        'google_integration': google_integration,
        'icloud_integration': icloud_integration,
        'categories': categories,
        'google_configured': bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
    }
    
    return render(request, 'tracker/calendar_settings_minimal.html', context)


@login_required
def profile_settings(request):
    """User profile settings page for editing display name"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('profile_settings')
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'tracker/profile_settings.html', context)


@login_required
def calendar_connect(request):
    """Initiate OAuth2 flow for Google Calendar"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        messages.error(request, "Google Calendar integration is not configured. Please contact administrator.")
        return redirect('calendar_settings')
    
    print(f"DEBUG connect: User {request.user.username} (id: {request.user.id}) starting OAuth")
    print(f"DEBUG connect: Session key before: {request.session.session_key}")
    
    # Create OAuth2 flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    
    # Generate authorization URL with custom state including user_id
    import json
    import base64
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force consent screen to get refresh token
    )
    
    # Encode user_id into the state parameter
    state_data = {
        'state': state,
        'user_id': request.user.id
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    # Replace state in URL
    authorization_url = authorization_url.replace(f'state={state}', f'state={encoded_state}')
    
    print(f"DEBUG connect: Storing user_id {request.user.id} in session")
    print(f"DEBUG connect: Encoded state: {encoded_state[:50]}...")
    
    # Still store in session as backup
    request.session['oauth_state'] = state
    request.session['oauth_user_id'] = request.user.id
    request.session['oauth_encoded_state'] = encoded_state
    request.session.modified = True
    request.session.save()
    
    print(f"DEBUG connect: Session after save - user_id: {request.session.get('oauth_user_id')}")
    print(f"DEBUG connect: Session key after: {request.session.session_key}")
    
    return redirect(authorization_url)


def calendar_oauth_callback(request):
    """Handle OAuth2 callback from Google"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        messages.error(request, "Google Calendar integration is not configured.")
        return redirect('calendar_settings')
    
    print(f"DEBUG callback: Session key: {request.session.session_key}")
    print(f"DEBUG callback: All session keys: {list(request.session.keys())}")
    
    # Try to get user_id from encoded state first
    encoded_state = request.GET.get('state')
    user_id = None
    original_state = None
    
    try:
        import json
        import base64
        decoded = base64.urlsafe_b64decode(encoded_state.encode()).decode()
        state_data = json.loads(decoded)
        user_id = state_data.get('user_id')
        original_state = state_data.get('state')
        print(f"DEBUG callback: Decoded user_id from state: {user_id}")
    except Exception as e:
        print(f"DEBUG callback: Failed to decode state: {e}")
        # Fall back to session
        user_id = request.session.get('oauth_user_id')
        original_state = request.session.get('oauth_state')
        print(f"DEBUG callback: Retrieved user_id from session: {user_id}")
    
    if not user_id:
        messages.error(request, "Session expired. Please try connecting again.")
        return redirect('calendar_settings')
    
    try:
        from django.contrib.auth import get_user_model, login
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        print(f"DEBUG callback: Found user: {user.username} (id: {user.id})")
        print(f"DEBUG callback: User authenticated before login: {request.user.is_authenticated}")
        
        # Log the user back in immediately
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        print(f"DEBUG callback: User authenticated after login: {request.user.is_authenticated}")
        print(f"DEBUG callback: Logged in user: {request.user.username}")
        
        # Save session explicitly
        request.session.save()
        print(f"DEBUG callback: Session saved")
        
    except User.DoesNotExist:
        messages.error(request, "User not found. Please try again.")
        return redirect('calendar_settings')
    
    # Verify state - use the original state we extracted
    if not original_state:
        messages.error(request, "Invalid OAuth state. Please try again.")
        return redirect('calendar_settings')
    
    # Exchange authorization code for credentials
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        state=original_state,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    
    try:
        flow.fetch_token(code=request.GET.get('code'))
        credentials = flow.credentials
        
        # Create or update integration
        integration, created = GoogleCalendarIntegration.objects.update_or_create(
            user=user,
            defaults={
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': ' '.join(credentials.scopes),
                'is_active': True,
            }
        )
        
        action = "connected" if created else "reconnected"
        messages.success(request, f"Google Calendar successfully {action}!")
        
        # Trigger initial sync
        service = GoogleCalendarService(user)
        stats = service.sync_events_to_logs(days_back=7)
        
        if stats.get('logs_created', 0) > 0:
            messages.info(request, f"Synced {stats['logs_created']} calendar events as log activities.")
        
        # Clean up session variables
        request.session.pop('oauth_state', None)
        request.session.pop('oauth_user_id', None)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"OAuth callback error for user {user_id}: {e}")
        messages.error(request, f"Failed to connect Google Calendar: {str(e)}")
        
        # Clean up session variables on error too
        request.session.pop('oauth_state', None)
        request.session.pop('oauth_user_id', None)
    
    return redirect('calendar_settings')


@login_required
def calendar_disconnect(request):
    """Disconnect Google Calendar integration"""
    if request.method == 'POST':
        try:
            integration = GoogleCalendarIntegration.objects.get(user=request.user)
            integration.delete()
            messages.success(request, "Google Calendar disconnected successfully.")
        except GoogleCalendarIntegration.DoesNotExist:
            messages.info(request, "No Google Calendar integration found.")
    
    return redirect('calendar_settings')


@login_required
def calendar_sync_now(request):
    """Manually trigger calendar sync"""
    if request.method == 'POST':
        try:
            integration = GoogleCalendarIntegration.objects.get(user=request.user)
            
            if not integration.is_active:
                messages.warning(request, "Calendar integration is disabled. Enable it first.")
                return redirect('calendar_settings')
            
            # Perform sync
            service = GoogleCalendarService(request.user)
            stats = service.sync_events_to_logs(days_back=7)
            
            if stats.get('errors'):
                messages.error(request, f"Sync completed with errors: {', '.join(stats['errors'][:3])}")
            elif stats['logs_created'] > 0:
                messages.success(request, f"Successfully synced! Created {stats['logs_created']} new log entries from {stats['events_processed']} calendar events.")
            else:
                messages.info(request, f"Sync completed. No new events to import (processed {stats['events_processed']} events).")
        
        except GoogleCalendarIntegration.DoesNotExist:
            messages.error(request, "Please connect your Google Calendar first.")
        except Exception as e:
            logger.error(f"Manual sync error for {request.user.username}: {e}")
            messages.error(request, f"Sync failed: {str(e)}")
    
    return redirect('calendar_settings')


@login_required
def calendar_update_settings(request):
    """Update calendar sync settings"""
    if request.method == 'POST':
        try:
            integration = GoogleCalendarIntegration.objects.get(user=request.user)
            
            # Update settings from POST data
            integration.auto_sync = request.POST.get('auto_sync') == 'on'
            integration.sync_interval_hours = int(request.POST.get('sync_interval_hours', 1))
            integration.min_event_duration = int(request.POST.get('min_event_duration', 15))
            integration.exclude_all_day_events = request.POST.get('exclude_all_day_events') == 'on'
            
            # Update default category
            category_id = request.POST.get('default_category')
            if category_id:
                try:
                    category = Category.objects.get(id=category_id)
                    # Verify user has access to this category
                    if category.is_global or category.user == request.user:
                        integration.default_category = category
                except Category.DoesNotExist:
                    pass
            else:
                integration.default_category = None
            
            integration.save()
            messages.success(request, "Calendar settings updated successfully.")
        
        except GoogleCalendarIntegration.DoesNotExist:
            messages.error(request, "Please connect your Google Calendar first.")
        except ValueError as e:
            messages.error(request, f"Invalid settings: {str(e)}")
    
    return redirect('calendar_settings')


@login_required
@require_http_methods(["GET"])
def calendar_list_calendars(request):
    """API endpoint to list available calendars"""
    try:
        service = GoogleCalendarService(request.user)
        calendars = service.list_calendars()
        
        return JsonResponse({
            'success': True,
            'calendars': [
                {
                    'id': cal.get('id'),
                    'summary': cal.get('summary'),
                    'primary': cal.get('primary', False),
                    'backgroundColor': cal.get('backgroundColor', '#000000'),
                }
                for cal in calendars
            ]
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================
# iCloud Calendar Integration Views
# ============================================

@login_required
@require_http_methods(["GET", "POST"])
def icloud_calendar_connect(request):
    """Connect or update iCloud Calendar integration"""
    if request.method == 'POST':
        apple_id = request.POST.get('apple_id', '').strip()
        app_password = request.POST.get('app_password', '').strip()
        
        if not apple_id or not app_password:
            messages.error(request, "Apple ID and App-Specific Password are required.")
            return redirect('calendar_settings')
        
        try:
            # Create or update integration
            integration, created = ICloudCalendarIntegration.objects.update_or_create(
                user=request.user,
                defaults={
                    'apple_id': apple_id,
                    'app_specific_password': app_password,
                    'is_active': True,
                }
            )
            
            action = "connected" if created else "updated"
            messages.success(request, f"iCloud Calendar successfully {action}!")
            
        except Exception as e:
            logger.error(f"iCloud Calendar connection error for user {request.user.id}: {str(e)}")
            messages.error(request, f"Failed to connect iCloud Calendar: {str(e)}")
        
        return redirect('calendar_settings')
    
    # GET request - show connection form
    try:
        integration = ICloudCalendarIntegration.objects.get(user=request.user)
        apple_id = integration.apple_id
    except ICloudCalendarIntegration.DoesNotExist:
        apple_id = ''
    
    context = {
        'apple_id': apple_id,
    }
    return render(request, 'tracker/icloud_connect.html', context)


@login_required
@require_http_methods(["POST"])
def icloud_calendar_disconnect(request):
    """Disconnect iCloud Calendar integration"""
    try:
        integration = ICloudCalendarIntegration.objects.get(user=request.user)
        integration.delete()
        messages.success(request, "iCloud Calendar disconnected successfully.")
    except ICloudCalendarIntegration.DoesNotExist:
        messages.info(request, "iCloud Calendar was not connected.")
    
    return redirect('calendar_settings')


@login_required
@require_http_methods(["POST"])
def icloud_calendar_sync(request):
    """Manually trigger iCloud Calendar sync"""
    try:
        integration = ICloudCalendarIntegration.objects.get(user=request.user)
        
        if not integration.is_active:
            messages.warning(request, "iCloud Calendar sync is disabled. Enable it in settings.")
            return redirect('calendar_settings')
        
        # Use the CalDAV service to sync events
        service = ICloudCalendarService(request.user)
        result = service.sync_events(
            days_back=integration.sync_days_back,
            days_forward=integration.sync_days_forward
        )
        
        messages.success(
            request,
            f"iCloud Calendar sync completed! Synced {result['synced_count']} events "
            f"from {result['calendars_synced']} calendar(s). "
            f"Skipped {result['skipped_count']} events."
        )
        
    except ICloudCalendarIntegration.DoesNotExist:
        messages.error(request, "iCloud Calendar is not connected.")
    except Exception as e:
        messages.error(request, f"iCloud Calendar sync failed: {str(e)}")
        logger.error(f"iCloud sync error for user {request.user.id}: {str(e)}")
    
    return redirect('calendar_settings')


@login_required
@require_http_methods(["POST"])
def icloud_calendar_update_settings(request):
    """Update iCloud Calendar sync settings"""
    try:
        integration = ICloudCalendarIntegration.objects.get(user=request.user)
        
        # Update settings from POST data
        integration.auto_sync = request.POST.get('auto_sync') == 'on'
        integration.sync_interval_hours = int(request.POST.get('sync_interval_hours', 1))
        integration.min_event_duration = int(request.POST.get('min_event_duration', 15))
        integration.exclude_all_day_events = request.POST.get('exclude_all_day_events') == 'on'
        
        # Update default category if provided
        category_id = request.POST.get('default_category')
        if category_id:
            try:
                category = Category.objects.get(pk=category_id)
                integration.default_category = category
            except Category.DoesNotExist:
                pass
        
        integration.save()
        messages.success(request, "iCloud Calendar settings updated successfully!")
        
    except ICloudCalendarIntegration.DoesNotExist:
        messages.error(request, "iCloud Calendar is not connected.")
    except Exception as e:
        logger.error(f"Error updating iCloud Calendar settings for user {request.user.id}: {str(e)}")
        messages.error(request, f"Failed to update settings: {str(e)}")
    
    return redirect('calendar_settings')
