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
from .models import Task, DailyLog, Category, DailySummary, FriendRequest, Friendship, ActivityReaction, Plan, PlanNode, DaySchedule, UserProfile
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
    from .visitor_tracking import track_landing_page_visitor
    
    # Track the visitor for analytics
    try:
        visitor = track_landing_page_visitor(request)
        # Store visitor ID in session for future reference
        request.session['visitor_id'] = visitor.id
    except Exception as e:
        # Log the error but don't break the page
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error tracking landing page visitor: {e}")
    
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
    
    # Prepare tasks as JSON for dropdown
    import json
    pending_tasks_json = json.dumps([{
        'id': task.id,
        'title': task.title,
        'category': task.category.name if task.category else None,
        'priority': task.priority,
        'due_date': task.due_date.isoformat() if task.due_date else None,
    } for task in pending_tasks])
    
    # Get today's logs
    today_logs = (
        DailyLog.objects.filter(user=request.user, date=today)
        .select_related("category", "task")
        .order_by("-date", "-id")
    )
    
    context = {
        "today": today,
        "pending_tasks": pending_tasks,
        "pending_tasks_json": pending_tasks_json,
        "plan_tasks": plan_tasks,
        "today_logs": today_logs,
    }
    
    return render(request, "tracker/day_planner.html", context)


@login_required
def dashboard(request):
    """Main dashboard showing today's overview + weekly summary."""

    # --- Award daily visit points and update streak ---
    from .models import UserPoints
    user_points, created = UserPoints.objects.get_or_create(user=request.user)
    user_points.update_daily_visit()

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

    # --- Load a quote from quotes.jsonl (same quote per day) ---
    import os
    
    random_quote = None
    quotes_file = os.path.join(os.path.dirname(__file__), '..', 'quotes', 'quotes.jsonl')
    
    try:
        if os.path.exists(quotes_file):
            with open(quotes_file, 'r', encoding='utf-8') as f:
                quotes = f.readlines()
                if quotes:
                    # Use day of year to select the same quote for the entire day
                    day_of_year = today.timetuple().tm_yday
                    # Use modulo to cycle through quotes if there are fewer quotes than days
                    quote_index = day_of_year % len(quotes)
                    selected_quote = quotes[quote_index]
                    random_quote = json.loads(selected_quote)
    except Exception as e:
        logger.error(f"Error loading quotes: {str(e)}")
        # Fallback quote if file can't be read
        random_quote = {
            "quote": "The only way to do great work is to love what you do.",
            "author": "Steve Jobs"
        }

    # --- Unread notifications count ---
    from .models import Notification
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    # --- Unread app notifications count ---
    from .models import UserNotification
    unread_app_notifications_count = UserNotification.objects.filter(user=request.user, is_read=False).count()

    # --- Check if user is a mentor ---
    from .models import MentorProfile
    is_mentor = MentorProfile.objects.filter(user=request.user).exists()

    # --- Active public timer sessions ---
    from .models import TimerSession
    
    # Show both running and paused sessions (but not fully ended ones)
    active_timer_sessions = TimerSession.objects.filter(
        is_public=True,
        is_active=True,
        task__isnull=False  # Only include sessions with existing tasks
    ).select_related('host', 'task', 'task__category').prefetch_related('participants')[:10]

    # --- Leaderboard (top 10 users by points) ---
    leaderboard = UserPoints.objects.select_related('user').order_by('-total_points')[:10]
    
    # Find current user's rank
    user_rank = None
    if user_points.total_points > 0:
        user_rank = UserPoints.objects.filter(total_points__gt=user_points.total_points).count() + 1

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
        "unread_notifications_count": unread_notifications_count,
        "unread_app_notifications_count": unread_app_notifications_count,
        "active_plans": plans_with_stats,
        "logs_this_month": logs_this_month,
        "calendar_days": calendar_days,
        "day_names": day_names,
        "random_quote": random_quote,
        "is_mentor": is_mentor,
        "active_timer_sessions": active_timer_sessions,
        "leaderboard": leaderboard,
        "user_points": user_points,
        "user_rank": user_rank,
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
            
            # Auto-classify task only if user didn't manually select a category
            if not task.category:
                from .services import semantic_classifier_remote
                try:
                    # Combine title and description for better classification
                    text = f"{task.title} {task.description or ''}".strip()
                    category_name, scores = semantic_classifier_remote.classify_text(text)
                    
                    # Try to find or create the category
                    from django.db.models import Q
                    category = Category.objects.filter(
                        Q(name__iexact=category_name) & (Q(is_global=True) | Q(user=request.user))
                    ).first()
                    
                    if not category:
                        # Fallback to Uncategorized
                        category = Category.objects.filter(
                            Q(name__iexact='Uncategorized') & (Q(is_global=True) | Q(user=request.user))
                        ).first()
                    
                    if category:
                        task.category = category
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to auto-classify task: {str(e)}")
                    # Continue without category - will use model default
            
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
    """Toggle task completion status"""
    task = get_object_or_404(Task, pk=pk, user=request.user)
    
    # Parse JSON body to determine desired state
    try:
        data = json.loads(request.body) if request.body else {}
        should_complete = data.get('completed', True)
    except json.JSONDecodeError:
        should_complete = True  # Default to completing if no valid JSON
    
    # Check if task was already completed
    was_completed = task.status == 'completed'
    
    if should_complete and not was_completed:
        # Mark as completed
        task.mark_completed()
        
        # Award points for first-time completion
        from .models import UserPoints
        user_points, created = UserPoints.objects.get_or_create(user=request.user)
        user_points.add_points(100, f"Completed task: {task.title}")
        messages.success(request, f"Task completed! +100 points")
        
        # Check if this task completion resulted in any plan completions
        from .models import PlanNode, PointsActivity
        plan_nodes = PlanNode.objects.filter(task=task).select_related('plan')
        
        for node in plan_nodes:
            plan = node.plan
            if plan.user == request.user and plan.is_active:
                # Check if all tasks in this plan are now completed
                total_nodes = plan.nodes.count()
                completed_nodes = plan.nodes.filter(task__status='completed').count()
                
                if total_nodes > 0 and completed_nodes == total_nodes:
                    # Plan is complete! Check if we already awarded points
                    already_awarded = PointsActivity.objects.filter(
                        user=request.user,
                        reason__contains=f"Completed plan: {plan.title}"
                    ).exists()
                    
                    if not already_awarded:
                        user_points.add_points(1000, f"Completed plan: {plan.title}")
                        messages.success(request, f"🎉 Plan '{plan.title}' completed! +1000 points!")
    
    elif not should_complete and was_completed:
        # Mark as incomplete
        task.status = 'pending'
        task.completed_at = None
        task.save()
        messages.info(request, f"Task marked as incomplete")
    
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


