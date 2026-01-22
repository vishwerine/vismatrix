"""
Pro-exclusive views for VisMatrix Pro subscribers.
All views in this module require an active Pro subscription.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from datetime import timedelta
import csv
import json
from decimal import Decimal

from .models import Task, DailyLog, Category, Plan, Habit, HabitCompletion, Subscription, PaymentHistory
from .decorators import pro_required
import logging

logger = logging.getLogger(__name__)


@login_required
@pro_required()
def export_data_csv(request):
    """Export all user data as CSV (Pro feature)."""
    user = request.user
    export_type = request.GET.get('type', 'tasks')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="vismatrix_{export_type}_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    if export_type == 'tasks':
        # Export tasks
        writer.writerow(['Title', 'Description', 'Status', 'Priority', 'Due Date', 'Created', 'Completed', 'Category', 'Estimated Duration', 'Actual Duration'])
        tasks = Task.objects.filter(user=user, is_global=False).select_related('category').order_by('-created_at')
        for task in tasks:
            writer.writerow([
                task.title,
                task.description or '',
                task.status,
                task.priority,
                task.due_date.strftime('%Y-%m-%d') if task.due_date else '',
                task.created_at.strftime('%Y-%m-%d %H:%M'),
                task.completed_at.strftime('%Y-%m-%d %H:%M') if task.completed_at else '',
                task.category.name if task.category else '',
                task.estimated_duration or '',
                task.actual_duration or ''
            ])
    
    elif export_type == 'logs':
        # Export daily logs
        writer.writerow(['Date', 'Activity', 'Duration (min)', 'Description', 'Category', 'Task'])
        logs = DailyLog.objects.filter(user=user).select_related('category', 'task').order_by('-date')
        for log in logs:
            writer.writerow([
                log.date.strftime('%Y-%m-%d'),
                log.activity,
                log.duration,
                log.description or '',
                log.category.name if log.category else '',
                log.task.title if log.task else ''
            ])
    
    elif export_type == 'habits':
        # Export habits
        writer.writerow(['Habit', 'Frequency', 'Active', 'Streak', 'Best Streak', 'Created', 'Completions'])
        habits = Habit.objects.filter(user=user).order_by('-created_at')
        for habit in habits:
            completions = HabitCompletion.objects.filter(habit=habit).count()
            writer.writerow([
                habit.name,
                habit.frequency,
                'Yes' if habit.is_active else 'No',
                habit.current_streak,
                habit.best_streak,
                habit.created_at.strftime('%Y-%m-%d'),
                completions
            ])
    
    elif export_type == 'analytics':
        # Export analytics summary
        writer.writerow(['Metric', 'Value'])
        
        total_tasks = Task.objects.filter(user=user, is_global=False).count()
        completed_tasks = Task.objects.filter(user=user, status='completed', is_global=False).count()
        total_logs = DailyLog.objects.filter(user=user).count()
        total_time = DailyLog.objects.filter(user=user).aggregate(total=Sum('duration'))['total'] or 0
        total_plans = Plan.objects.filter(user=user).count()
        active_plans = Plan.objects.filter(user=user, is_active=True).count()
        
        writer.writerow(['Total Tasks', total_tasks])
        writer.writerow(['Completed Tasks', completed_tasks])
        writer.writerow(['Completion Rate', f'{(completed_tasks/total_tasks*100):.1f}%' if total_tasks > 0 else '0%'])
        writer.writerow(['Total Logs', total_logs])
        writer.writerow(['Total Time Logged (hours)', f'{total_time/60:.1f}'])
        writer.writerow(['Total Plans', total_plans])
        writer.writerow(['Active Plans', active_plans])
        writer.writerow(['Export Date', timezone.now().strftime('%Y-%m-%d %H:%M')])
    
    logger.info(f"Pro user {user.username} exported {export_type} data as CSV")
    return response


@login_required
@pro_required()
def advanced_analytics(request):
    """Advanced analytics dashboard with detailed insights (Pro feature)."""
    user = request.user
    today = timezone.now().date()
    
    # Time range selection
    days = int(request.GET.get('days', 30))
    start_date = today - timedelta(days=days)
    
    # Advanced task insights
    task_stats = {
        'total': Task.objects.filter(user=user, is_global=False).count(),
        'completed': Task.objects.filter(user=user, status='completed', is_global=False).count(),
        'in_progress': Task.objects.filter(user=user, status='in_progress', is_global=False).count(),
        'pending': Task.objects.filter(user=user, status='pending', is_global=False).count(),
        'overdue': Task.objects.filter(user=user, status__in=['pending', 'in_progress'], due_date__lt=today, is_global=False).count(),
    }
    
    # Completion rate by priority
    priority_stats = []
    for priority in ['high', 'medium', 'low']:
        total = Task.objects.filter(user=user, priority=priority, is_global=False).count()
        completed = Task.objects.filter(user=user, priority=priority, status='completed', is_global=False).count()
        priority_stats.append({
            'priority': priority.capitalize(),
            'total': total,
            'completed': completed,
            'rate': (completed / total * 100) if total > 0 else 0
        })
    
    # Time analysis by category (last N days)
    category_time = DailyLog.objects.filter(
        user=user,
        date__gte=start_date
    ).values('category__name').annotate(
        total_time=Sum('duration'),
        log_count=Count('id')
    ).order_by('-total_time')[:10]
    
    # Daily productivity trend
    daily_trend = []
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        minutes = DailyLog.objects.filter(user=user, date=date).aggregate(total=Sum('duration'))['total'] or 0
        tasks_completed = Task.objects.filter(user=user, completed_at__date=date).count()
        daily_trend.append({
            'date': date.strftime('%Y-%m-%d'),
            'minutes': minutes,
            'tasks': tasks_completed
        })
    
    # Week-over-week comparison
    last_week_minutes = DailyLog.objects.filter(
        user=user,
        date__gte=today - timedelta(days=7),
        date__lte=today
    ).aggregate(total=Sum('duration'))['total'] or 0
    
    previous_week_minutes = DailyLog.objects.filter(
        user=user,
        date__gte=today - timedelta(days=14),
        date__lt=today - timedelta(days=7)
    ).aggregate(total=Sum('duration'))['total'] or 0
    
    week_change = ((last_week_minutes - previous_week_minutes) / previous_week_minutes * 100) if previous_week_minutes > 0 else 0
    
    # Convert to hours for template
    last_week_hours = round(last_week_minutes / 60, 1) if last_week_minutes else 0
    previous_week_hours = round(previous_week_minutes / 60, 1) if previous_week_minutes else 0
    
    # Average task completion time by category
    avg_completion_time = Task.objects.filter(
        user=user,
        status='completed',
        completed_at__isnull=False,
        is_global=False
    ).values('category__name').annotate(
        avg_time=Avg('actual_duration')
    ).order_by('-avg_time')[:5]
    
    # Habit success rate
    habit_success = []
    habits = Habit.objects.filter(user=user)
    for habit in habits:
        total_expected = (today - habit.created_at.date()).days
        total_completed = HabitCompletion.objects.filter(habit=habit).count()
        success_rate = (total_completed / total_expected * 100) if total_expected > 0 else 0
        habit_success.append({
            'name': habit.name,
            'success_rate': success_rate,
            'current_streak': habit.current_streak,
            'best_streak': habit.best_streak
        })
    
    # Peak productivity hours (from logs with time data)
    hour_productivity = [0] * 24  # Hours 0-23
    # Note: This would require storing time in logs, placeholder for now
    
    context = {
        'days': days,
        'start_date': start_date,
        'task_stats': task_stats,
        'priority_stats': priority_stats,
        'category_time': list(category_time),
        'daily_trend': daily_trend,
        'last_week_minutes': last_week_minutes,
        'last_week_hours': last_week_hours,
        'previous_week_minutes': previous_week_minutes,
        'previous_week_hours': previous_week_hours,
        'week_change': round(week_change, 1),
        'avg_completion_time': list(avg_completion_time),
        'habit_success': habit_success,
        'is_pro': True,
    }
    
    return render(request, 'tracker/pro_analytics.html', context)


@login_required
@pro_required()
def bulk_operations(request):
    """Bulk edit, delete, or complete multiple tasks/logs (Pro feature)."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            operation = data.get('operation')
            item_type = data.get('type')  # 'tasks' or 'logs'
            item_ids = data.get('ids', [])
            
            if not operation or not item_type or not item_ids:
                return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
            
            count = 0
            
            if item_type == 'tasks':
                tasks = Task.objects.filter(user=request.user, id__in=item_ids, is_global=False)
                
                if operation == 'delete':
                    count = tasks.count()
                    tasks.delete()
                    message = f'Deleted {count} tasks'
                
                elif operation == 'complete':
                    count = tasks.update(status='completed', completed_at=timezone.now())
                    message = f'Marked {count} tasks as complete'
                
                elif operation == 'reopen':
                    count = tasks.update(status='pending', completed_at=None)
                    message = f'Reopened {count} tasks'
                
                elif operation == 'update_priority':
                    priority = data.get('priority', 'medium')
                    count = tasks.update(priority=priority)
                    message = f'Updated priority for {count} tasks'
                
                elif operation == 'update_category':
                    category_id = data.get('category_id')
                    if category_id:
                        category = Category.objects.get(id=category_id, user=request.user)
                        count = tasks.update(category=category)
                        message = f'Updated category for {count} tasks'
                    else:
                        return JsonResponse({'success': False, 'error': 'Category required'}, status=400)
                
                else:
                    return JsonResponse({'success': False, 'error': 'Invalid operation'}, status=400)
            
            elif item_type == 'logs':
                logs = DailyLog.objects.filter(user=request.user, id__in=item_ids)
                
                if operation == 'delete':
                    count = logs.count()
                    logs.delete()
                    message = f'Deleted {count} logs'
                
                elif operation == 'update_category':
                    category_id = data.get('category_id')
                    if category_id:
                        category = Category.objects.get(id=category_id, user=request.user)
                        count = logs.update(category=category)
                        message = f'Updated category for {count} logs'
                    else:
                        return JsonResponse({'success': False, 'error': 'Category required'}, status=400)
                
                else:
                    return JsonResponse({'success': False, 'error': 'Invalid operation'}, status=400)
            
            else:
                return JsonResponse({'success': False, 'error': 'Invalid item type'}, status=400)
            
            logger.info(f"Pro user {request.user.username} performed bulk {operation} on {count} {item_type}")
            
            return JsonResponse({
                'success': True,
                'count': count,
                'message': message
            })
        
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Category.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Category not found'}, status=404)
        except Exception as e:
            logger.error(f"Error in bulk operations: {e}", exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)


