from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'tasks', api_views.TaskViewSet, basename='task')
router.register(r'logs', api_views.DailyLogViewSet, basename='dailylog')
router.register(r'categories', api_views.CategoryViewSet, basename='category')
router.register(r'plans', api_views.PlanViewSet, basename='plan')

urlpatterns = [
    # Auth endpoints
    path('auth/csrf/', api_views.api_csrf, name='api_csrf'),
    path('auth/login/', api_views.api_login, name='api_login'),
    path('auth/logout/', api_views.api_logout, name='api_logout'),
    path('auth/user/', api_views.api_current_user, name='api_current_user'),
    
    # Dashboard
    path('dashboard/', api_views.api_dashboard, name='api_dashboard'),
    
    # Analytics
    path('analytics/', api_views.api_analytics, name='api_analytics'),
    
    # Users and friends
    path('users/', api_views.api_users, name='api_users'),
    path('users/<int:user_id>/send_request/', api_views.api_send_friend_request, name='api_send_friend_request'),
    path('friends/', api_views.api_friends, name='api_friends'),
    path('friends/requests/', api_views.api_friend_requests, name='api_friend_requests'),
    path('friends/requests/<int:request_id>/accept/', api_views.api_accept_friend_request, name='api_accept_friend_request'),
    path('friends/requests/<int:request_id>/reject/', api_views.api_reject_friend_request, name='api_reject_friend_request'),
    path('friends/<int:friendship_id>/remove/', api_views.api_remove_friend, name='api_remove_friend'),
    
    # Router URLs (tasks, logs, categories, plans)
    path('', include(router.urls)),
]