@login_required
def task_timer(request, pk):
    """Pomodoro timer view for a specific task"""
    # Check if there's a session code in the URL first
    session_code = request.GET.get('session')
    timer_session = None
    session_participants = []
    
    if session_code:
        try:
            from .models import TimerSession
            timer_session = TimerSession.objects.select_related('task', 'task__user').get(
                share_code=session_code, 
                is_active=True
            )
            
            # Check if the task still exists
            if not timer_session.task:
                messages.error(request, "This timer session's task has been deleted.")
                return redirect('task_list')
            
            # For public sessions, use the session's task regardless of owner
            task = timer_session.task
            
            # Add current user as participant if not already
            if request.user not in timer_session.participants.all():
                timer_session.participants.add(request.user)
            session_participants = list(timer_session.participants.all())
            
        except TimerSession.DoesNotExist:
            messages.warning(request, "Timer session not found or has ended.")
            # Fall back to checking if user owns the task
            task = get_object_or_404(Task, pk=pk, user=request.user)
    else:
        # No session code - require user to own the task
        task = get_object_or_404(Task, pk=pk, user=request.user)
    
    # Get user's recent logs for this task to show context
    recent_logs = DailyLog.objects.filter(
        user=request.user,
        task=task
    ).select_related('category').order_by('-date', '-created_at')[:5]
    
    # Get user's friends for invitations
    friendships = Friendship.objects.filter(user=request.user).select_related('friend')
    friends = [f.friend for f in friendships]
    
    context = {
        'task': task,
        'recent_logs': recent_logs,
        'friends': friends,
        'timer_session': timer_session,
        'session_participants': session_participants,
    }
    return render(request, 'tracker/task_timer.html', context)