@login_required
@pro_required()
def ai_categorize_task(request):
    """Use AI to automatically categorize a task (Pro feature)."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_id = data.get('task_id')
            
            if not task_id:
                return JsonResponse({'success': False, 'error': 'Task ID required'}, status=400)
            
            task = Task.objects.get(id=task_id, user=request.user, is_global=False)
            
            # Use the classifier service
            try:
                import sys
                sys.path.insert(0, '/Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix')
                from classifier_service import classify_text
                
                # Combine title and description for better classification
                text = f"{task.title}. {task.description or ''}"
                predicted_category = classify_text(text)
                
                # Find or create the category
                category, created = Category.objects.get_or_create(
                    user=request.user,
                    name=predicted_category,
                    defaults={'color': '#6366f1'}  # Default color
                )
                
                task.category = category
                task.save()
                
                logger.info(f"Pro user {request.user.username} used AI categorization for task {task_id}: {predicted_category}")
                
                return JsonResponse({
                    'success': True,
                    'category': predicted_category,
                    'category_id': category.id,
                    'message': f'Task categorized as: {predicted_category}'
                })
            
            except ImportError:
                return JsonResponse({
                    'success': False,
                    'error': 'AI classification service not available'
                }, status=503)
            except Exception as e:
                logger.error(f"Error in AI categorization: {e}", exc_info=True)
                return JsonResponse({
                    'success': False,
                    'error': 'Classification failed'
                }, status=500)
        
        except Task.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Task not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error in AI categorization endpoint: {e}", exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)


@login_required
@pro_required()
def pro_features_dashboard(request):
    """Dashboard showing all Pro features and usage stats."""
    user = request.user
    subscription = user.subscription
    
    # Calculate usage stats
    total_exports = 0  # Would track this with a model
    total_bulk_ops = 0  # Would track this with a model
    total_ai_classifications = 0  # Would track this with a model
    
    # Subscription info
    days_remaining = (subscription.current_period_end - timezone.now()).days if subscription.current_period_end else 0
    
    # Payment history
    payments = PaymentHistory.objects.filter(user=user).order_by('-created_at')[:5]
    
    context = {
        'subscription': subscription,
        'days_remaining': days_remaining,
        'payments': payments,
        'total_exports': total_exports,
        'total_bulk_ops': total_bulk_ops,
        'total_ai_classifications': total_ai_classifications,
    }
    
    return render(request, 'tracker/pro_dashboard.html', context)
