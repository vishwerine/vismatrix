from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum, Count
from django.middleware.csrf import get_token
from datetime import timedelta

from .models import Task, DailyLog, Category, DailySummary, FriendRequest, Friendship, Plan, PlanNode
from .serializers import (
    TaskSerializer, DailyLogSerializer, CategorySerializer, 
    DailySummarySerializer, FriendRequestSerializer, FriendshipSerializer,
    PlanSerializer, PlanNodeSerializer, UserSerializer
)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_csrf(request):
    """Get CSRF token"""
    csrf_token = get_token(request)
    return Response({'csrfToken': csrf_token})


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """API endpoint for user login"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return Response({
            'success': True,
            'user': UserSerializer(user).data
        })
    return Response({
        'success': False,
        'error': 'Invalid credentials'
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """API endpoint for user logout"""
    logout(request)
    return Response({'success': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_current_user(request):
    """Get current authenticated user"""
    return Response(UserSerializer(request.user).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_dashboard(request):
    """API endpoint for dashboard data"""
    today = timezone.now().date()
    recent_log = DailyLog.objects.filter(user=request.user).order_by('-date').first()
    base_date = recent_log.date if recent_log else today
    week_ago = base_date - timedelta(days=6)
    
    # Today's stats
    today_tasks = Task.objects.filter(user=request.user, created_at__date=today)
    today_tasks_count = today_tasks.count()
    today_completed = today_tasks.filter(status="completed").count()
    
    today_logs = DailyLog.objects.filter(user=request.user, date=today)
    today_time = today_logs.aggregate(total=Sum("duration"))["total"] or 0
    
    # Pending tasks
    pending_tasks = Task.objects.filter(
        user=request.user,
        status__in=["pending", "in_progress"]
    ).order_by('-priority', 'due_date')[:10]
    
    # Weekly stats
    weekly_logs = DailyLog.objects.filter(user=request.user, date__gte=week_ago)
    weekly_total_time = weekly_logs.aggregate(total=Sum("duration"))["total"] or 0
    
    # Recent activities
    recent_activities = DailyLog.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Friend activities
    friend_activities = []
    friendships = Friendship.objects.filter(user=request.user) | Friendship.objects.filter(friend=request.user)
    for friendship in friendships[:5]:
        friend = friendship.friend if friendship.user == request.user else friendship.user
        friend_logs = DailyLog.objects.filter(user=friend, date__gte=week_ago).order_by('-created_at')[:3]
        if friend_logs:
            friend_activities.append({
                'friend': UserSerializer(friend).data,
                'activities': DailyLogSerializer(friend_logs, many=True).data
            })
    
    return Response({
        'today_tasks_count': today_tasks_count,
        'today_completed': today_completed,
        'today_time': today_time,
        'pending_tasks': TaskSerializer(pending_tasks, many=True).data,
        'weekly_logs': DailyLogSerializer(weekly_logs, many=True).data,
        'weekly_total_time': weekly_total_time,
        'recent_activities': DailyLogSerializer(recent_activities, many=True).data,
        'friend_activities': friend_activities,
    })


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = 'completed'
        task.save()
        return Response(TaskSerializer(task).data)


class DailyLogViewSet(viewsets.ModelViewSet):
    serializer_class = DailyLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DailyLog.objects.filter(user=self.request.user).order_by('-date', '-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Category.objects.filter(user=self.request.user) | Category.objects.filter(is_global=True)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PlanViewSet(viewsets.ModelViewSet):
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Plan.objects.filter(user=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_users(request):
    """Get list of all users for friend requests"""
    users = User.objects.exclude(id=request.user.id)
    return Response(UserSerializer(users, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_friends(request):
    """Get user's friends"""
    friendships = Friendship.objects.filter(user1=request.user) | Friendship.objects.filter(user2=request.user)
    return Response(FriendshipSerializer(friendships, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_send_friend_request(request, user_id):
    """Send friend request"""
    try:
        to_user = User.objects.get(id=user_id)
        friend_request, created = FriendRequest.objects.get_or_create(
            from_user=request.user,
            to_user=to_user,
            defaults={'status': 'pending'}
        )
        if created:
            return Response({'success': True, 'message': 'Friend request sent'})
        return Response({'success': False, 'message': 'Request already exists'}, status=status.HTTP_400_BAD_REQUEST)
    except User.DoesNotExist:
        return Response({'success': False, 'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_friend_requests(request):
    """Get pending friend requests"""
    requests_received = FriendRequest.objects.filter(to_user=request.user, status='pending')
    requests_sent = FriendRequest.objects.filter(from_user=request.user, status='pending')
    
    return Response({
        'received': FriendRequestSerializer(requests_received, many=True).data,
        'sent': FriendRequestSerializer(requests_sent, many=True).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_accept_friend_request(request, request_id):
    """Accept friend request"""
    try:
        friend_request = FriendRequest.objects.get(id=request_id, to_user=request.user)
        friend_request.status = 'accepted'
        friend_request.save()
        
        # Create friendship
        Friendship.objects.create(user1=request.user, user2=friend_request.from_user)
        
        return Response({'success': True, 'message': 'Friend request accepted'})
    except FriendRequest.DoesNotExist:
        return Response({'success': False, 'message': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_reject_friend_request(request, request_id):
    """Reject friend request"""
    try:
        friend_request = FriendRequest.objects.get(id=request_id, to_user=request.user)
        friend_request.status = 'rejected'
        friend_request.save()
        return Response({'success': True, 'message': 'Friend request rejected'})
    except FriendRequest.DoesNotExist:
        return Response({'success': False, 'message': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_remove_friend(request, friendship_id):
    """Remove friend"""
    try:
        friendship = Friendship.objects.get(
            id=friendship_id
        ).filter(user1=request.user) | Friendship.objects.filter(user2=request.user)
        friendship.delete()
        return Response({'success': True, 'message': 'Friend removed'})
    except Friendship.DoesNotExist:
        return Response({'success': False, 'message': 'Friendship not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_analytics(request):
    """API endpoint for analytics data"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=6)
    
    # Task statistics
    total_tasks = Task.objects.filter(user=request.user).count()
    completed_tasks = Task.objects.filter(user=request.user, status='completed').count()
    pending_tasks = Task.objects.filter(user=request.user, status__in=['pending', 'in_progress']).count()
    
    # Time statistics from daily logs
    all_logs = DailyLog.objects.filter(user=request.user)
    total_time_logged = all_logs.aggregate(total=Sum('duration'))['total'] or 0
    
    # Average daily time
    unique_days = all_logs.values('date').distinct().count()
    avg_daily_time = total_time_logged / unique_days if unique_days > 0 else 0
    
    # Most productive day (day with most time logged)
    most_productive = all_logs.values('date').annotate(
        day_total=Sum('duration')
    ).order_by('-day_total').first()
    most_productive_day = most_productive['date'] if most_productive else None
    
    # Categories breakdown
    categories_breakdown = []
    categories = Category.objects.filter(user=request.user) | Category.objects.filter(is_global=True)
    for category in categories:
        logs = all_logs.filter(category=category)
        count = logs.count()
        if count > 0:
            total_time = logs.aggregate(total=Sum('duration'))['total'] or 0
            categories_breakdown.append({
                'category_name': category.name,
                'count': count,
                'total_time': total_time
            })
    
    # Uncategorized logs
    uncategorized_logs = all_logs.filter(category__isnull=True)
    uncategorized_count = uncategorized_logs.count()
    if uncategorized_count > 0:
        uncategorized_time = uncategorized_logs.aggregate(total=Sum('duration'))['total'] or 0
        categories_breakdown.append({
            'category_name': 'Uncategorized',
            'count': uncategorized_count,
            'total_time': uncategorized_time
        })
    
    # Weekly stats (last 7 days)
    weekly_stats = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_logs = all_logs.filter(date=day)
        day_tasks = Task.objects.filter(user=request.user, completed_at__date=day, status='completed')
        
        weekly_stats.append({
            'date': day.isoformat(),
            'tasks_completed': day_tasks.count(),
            'time_spent': day_logs.aggregate(total=Sum('duration'))['total'] or 0
        })
    
    return Response({
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'total_time_logged': total_time_logged,
        'avg_daily_time': int(avg_daily_time),
        'most_productive_day': most_productive_day.isoformat() if most_productive_day else None,
        'categories_breakdown': categories_breakdown,
        'weekly_stats': weekly_stats
    })