@login_required
@require_http_methods(["POST"])
def save_timer_log(request):
    """API endpoint to save activity log from Pomodoro timer"""
    try:
        import json
        data = json.loads(request.body)
        
        task_id = data.get('task_id')
        duration = data.get('duration')  # in minutes
        activity = data.get('activity', '')
        description = data.get('description', '')
        date_str = data.get('date')
        
        # Validate required fields
        if not task_id or not duration:
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields: task_id and duration'
            }, status=400)
        
        # Get the task
        task = get_object_or_404(Task, pk=task_id, user=request.user)
        
        # Parse date or use today
        if date_str:
            from datetime import datetime
            log_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            log_date = timezone.localdate()
        
        # Create the log
        log = DailyLog.objects.create(
            user=request.user,
            date=log_date,
            activity=activity or f"Pomodoro: {task.title}",
            description=description,
            category=task.category,
            task=task,
            duration=int(duration)
        )
        
        # Award points for logging activity
        from .models import UserPoints
        user_points, created = UserPoints.objects.get_or_create(user=request.user)
        user_points.add_points(10, f"Logged activity via Pomodoro timer: {log.activity}")
        
        return JsonResponse({
            'success': True,
            'log_id': log.id,
            'message': 'Activity logged successfully! +10 points',
            'redirect_url': '/logs/'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error saving timer log for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while saving your log'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def create_timer_session(request):
    """API endpoint to create a collaborative timer session"""
    try:
        import json
        from django.utils.safestring import mark_safe
        from .models import TimerSession
        
        data = json.loads(request.body)
        task_id = data.get('task_id')
        mode = data.get('mode', 'work')
        duration = data.get('duration', 25)
        is_public = data.get('is_public', False)
        invited_user_ids = data.get('invited_users', [])
        
        if not task_id:
            return JsonResponse({'success': False, 'error': 'Task ID required'}, status=400)
        
        task = get_object_or_404(Task, pk=task_id, user=request.user)
        
        # Create session
        session = TimerSession.objects.create(
            task=task,
            host=request.user,
            mode=mode,
            duration=duration,
            is_public=is_public,
            share_code=TimerSession().generate_share_code(),
            started_at=timezone.now() if is_public else None  # Auto-start public sessions so they appear on dashboard
        )
        
        # Add host as participant
        session.participants.add(request.user)
        
        # Add invited users
        if invited_user_ids:
            invited_users = User.objects.filter(id__in=invited_user_ids)
            session.participants.add(*invited_users)
            
            # Send notifications to invited users with join link
            from .models import UserNotification
            join_url = f"/tasks/{task_id}/timer/?session={session.share_code}"
            
            for user in invited_users:
                # Create notification with session info (format: message|||task_id:session_code)
                notification_message = (
                    f'{request.user.username} invited you to a collaborative timer '
                    f'session for "{task.title}".|||{task_id}:{session.share_code}'
                )
                
                UserNotification.objects.create(
                    user=user,
                    level='info',
                    message=notification_message
                )
        
        return JsonResponse({
            'success': True,
            'session_code': session.share_code,
            'share_url': f'/tasks/{task_id}/timer/?session={session.share_code}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error creating timer session: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_session_participants(request, session_code):
    """API endpoint to get current participants in a timer session"""
    try:
        from .models import TimerSession
        session = get_object_or_404(TimerSession, share_code=session_code, is_active=True)
        
        participants = [{
            'id': p.id,
            'username': p.username,
            'is_host': p.id == session.host.id
        } for p in session.participants.all()]
        
        return JsonResponse({
            'success': True,
            'participants': participants,
            'host': session.host.username
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_session_state(request, session_code):
    """API endpoint to get current state of a timer session for syncing"""
    try:
        from .models import TimerSession
        session = get_object_or_404(TimerSession, share_code=session_code, is_active=True)
        
        return JsonResponse({
            'success': True,
            'state': {
                'mode': session.mode,
                'duration': session.duration,
                'is_active': session.is_active,
                'is_running': session.is_active and session.started_at is not None and session.ended_at is None,
                'started_at': session.started_at.isoformat() if session.started_at else None,
                'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                'host_username': session.host.username
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def update_session_state(request, session_code):
    """API endpoint to update timer session state (start/pause/reset)"""
    try:
        import json
        from .models import TimerSession
        
        session = get_object_or_404(TimerSession, share_code=session_code, is_active=True)
        
        # Only host can update session state
        if session.host != request.user:
            return JsonResponse({'success': False, 'error': 'Only the host can control the session'}, status=403)
        
        data = json.loads(request.body)
        action = data.get('action')  # 'start', 'pause', 'reset'
        
        if action == 'start':
            session.started_at = timezone.now()
            session.ended_at = None
        elif action == 'pause':
            # Store the remaining time by calculating elapsed time
            if session.started_at:
                elapsed = (timezone.now() - session.started_at).total_seconds()
                remaining = (session.duration * 60) - elapsed
                # Update duration to remaining time for when it resumes
                session.duration = max(1, int(remaining / 60))
            session.ended_at = timezone.now()
        elif action == 'reset':
            # Reset to initial duration and mode
            mode = data.get('mode', session.mode)
            duration = data.get('duration', session.duration)
            session.mode = mode
            session.duration = duration
            session.started_at = None
            session.ended_at = None
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
        
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Session {action}ed successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error updating session state: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def end_timer_session(request, session_code):
    """API endpoint for host to end a timer session"""
    try:
        from .models import TimerSession, UserNotification
        
        session = get_object_or_404(TimerSession, share_code=session_code, is_active=True)
        
        # Only host can end the session
        if session.host != request.user:
            return JsonResponse({'success': False, 'error': 'Only the host can end the session'}, status=403)
        
        # Notify all participants (except host) that session ended
        participants = session.participants.exclude(id=request.user.id)
        for participant in participants:
            UserNotification.objects.create(
                user=participant,
                level='info',
                message=f'{request.user.username} ended the collaborative timer session for "{session.task.title}".'
            )
        
        # Mark session as inactive
        session.is_active = False
        session.ended_at = timezone.now()
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Session ended successfully'
        })
        
    except Exception as e:
        logger.error(f"Error ending timer session: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def leave_timer_session(request, session_code):
    """API endpoint for participant to leave a timer session"""
    try:
        from .models import TimerSession, UserNotification
        
        session = get_object_or_404(TimerSession, share_code=session_code, is_active=True)
        
        # Check if user is a participant
        if not session.participants.filter(id=request.user.id).exists():
            return JsonResponse({'success': False, 'error': 'You are not a participant in this session'}, status=403)
        
        # Remove user from participants
        session.participants.remove(request.user)
        
        # Notify host that user left
        if session.host != request.user:
            UserNotification.objects.create(
                user=session.host,
                level='info',
                message=f'{request.user.username} left the collaborative timer session for "{session.task.title}".'
            )
        
        # If host leaves, end the session
        if session.host == request.user:
            # Notify all remaining participants
            participants = session.participants.exclude(id=request.user.id)
            for participant in participants:
                UserNotification.objects.create(
                    user=participant,
                    level='info',
                    message=f'The host ended the collaborative timer session for "{session.task.title}".'
                )
            
            session.is_active = False
            session.ended_at = timezone.now()
            session.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Left session successfully'
        })
        
    except Exception as e:
        logger.error(f"Error leaving timer session: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


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
                
                # Award points for logging activity
                from .models import UserPoints
                user_points, created = UserPoints.objects.get_or_create(user=request.user)
                user_points.add_points(10, f"Logged activity: {log.activity}")
                
                messages.success(request, "Activity logged successfully! +10 points")
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
        ).select_related('category', 'task').order_by('created_at')
        
        # Convert DailyLog entries to event format
        calendar_events = []
        
        for log in calendar_logs:
            # Try to extract time from created_at or distribute events throughout the day
            # Use created_at hour/minute as the event time
            event_time = log.created_at.astimezone(timezone.get_current_timezone())
            start_min = event_time.hour * 60 + event_time.minute
            end_min = start_min + log.duration
            
            # Clamp to valid day range (0-1440 minutes)
            start_min = max(0, min(1380, start_min))  # 0-23:00
            end_min = max(start_min + 15, min(1440, end_min))  # at least 15 min, max 24:00
            
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
def smart_schedule_tasks(request):
    """
    Smart auto-scheduling endpoint that creates an optimized schedule
    based on task priority, due dates, duration, and category balance.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            schedule_date = data.get('date')
            start_time = data.get('start_time')  # HH:MM format
            end_time = data.get('end_time')      # HH:MM format
            
            if not all([schedule_date, start_time, end_time]):
                return JsonResponse({
                    'success': False, 
                    'error': 'Missing required fields: date, start_time, end_time'
                }, status=400)
            
            # Parse date
            try:
                from datetime import datetime
                schedule_date_obj = datetime.strptime(schedule_date, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid date format'}, status=400)
            
            # Parse times (HH:MM) to minutes from midnight
            try:
                start_h, start_m = map(int, start_time.split(':'))
                end_h, end_m = map(int, end_time.split(':'))
                start_minutes = start_h * 60 + start_m
                end_minutes = end_h * 60 + end_m
            except (ValueError, AttributeError):
                return JsonResponse({'success': False, 'error': 'Invalid time format'}, status=400)
            
            if start_minutes >= end_minutes:
                return JsonResponse({'success': False, 'error': 'End time must be after start time'}, status=400)
            
            # Get all pending and in-progress tasks for this user
            tasks_qs = Task.objects.filter(
                user=request.user,
                status__in=['pending', 'in_progress']
            ).select_related('category').order_by('due_date', '-priority')
            
            # Build task->plan mapping
            from .models import Plan, PlanNode
            active_plans = Plan.objects.filter(user=request.user, is_active=True)
            task_to_plans = {}
            
            for plan in active_plans:
                nodes = PlanNode.objects.filter(plan=plan).select_related('task')
                for node in nodes:
                    if node.task and node.task.status in ['pending', 'in_progress']:
                        if node.task.id not in task_to_plans:
                            task_to_plans[node.task.id] = []
                        task_to_plans[node.task.id].append(plan.title)
            
            # Convert tasks to dictionary format for scheduler
            tasks_data = []
            for task in tasks_qs:
                tasks_data.append({
                    'id': task.id,
                    'title': task.title,
                    'priority': task.priority,
                    'due_date': task.due_date.isoformat() if task.due_date else None,
                    'category_name': task.category.name if task.category else 'Uncategorized',
                    'estimated_duration': task.estimated_duration,
                    'plan_names': task_to_plans.get(task.id, [])
                })
            
            if not tasks_data:
                return JsonResponse({
                    'success': False,
                    'error': 'No tasks available to schedule. Add some tasks first!'
                }, status=400)
            
            # Use the smart scheduler
            from .services.smart_scheduler import SmartScheduler
            scheduler = SmartScheduler(start_minutes, end_minutes, schedule_date_obj)
            scheduled_events, stats = scheduler.schedule_tasks(tasks_data)
            
            logger.info(f"Smart scheduling complete: {stats}")
            
            return JsonResponse({
                'success': True,
                'events': scheduled_events,
                'stats': stats,
                'message': f"Scheduled {stats['scheduled_count']} tasks"
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error in smart_schedule_tasks: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)

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
    """Send a friend request to another user (AJAX & redirect support)"""
    
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
    
    # Check if a pending request already exists
    existing_request = FriendRequest.objects.filter(
        from_user=request.user,
        to_user=to_user,
        status='pending'
    ).first()
    
    if existing_request:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'warning', 'message': f'Friend request already sent to {to_user.username}'}, status=400)
        messages.info(request, f"Friend request already sent to {to_user.username}")
        return redirect('user_list')
    
    # Check if the other user already sent you a request (auto-accept)
    reverse_request = FriendRequest.objects.filter(
        from_user=to_user,
        to_user=request.user,
        status='pending'
    ).first()
    
    if reverse_request:
        # Auto-accept: they already requested you, so accept their request
        reverse_request.accept()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': f'You are now friends with {to_user.username}!'}, status=201)
        messages.success(request, f"You are now friends with {to_user.username}!")
        return redirect('user_list')
    
    # Create new friend request
    friend_request = FriendRequest.objects.create(
        from_user=request.user,
        to_user=to_user,
        status='pending'
    )
    
    # Create notification for the recipient
    from .models import Notification
    Notification.objects.create(
        user=to_user,
        notification_type='friend_request',
        title='New Friend Request',
        message=f'{request.user.get_full_name() or request.user.username} sent you a friend request',
        friend_request=friend_request
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': f'Friend request sent to {to_user.username}'}, status=201)
    messages.success(request, f"Friend request sent to {to_user.username}")
    
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
        from_user = friend_request.from_user
        
        # Use the model's accept method which creates bidirectional friendship
        friend_request.accept()
        
        # Create notification for the requester
        from .models import Notification
        Notification.objects.create(
            user=from_user,
            notification_type='friend_accepted',
            title='Friend Request Accepted',
            message=f'{request.user.get_full_name() or request.user.username} accepted your friend request'
        )
        
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
    from .models import UserPoints
    from django.core.paginator import Paginator
    
    friends = Friendship.objects.filter(user=request.user).select_related('friend').order_by('friend__username')
    
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
        
        # Get friend's points
        user_points = UserPoints.objects.filter(user=friend).first()
        total_points = user_points.total_points if user_points else 0
        
        # Calculate friend's rank
        friend_rank = None
        if user_points:
            friend_rank = UserPoints.objects.filter(total_points__gt=user_points.total_points).count() + 1
        
        friends_data.append({
            'friend': friend,
            'friendship': friendship,
            'completed_tasks': completed_tasks,
            'total_time': total_time,
            'activity_percent': activity_percent,
            'points': total_points,
            'rank': friend_rank,
        })
    
    # Pagination
    paginator = Paginator(friends_data, 12)  # 12 friends per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'friends_data': page_obj,
        'page_obj': page_obj,
        'total_friends_count': len(friends_data),
    }
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
    from django.core.paginator import Paginator
    
    search_query = request.GET.get('search', '')
    
    users = User.objects.exclude(id=request.user.id).order_by('username')
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(users, 12)  # 12 users per page (fits 3x4 grid nicely)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
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
        'users': page_obj,
        'page_obj': page_obj,
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
        # Star created - award points to the activity owner
        from .models import UserPoints
        activity_owner = activity.user
        owner_points, created_points = UserPoints.objects.get_or_create(user=activity_owner)
        owner_points.add_points(75, f"Received star from {request.user.username}")
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
    """Redirect to the unified notifications list page"""
    return redirect('notifications_list')


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
    
    # Check if plan just completed and award points
    if total_nodes > 0 and completed_nodes == total_nodes and plan.is_active:
        from .models import UserPoints, PointsActivity
        
        # Check if we already awarded points for this plan completion
        already_awarded = PointsActivity.objects.filter(
            user=request.user,
            reason__contains=f"Completed plan: {plan.title}"
        ).exists()
        
        if not already_awarded:
            user_points, created = UserPoints.objects.get_or_create(user=request.user)
            user_points.add_points(1000, f"Completed plan: {plan.title}")
            messages.success(request, f"🎉 Plan completed! +1000 points!")
    
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


from .forms import UserProfileForm

@login_required
def set_user_timezone(request):
    """API endpoint to save user's detected timezone"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            timezone_str = data.get('timezone')
            
            if not timezone_str:
                return JsonResponse({'success': False, 'error': 'Timezone is required'}, status=400)
            
            # Validate timezone
            import pytz
            try:
                pytz.timezone(timezone_str)
            except pytz.exceptions.UnknownTimeZoneError:
                return JsonResponse({'success': False, 'error': 'Invalid timezone'}, status=400)
            
            # Update user profile
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            profile.timezone = timezone_str
            profile.save()
            
            return JsonResponse({
                'success': True,
                'timezone': timezone_str,
                'message': 'Timezone updated successfully'
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error setting user timezone: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)

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
def download_user_data(request):
    """Export all user data as JSON for download"""
    from django.http import HttpResponse
    import json
    from datetime import datetime
    
    user = request.user
    
    # Collect all user data
    data = {
        'export_date': datetime.now().isoformat(),
        'user': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        },
        'tasks': list(Task.objects.filter(user=user).values(
            'title', 'description', 'status', 'priority', 'due_date', 
            'created_at', 'completed_at', 'estimated_duration', 
            'actual_duration', 'category__name', 'is_global'
        )),
        'daily_logs': list(DailyLog.objects.filter(user=user).values(
            'activity', 'date', 'duration', 'description', 
            'category__name', 'created_at', 'task__title'
        )),
        'categories': list(Category.objects.filter(user=user).values(
            'name', 'color', 'created_at'
        )),
        'plans': [],
        'day_schedules': list(DaySchedule.objects.filter(user=user).values(
            'date', 'title', 'events_data', 'created_at', 'updated_at'
        )),
        'friendships': list(Friendship.objects.filter(
            Q(user=user) | Q(friend=user)
        ).values('user__username', 'friend__username', 'created_at')),
    }
    
    # Get plans with nodes
    plans = Plan.objects.filter(user=user).prefetch_related('nodes')
    for plan in plans:
        plan_data = {
            'title': plan.title,
            'description': plan.description,
            'is_active': plan.is_active,
            'created_at': plan.created_at.isoformat(),
            'updated_at': plan.updated_at.isoformat(),
            'nodes': list(plan.nodes.values(
                'task__title', 'task__description', 'task__status', 
                'position_x', 'position_y', 'order'
            ))
        }
        data['plans'].append(plan_data)
    
    # Create response
    response = HttpResponse(
        json.dumps(data, indent=2, default=str),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="vismatrix_data_{user.username}_{datetime.now().strftime("%Y%m%d")}.json"'
    
    logger.info(f"User {user.username} downloaded their data")
    return response


@login_required
def delete_account(request):
    """Permanently delete user account and all associated data"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('profile_settings')
    
    user = request.user
    username = user.username
    
    try:
        # Log the deletion
        logger.warning(f"User {username} (id: {user.id}) requested account deletion")
        
        # Django's ORM will handle cascade deletions for related objects
        # This includes: tasks, logs, categories, plans, friendships, etc.
        user.delete()
        
        # Add a success message before logout
        messages.success(request, f"Your account has been permanently deleted. Goodbye, {username}!")
        
        # Redirect to landing page (user will be logged out automatically)
        return redirect('landing_page')
        
    except Exception as e:
        logger.error(f"Error deleting account for {username}: {str(e)}")
        messages.error(request, "An error occurred while deleting your account. Please try again or contact support.")
        return redirect('profile_settings')


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


@login_required
def quickstart(request):
    """Quickstart page showing pre-built plan options."""
    return render(request, 'tracker/quickstart.html')


@login_required
def quickstart_create_plan(request, plan_type):
    """Create a pre-built plan based on the selected type."""
    if request.method != 'POST':
        return redirect('quickstart')
    
    # Define plan templates
    plan_templates = {
        'fitness': {
            'title': 'Fitness Journey',
            'description': 'A comprehensive fitness plan to transform your health with structured workout routines, nutrition tracking, and recovery goals.',
            'tasks': [
                {'title': 'Set fitness baseline - Weight, measurements, and fitness test', 'priority': 'high', 'category': 'Health'},
                {'title': 'Create weekly workout schedule', 'priority': 'high', 'category': 'Health'},
                {'title': 'Cardio workout - 30 min running/cycling', 'priority': 'medium', 'category': 'Health'},
                {'title': 'Strength training - Upper body', 'priority': 'medium', 'category': 'Health'},
                {'title': 'Strength training - Lower body', 'priority': 'medium', 'category': 'Health'},
                {'title': 'Strength training - Core workout', 'priority': 'medium', 'category': 'Health'},
                {'title': 'Meal prep - Plan healthy meals for the week', 'priority': 'high', 'category': 'Health'},
                {'title': 'Track daily nutrition and water intake', 'priority': 'medium', 'category': 'Health'},
                {'title': 'Rest day - Stretching and recovery', 'priority': 'low', 'category': 'Health'},
                {'title': 'Weekly progress check - Weight and measurements', 'priority': 'medium', 'category': 'Health'},
                {'title': 'HIIT workout - High intensity interval training', 'priority': 'medium', 'category': 'Health'},
                {'title': 'Yoga or flexibility session', 'priority': 'low', 'category': 'Health'},
            ],
            'dependencies': [
                # Workouts depend on baseline and schedule
                (2, [0, 1]),  # Cardio depends on baseline and schedule
                (3, [0, 1]),  # Upper body depends on baseline and schedule
                (4, [0, 1]),  # Lower body depends on baseline and schedule
                (5, [0, 1]),  # Core depends on baseline and schedule
                (7, [6]),     # Track nutrition depends on meal prep
                (9, [2, 3, 4, 5]),  # Weekly check depends on doing workouts
                (10, [0, 1]), # HIIT depends on baseline and schedule
                (11, [0, 1]), # Yoga depends on baseline and schedule
            ]
        },
        'exam': {
            'title': 'Competitive Exam Preparation',
            'description': 'A structured study plan to ace your competitive exams with subject coverage, practice tests, and effective revision strategies.',
            'tasks': [
                {'title': 'Create detailed study timetable', 'priority': 'high', 'category': 'Study'},
                {'title': 'Collect and organize study materials', 'priority': 'high', 'category': 'Study'},
                {'title': 'Mathematics - Complete Chapter 1', 'priority': 'high', 'category': 'Study'},
                {'title': 'Mathematics - Practice problems set 1', 'priority': 'medium', 'category': 'Study'},
                {'title': 'English - Grammar and comprehension', 'priority': 'medium', 'category': 'Study'},
                {'title': 'English - Vocabulary building (50 words)', 'priority': 'low', 'category': 'Study'},
                {'title': 'Science - Physics concepts review', 'priority': 'high', 'category': 'Study'},
                {'title': 'Science - Chemistry formulas memorization', 'priority': 'medium', 'category': 'Study'},
                {'title': 'Mock test - Full length practice exam', 'priority': 'high', 'category': 'Study'},
                {'title': 'Analyze mock test results and weak areas', 'priority': 'high', 'category': 'Study'},
                {'title': 'Revision - All completed chapters', 'priority': 'medium', 'category': 'Study'},
                {'title': 'Current affairs - Weekly update', 'priority': 'low', 'category': 'Study'},
                {'title': 'Speed and accuracy practice', 'priority': 'medium', 'category': 'Study'},
                {'title': 'Previous year question papers', 'priority': 'high', 'category': 'Study'},
            ],
            'dependencies': [
                # Study chapters depend on timetable and materials
                (2, [0, 1]),  # Math Chapter depends on timetable and materials
                (3, [2]),     # Math Practice depends on completing chapter
                (4, [0, 1]),  # English depends on timetable and materials
                (5, [4]),     # Vocabulary depends on grammar
                (6, [0, 1]),  # Physics depends on timetable and materials
                (7, [0, 1]),  # Chemistry depends on timetable and materials
                (8, [2, 4, 6, 7]),  # Mock test depends on covering subjects
                (9, [8]),     # Analyze results depends on mock test
                (10, [9]),    # Revision depends on analysis
                (13, [8]),    # Previous year papers depend on mock test
            ]
        },
        'work': {
            'title': 'Professional Growth Goals',
            'description': 'Accelerate your career growth with targeted skill development, strategic networking, and achievement milestones.',
            'tasks': [
                {'title': 'Define career goals and 6-month targets', 'priority': 'high', 'category': 'Work'},
                {'title': 'Identify 3 key skills to develop', 'priority': 'high', 'category': 'Work'},
                {'title': 'Complete online course - Module 1', 'priority': 'medium', 'category': 'Work'},
                {'title': 'Complete online course - Module 2', 'priority': 'medium', 'category': 'Work'},
                {'title': 'Build portfolio project - Phase 1', 'priority': 'high', 'category': 'Work'},
                {'title': 'Build portfolio project - Phase 2', 'priority': 'high', 'category': 'Work'},
                {'title': 'Network - Connect with 5 industry professionals', 'priority': 'medium', 'category': 'Work'},
                {'title': 'Attend industry webinar or workshop', 'priority': 'low', 'category': 'Work'},
                {'title': 'Update resume and LinkedIn profile', 'priority': 'medium', 'category': 'Work'},
                {'title': 'Read industry book or research papers', 'priority': 'low', 'category': 'Work'},
                {'title': 'Contribute to open source project', 'priority': 'medium', 'category': 'Work'},
                {'title': 'Write technical blog post', 'priority': 'low', 'category': 'Work'},
                {'title': 'Seek feedback from mentor or peers', 'priority': 'medium', 'category': 'Work'},
                {'title': 'Monthly progress review and goal adjustment', 'priority': 'high', 'category': 'Work'},
            ],
            'dependencies': [
                # Skills and courses depend on goals
                (1, [0]),     # Identify skills depends on defining goals
                (2, [1]),     # Course Module 1 depends on identifying skills
                (3, [2]),     # Course Module 2 depends on Module 1
                (4, [1]),     # Portfolio Phase 1 depends on identifying skills
                (5, [4]),     # Portfolio Phase 2 depends on Phase 1
                (8, [2, 3]),  # Update resume depends on completing courses
                (10, [2, 3]), # Open source depends on completing courses
                (11, [4, 5]), # Blog post depends on portfolio project
                (12, [2, 3, 4, 5]),  # Feedback depends on having work to show
                (13, [6, 8, 10, 11, 12]),  # Monthly review depends on activities
            ]
        }
    }
    
    if plan_type not in plan_templates:
        messages.error(request, "Invalid plan type selected.")
        return redirect('quickstart')
    
    template = plan_templates[plan_type]
    
    try:
        # Create the plan
        plan = Plan.objects.create(
            user=request.user,
            title=template['title'],
            description=template['description'],
            is_active=True
        )
        
        # Create tasks and add them to the plan
        created_nodes = []
        for task_data in template['tasks']:
            # Get or create category
            category, _ = Category.objects.get_or_create(
                name=task_data['category'],
                user=request.user,
                defaults={'color': '#3B82F6'}
            )
            
            # Create task
            task = Task.objects.create(
                user=request.user,
                title=task_data['title'],
                category=category,
                priority=task_data['priority'],
                status='pending'
            )
            
            # Create plan node
            node = PlanNode.objects.create(
                plan=plan,
                task=task,
                order=len(created_nodes) + 1
            )
            created_nodes.append(node)
        
        # Add dependencies
        if 'dependencies' in template:
            for task_index, dependency_indices in template['dependencies']:
                node = created_nodes[task_index]
                for dep_index in dependency_indices:
                    dependency_node = created_nodes[dep_index]
                    node.dependencies.add(dependency_node)
        
        messages.success(
            request, 
            f'Successfully created "{template["title"]}" plan with {len(created_nodes)} tasks! '
            f'View it in your <a href="/plans/{plan.id}/" class="underline">Plans</a>.'
        )
        
    except Exception as e:
        logger.error(f"Error creating quickstart plan for user {request.user.id}: {str(e)}")
        messages.error(request, f"Failed to create plan: {str(e)}")
        return redirect('quickstart')
    
    return redirect('plan_detail', pk=plan.id)


# ============================================================================
# MENTORSHIP VIEWS
# ============================================================================

@login_required
def mentor_list(request):
    """List all available mentors with filtering by category."""
    from .models import MentorProfile
    
    category_filter = request.GET.get('category', '')
    
    mentors = MentorProfile.objects.filter(is_active=True).select_related('user')
    
    # Filter mentors based on category (compatible with SQLite)
    mentor_list = []
    for mentor in mentors:
        # Check if category filter matches
        if category_filter and category_filter not in mentor.categories:
            continue
        
        mentor_list.append({
            'profile': mentor,
            'user': mentor.user,
            'active_mentees': mentor.active_mentees_count(),
            'categories_display': mentor.get_categories_display(),
        })
    
    context = {
        'mentor_list': mentor_list,
        'category_filter': category_filter,
        'categories': MentorProfile.CATEGORY_CHOICES,
    }
    
    return render(request, 'tracker/mentorship/mentor_list.html', context)


@login_required
def mentor_profile_view(request, mentor_id):
    """View a mentor's profile and apply for mentorship."""
    from .models import MentorProfile, MentorshipRequest
    
    mentor_profile = get_object_or_404(MentorProfile, id=mentor_id)
    
    # Check if user already has a request to this mentor
    existing_requests = MentorshipRequest.objects.filter(
        mentee=request.user,
        mentor_profile=mentor_profile
    )
    
    context = {
        'mentor_profile': mentor_profile,
        'active_mentees': mentor_profile.active_mentees_count(),
        'categories_display': mentor_profile.get_categories_display(),
        'existing_requests': existing_requests,
        'can_accept_more': mentor_profile.can_accept_more_mentees(),
    }
    
    return render(request, 'tracker/mentorship/mentor_profile.html', context)


@login_required
def become_mentor(request):
    """Register as a mentor or update mentor profile."""
    from .models import MentorProfile
    
    try:
        mentor_profile = MentorProfile.objects.get(user=request.user)
        is_new = False
    except MentorProfile.DoesNotExist:
        mentor_profile = None
        is_new = True
    
    if request.method == 'POST':
        # Get form data
        categories = request.POST.getlist('categories')
        bio = request.POST.get('bio', '').strip()
        experience_years = int(request.POST.get('experience_years', 0))
        specializations = request.POST.get('specializations', '').strip()
        max_mentees = int(request.POST.get('max_mentees', 5))
        is_active = request.POST.get('is_active') == 'on'
        
        if not categories:
            messages.error(request, "Please select at least one category.")
            return redirect('become_mentor')
        
        if not bio:
            messages.error(request, "Please provide a bio.")
            return redirect('become_mentor')
        
        if mentor_profile:
            # Update existing
            mentor_profile.categories = categories
            mentor_profile.bio = bio
            mentor_profile.experience_years = experience_years
            mentor_profile.specializations = specializations
            mentor_profile.max_mentees = max_mentees
            mentor_profile.is_active = is_active
            mentor_profile.save()
            messages.success(request, "Mentor profile updated successfully!")
        else:
            # Create new
            mentor_profile = MentorProfile.objects.create(
                user=request.user,
                categories=categories,
                bio=bio,
                experience_years=experience_years,
                specializations=specializations,
                max_mentees=max_mentees,
                is_active=is_active
            )
            messages.success(request, "Welcome! You're now a mentor on VisMatrix!")
        
        return redirect('mentor_dashboard')
    
    context = {
        'mentor_profile': mentor_profile,
        'is_new': is_new,
        'categories': MentorProfile.CATEGORY_CHOICES,
    }
    
    return render(request, 'tracker/mentorship/become_mentor.html', context)


@login_required
def apply_for_mentorship(request, mentor_id):
    """Apply for mentorship from a specific mentor."""
    from .models import MentorProfile, MentorshipRequest
    
    mentor_profile = get_object_or_404(MentorProfile, id=mentor_id)
    
    if request.method == 'POST':
        category = request.POST.get('category')
        message = request.POST.get('message', '').strip()
        
        if not category or category not in dict(MentorProfile.CATEGORY_CHOICES):
            messages.error(request, "Please select a valid category.")
            return redirect('mentor_profile', mentor_id=mentor_id)
        
        if category not in mentor_profile.categories:
            messages.error(request, "This mentor doesn't offer mentorship in that category.")
            return redirect('mentor_profile', mentor_id=mentor_id)
        
        if not message:
            messages.error(request, "Please tell the mentor why you want mentorship.")
            return redirect('mentor_profile', mentor_id=mentor_id)
        
        # Check if already applied
        existing = MentorshipRequest.objects.filter(
            mentee=request.user,
            mentor_profile=mentor_profile,
            category=category
        ).first()
        
        if existing:
            messages.warning(request, "You already have a request for this category with this mentor.")
            return redirect('mentor_profile', mentor_id=mentor_id)
        
        # Create request
        from .models import Notification
        mentorship_request = MentorshipRequest.objects.create(
            mentee=request.user,
            mentor_profile=mentor_profile,
            category=category,
            message=message
        )
        
        # Create notification for mentor
        category_display = dict(MentorProfile.CATEGORY_CHOICES).get(category, category)
        Notification.objects.create(
            user=mentor_profile.user,
            notification_type='mentorship_request',
            title='New Mentorship Request',
            message=f"{request.user.username} requested mentorship in {category_display}",
            mentorship_request=mentorship_request
        )
        
        messages.success(request, f"Your mentorship request has been sent to {mentor_profile.user.username}!")
        return redirect('my_mentorships')
    
    return redirect('mentor_profile', mentor_id=mentor_id)


@login_required
def mentor_dashboard(request):
    """Dashboard for mentors to manage their mentees and requests."""
    from .models import MentorProfile, MentorshipRequest
    
    try:
        mentor_profile = MentorProfile.objects.get(user=request.user)
    except MentorProfile.DoesNotExist:
        messages.info(request, "You're not registered as a mentor yet.")
        return redirect('become_mentor')
    
    # Get pending requests
    pending_requests = MentorshipRequest.objects.filter(
        mentor_profile=mentor_profile,
        status='pending'
    ).select_related('mentee').order_by('-created_at')
    
    # Get accepted mentees
    active_mentees = MentorshipRequest.objects.filter(
        mentor_profile=mentor_profile,
        status='accepted'
    ).select_related('mentee').order_by('-updated_at')
    
    # Add friendship information to each mentee
    for req in pending_requests:
        friendship = Friendship.objects.filter(
            Q(user=request.user, friend=req.mentee) | Q(user=req.mentee, friend=request.user)
        ).first()
        req.friendship_id = friendship.id if friendship else None
    
    for mentorship in active_mentees:
        friendship = Friendship.objects.filter(
            Q(user=request.user, friend=mentorship.mentee) | Q(user=mentorship.mentee, friend=request.user)
        ).first()
        mentorship.friendship_id = friendship.id if friendship else None
    
    context = {
        'mentor_profile': mentor_profile,
        'pending_requests': pending_requests,
        'active_mentees': active_mentees,
        'active_count': mentor_profile.active_mentees_count(),
        'can_accept_more': mentor_profile.can_accept_more_mentees(),
    }
    
    return render(request, 'tracker/mentorship/mentor_dashboard.html', context)


@login_required
def respond_to_mentorship_request(request, request_id):
    """Accept or reject a mentorship request."""
    from .models import MentorshipRequest
    
    mentorship_request = get_object_or_404(MentorshipRequest, id=request_id)
    
    # Verify this is the mentor
    if mentorship_request.mentor_profile.user != request.user:
        messages.error(request, "You don't have permission to respond to this request.")
        return redirect('mentor_dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        response_message = request.POST.get('response_message', '').strip()
        
        if action == 'accept':
            # Check if can accept more mentees
            if not mentorship_request.mentor_profile.can_accept_more_mentees():
                messages.error(request, "You've reached your maximum number of mentees.")
                return redirect('mentor_dashboard')
            
            mentorship_request.status = 'accepted'
            mentorship_request.response_message = response_message
            mentorship_request.responded_at = timezone.now()
            mentorship_request.save()
            
            # Automatically create friendship if not already friends
            existing_friendship = Friendship.objects.filter(
                Q(user=request.user, friend=mentorship_request.mentee) | 
                Q(user=mentorship_request.mentee, friend=request.user)
            ).first()
            
            if not existing_friendship:
                Friendship.objects.create(
                    user=request.user,
                    friend=mentorship_request.mentee
                )
                messages.success(request, f"You and {mentorship_request.mentee.username} are now friends!")
            
            # Create notification for mentee
            from .models import Notification
            Notification.objects.create(
                user=mentorship_request.mentee,
                notification_type='mentorship_accepted',
                title='Mentorship Request Accepted!',
                message=f"{request.user.username} accepted your mentorship request for {mentorship_request.get_category_display()}",
                mentorship_request=mentorship_request
            )
            
            # Award points for accepting a mentee
            from .models import UserPoints
            user_points, created = UserPoints.objects.get_or_create(user=request.user)
            user_points.add_points(100, f"Accepted mentee: {mentorship_request.mentee.username}")
            
            messages.success(request, f"You've accepted {mentorship_request.mentee.username} as your mentee! +100 points")
            
        elif action == 'reject':
            mentorship_request.status = 'rejected'
            mentorship_request.response_message = response_message
            mentorship_request.responded_at = timezone.now()
            mentorship_request.save()
            
            # Create notification for mentee
            from .models import Notification
            Notification.objects.create(
                user=mentorship_request.mentee,
                notification_type='mentorship_rejected',
                title='Mentorship Request Update',
                message=f"{request.user.username} has responded to your mentorship request for {mentorship_request.get_category_display()}",
                mentorship_request=mentorship_request
            )
            
            messages.info(request, "Request has been declined.")
        
        return redirect('mentor_dashboard')
    
    return redirect('mentor_dashboard')


@login_required
def my_mentorships(request):
    """View user's mentorship requests and active mentorships."""
    from .models import MentorshipRequest
    
    # Get all mentorship requests made by this user
    my_requests = MentorshipRequest.objects.filter(
        mentee=request.user
    ).select_related('mentor_profile__user').order_by('-created_at')
    
    context = {
        'my_requests': my_requests,
    }
    
    return render(request, 'tracker/mentorship/my_mentorships.html', context)


@login_required
def complete_mentorship(request, request_id):
    """Mark a mentorship as completed."""
    from .models import MentorshipRequest
    
    mentorship_request = get_object_or_404(MentorshipRequest, id=request_id)
    
    # Only mentor can mark as completed
    if mentorship_request.mentor_profile.user != request.user:
        messages.error(request, "Only the mentor can complete a mentorship.")
        return redirect('my_mentorships')
    
    if request.method == 'POST':
        mentorship_request.status = 'completed'
        mentorship_request.save()
        
        # Create notification for mentee
        from .models import Notification
        Notification.objects.create(
            user=mentorship_request.mentee,
            notification_type='mentorship_completed',
            title='Mentorship Completed',
            message=f"Your mentorship with {request.user.username} has been marked as completed",
            mentorship_request=mentorship_request
        )
        
        messages.success(request, "Mentorship marked as completed!")
        return redirect('mentor_dashboard')
    
    return redirect('mentor_dashboard')


@login_required
def notifications_list(request):
    """List all notifications for the user - unified view with system notifications, app notifications, stars, and messages."""
    from .models import Notification, UserNotification
    from datetime import timedelta
    
    # Get both old Notification and new UserNotification models
    old_notifications = Notification.objects.filter(user=request.user).select_related('mentorship_request', 'friend_request', 'friend_request__from_user')
    new_notifications = UserNotification.objects.filter(user=request.user).order_by('-created_at')
    
    # Count unread app notifications before marking as read
    unread_app_notifications_count = new_notifications.filter(is_read=False).count()
    
    # Combine both notification types for system notifications section
    system_notifications = list(new_notifications) + list(old_notifications)
    system_notifications.sort(key=lambda x: x.created_at, reverse=True)
    
    # Parse timer notifications and add timer data
    for notification in system_notifications:
        if '|||' in notification.message:
            parts = notification.message.split('|||')
            if len(parts) == 2:
                text_part = parts[0].strip()
                session_data = parts[1].strip()
                if ':' in session_data:
                    task_id, session_code = session_data.split(':', 1)
                    # Add parsed data as attributes
                    notification.timer_text = text_part
                    notification.timer_task_id = task_id
                    notification.timer_session_code = session_code
                    notification.is_timer_notification = True
                else:
                    notification.is_timer_notification = False
            else:
                notification.is_timer_notification = False
        else:
            notification.is_timer_notification = False
    
    # Mark notifications as read when viewed
    for notification in new_notifications.filter(is_read=False):
        notification.mark_as_read()
    for notification in old_notifications.filter(is_read=False):
        notification.mark_as_read()
    
    # Get stars received (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    # Stars on tasks
    task_stars = ActivityReaction.objects.filter(
        task__user=request.user,
        created_at__gte=thirty_days_ago
    ).select_related('user', 'task').order_by('-created_at')
    
    # Stars on daily logs
    log_stars = ActivityReaction.objects.filter(
        daily_log__user=request.user,
        created_at__gte=thirty_days_ago
    ).select_related('user', 'daily_log').order_by('-created_at')
    
    # Combine and sort stars by creation date
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
    
    all_stars.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Get unread messages from conversations
    from .models import Conversation, ConversationMember, Message
    unread_messages = []
    
    me = request.user
    conversations = Conversation.objects.filter(
        Q(user1=me) | Q(user2=me)
    ).select_related('user1', 'user2').order_by('-updated_at')
    
    for conv in conversations:
        other = conv.user2 if conv.user1 == me else conv.user1
        
        try:
            membership = ConversationMember.objects.get(conversation=conv, user=me)
            unread_qs = conv.messages.all()
            if membership.last_read_message_id:
                unread_qs = unread_qs.filter(id__gt=membership.last_read_message_id)
            
            unread_count = unread_qs.count()
            
            if unread_count > 0:
                latest_msg = unread_qs.order_by('-created_at').first()
                if latest_msg and latest_msg.created_at >= seven_days_ago:
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
        'notifications': system_notifications[:50],
        'stars': all_stars,
        'total_stars': len(all_stars),
        'unread_messages': unread_messages,
        'total_unread_messages': len(unread_messages),
        'unread_app_notifications': unread_app_notifications_count,
    }
    
    return render(request, 'tracker/notifications_list.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a single notification as read."""
    from .models import Notification
    
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    
    return redirect('notifications_list')


@login_required
def get_unread_notification_count(request):
    """API endpoint to get unread notification count."""
    from .models import Notification
    
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@login_required
def recent_notifications(request):
    """Redirect to unified notifications page."""
    return redirect('notifications_list')


@login_required
def clear_all_notifications(request):
    """Clear all notifications for the current user."""
    from .models import UserNotification
    
    if request.method == 'POST':
        UserNotification.objects.filter(user=request.user).update(is_read=True)
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)


# ============================================================================
# LANDING PAGE ANALYTICS (Admin Only)
# ============================================================================

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from datetime import timedelta

@staff_member_required
def landing_analytics(request):
    """Analytics dashboard for landing page visitors (admin only)."""
    from .models import LandingPageVisitor
    
    # Date range filter
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Total visitors
    total_visitors = LandingPageVisitor.objects.filter(first_visit__gte=start_date).count()
    unique_visitors = LandingPageVisitor.objects.filter(first_visit__gte=start_date).values('ip_address').distinct().count()
    returning_visitors = LandingPageVisitor.objects.filter(first_visit__gte=start_date, visit_count__gt=1).count()
    
    # Conversion metrics
    converted_visitors = LandingPageVisitor.objects.filter(
        first_visit__gte=start_date,
        converted_to_user=True
    ).count()
    conversion_rate = (converted_visitors / total_visitors * 100) if total_visitors > 0 else 0
    
    # Device breakdown
    device_stats = LandingPageVisitor.objects.filter(
        first_visit__gte=start_date
    ).values('device').annotate(count=Count('id')).order_by('-count')
    
    # Browser breakdown
    browser_stats = LandingPageVisitor.objects.filter(
        first_visit__gte=start_date
    ).values('browser').annotate(count=Count('id')).order_by('-count')
    
    # OS breakdown
    os_stats = LandingPageVisitor.objects.filter(
        first_visit__gte=start_date
    ).values('os').annotate(count=Count('id')).order_by('-count')
    
    # Top referrers (excluding empty)
    referrer_stats = LandingPageVisitor.objects.filter(
        first_visit__gte=start_date
    ).exclude(referrer='').values('referrer').annotate(count=Count('id')).order_by('-count')[:10]
    
    # UTM source breakdown
    utm_source_stats = LandingPageVisitor.objects.filter(
        first_visit__gte=start_date
    ).exclude(utm_source='').values('utm_source').annotate(count=Count('id')).order_by('-count')
    
    # UTM campaign breakdown
    utm_campaign_stats = LandingPageVisitor.objects.filter(
        first_visit__gte=start_date
    ).exclude(utm_campaign='').values('utm_campaign').annotate(count=Count('id')).order_by('-count')
    
    # Daily visitor trend (last 30 days)
    daily_visitors = []
    for i in range(days - 1, -1, -1):
        date = timezone.now().date() - timedelta(days=i)
        count = LandingPageVisitor.objects.filter(first_visit__date=date).count()
        daily_visitors.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    # Recent visitors (last 50)
    recent_visitors = LandingPageVisitor.objects.filter(
        first_visit__gte=start_date
    ).order_by('-last_visit')[:50]
    
    context = {
        'days': days,
        'total_visitors': total_visitors,
        'unique_visitors': unique_visitors,
        'returning_visitors': returning_visitors,
        'converted_visitors': converted_visitors,
        'conversion_rate': round(conversion_rate, 2),
        'device_stats': device_stats,
        'browser_stats': browser_stats,
        'os_stats': os_stats,
        'referrer_stats': referrer_stats,
        'utm_source_stats': utm_source_stats,
        'utm_campaign_stats': utm_campaign_stats,
        'daily_visitors': daily_visitors,
        'recent_visitors': recent_visitors,
    }
    
    return render(request, 'tracker/landing_analytics.html', context)


@login_required
def clear_all_notifications(request):
    """Delete all read notifications for the user."""
    from .models import UserNotification
    
    if request.method == 'POST':
        deleted_count = UserNotification.objects.filter(user=request.user, is_read=True).delete()[0]
        # Don't use messages.success here to avoid recursion
        return redirect('notifications_list')
    
    return redirect('notifications_list')
