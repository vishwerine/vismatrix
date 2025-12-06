from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Tasks
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/new/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/edit/', views.task_update, name='task_update'),
    path('tasks/<int:pk>/complete/', views.task_complete, name='task_complete'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),

    # Daily logs
    path("logs/", views.log_list, name="log_list"),
    path("logs/new/", views.log_create, name="log_create"),
    path("logs/<int:pk>/edit/", views.log_update, name="log_update"),
    path("logs/<int:pk>/delete/", views.log_delete, name="log_delete"),

    # Progress
    path('progress/', views.progress_view, name='progress'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Social/Friends URLs
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/profile/', views.view_user_profile, name='view_user_profile'),
    path('friends/', views.friends_list, name='friends_list'),
    path('friends/<int:friendship_id>/profile/', views.view_friend_profile, name='view_friend_profile'),

    # Friend Request URLs - AJAX ENABLED
    path('users/<int:user_id>/send_request/', views.send_friend_request, name='send_friend_request'),
    path('friends/requests/', views.friend_requests, name='friend_requests'),
    path('friends/requests/<int:request_id>/accept/', views.accept_friend_request, name='accept_friend_request'),
    path('friends/requests/<int:request_id>/reject/', views.reject_friend_request, name='reject_friend_request'),
    path('friends/requests/<int:user_id>/cancel/', views.cancel_friend_request, name='cancel_friend_request'),
    path('friends/<int:friendship_id>/remove/', views.remove_friend, name='remove_friend'),
]
