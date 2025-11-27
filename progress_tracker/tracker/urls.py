from django.urls import path
from . import views

urlpatterns = [
    # REMOVE these three lines:
    # path('register/', views.register_view, name='register'),
    # path('login/', views.login_view, name='login'),
    # path('logout/', views.logout_view, name='logout'),
    
    # Keep everything else:
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Tasks
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/new/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/edit/', views.task_update, name='task_update'),
    path('tasks/<int:pk>/complete/', views.task_complete, name='task_complete'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    
    # Daily logs
    path('logs/', views.log_list, name='log_list'),
    path('logs/new/', views.log_create, name='log_create'),
    
    # Progress
    path('progress/', views.progress_view, name='progress'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Social URLs
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/add_friend/', views.add_friend, name='add_friend'),
    path('users/<int:user_id>/remove_friend/', views.remove_friend, name='remove_friend'),
    path('friends/progress/', views.friend_progress_list, name='friend_progress_list'),
    path('friends/<int:friend_id>/progress/', views.view_friend_progress, name='view_friend_progress'),


    # Social/Friends URLs
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/send_request/', views.send_friend_request, name='send_friend_request'),
    path('users/<int:user_id>/cancel_request/', views.cancel_friend_request, name='cancel_friend_request'),
    path('users/<int:user_id>/remove_friend/', views.remove_friend, name='remove_friend'),
    path('friend-requests/', views.friend_requests, name='friend_requests'),
    path('friend-requests/<int:request_id>/accept/', views.accept_friend_request, name='accept_friend_request'),
    path('friend-requests/<int:request_id>/reject/', views.reject_friend_request, name='reject_friend_request'),
    path('friends/', views.friends_list, name='friends_list'),
    path('friends/<int:friend_id>/profile/', views.view_friend_profile, name='view_friend_profile'),
]

