from django.urls import path
from . import views

urlpatterns = [
    # Existing HTML routes (keep them)
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("analytics/", views.analytics, name="analytics"),

    path("tasks/", views.task_list, name="task_list"),
    path("tasks/new/", views.task_create, name="task_create"),
    path("tasks/<int:pk>/edit/", views.task_update, name="task_update"),
    path("tasks/<int:pk>/complete/", views.task_complete, name="task_complete"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="task_delete"),

    path("logs/", views.log_list, name="log_list"),
    path("logs/new/", views.log_create, name="log_create"),
    path("logs/<int:pk>/edit/", views.log_update, name="log_update"),
    path("logs/<int:pk>/delete/", views.log_delete, name="log_delete"),

    path("progress/", views.progress_view, name="progress"),

    path("categories/", views.category_list, name="category_list"),
    path("categories/new/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),

    path("users/", views.user_list, name="user_list"),
    path("users/<int:user_id>/profile/", views.view_user_profile, name="view_user_profile"),
    path("friends/", views.friends_list, name="friends_list"),
    path("friends/<int:friendship_id>/profile/", views.view_friend_profile, name="view_friend_profile"),

    path("users/<int:user_id>/send_request/", views.send_friend_request, name="send_friend_request"),
    path("friends/requests/", views.friend_requests, name="friend_requests"),
    path("friends/requests/<int:request_id>/accept/", views.accept_friend_request, name="accept_friend_request"),
    path("friends/requests/<int:request_id>/reject/", views.reject_friend_request, name="reject_friend_request"),
    path("friends/requests/<int:user_id>/cancel/", views.cancel_friend_request, name="cancel_friend_request"),
    path("friends/<int:friendship_id>/remove/", views.remove_friend, name="remove_friend"),

    # Star reactions
    path("activities/toggle_star/", views.toggle_star_reaction, name="toggle_star_reaction"),

    # Notifications
    path("notifications/", views.notifications, name="notifications"),

    # Daily summary
    path("daily/<int:year>/<int:month>/<int:day>/", views.daily_summary, name="daily_summary"),

    # About page
    path("about/", views.about, name="about"),

    # Plans
    path("plans/", views.plan_list, name="plan_list"),
    path("plans/new/", views.plan_create, name="plan_create"),
    path("plans/<int:pk>/", views.plan_detail, name="plan_detail"),
    path("plans/<int:pk>/edit/", views.plan_update, name="plan_update"),
    path("plans/<int:pk>/delete/", views.plan_delete, name="plan_delete"),
    path("plans/<int:plan_pk>/add_task/", views.plan_node_add, name="plan_node_add"),
    path("plans/nodes/<int:pk>/edit/", views.plan_node_update, name="plan_node_update"),
    path("plans/nodes/<int:pk>/delete/", views.plan_node_delete, name="plan_node_delete"),
    path("plans/nodes/<int:pk>/add-dependency/", views.plan_node_add_dependency, name="plan_node_add_dependency"),
    path("plans/nodes/<int:pk>/update_position/", views.plan_node_update_position, name="plan_node_update_position"),

    path("messages/", views.inbox, name="inbox"),
    path("messages/start/<str:username>/", views.start_chat, name="start_chat"),
    path("messages/<int:conversation_id>/", views.conversation_detail, name="conversation_detail"),
        # mini chat json endpoints
    path("api/mini-chat/friends/", views.mini_chat_friends, name="mini_chat_friends"),
    path("api/mini-chat/<int:conversation_id>/messages/", views.mini_chat_messages, name="mini_chat_messages"),
    path("api/mini-chat/<int:conversation_id>/send/", views.mini_chat_send, name="mini_chat_send"),
    path("api/mini-chat/start/<int:friend_id>/", views.mini_chat_start, name="mini_chat_start"),

]
