from django.urls import path
from . import views

urlpatterns = [
    # Public landing page
    path("", views.landing_page, name="landing_page"),
    # Dashboard (requires login)
    path("dashboard/", views.dashboard, name="dashboard"),
    path("analytics/", views.analytics, name="analytics"),
    path("day-planner/", views.day_planner, name="day_planner"),
    
    # Quickstart
    path("quickstart/", views.quickstart, name="quickstart"),
    path("quickstart/create/<str:plan_type>/", views.quickstart_create_plan, name="quickstart_create_plan"),
    path("quickstart/habit/<str:habit_type>/", views.quickstart_create_habit, name="quickstart_create_habit"),

    path("tasks/", views.task_list, name="task_list"),
    path("tasks/new/", views.task_create, name="task_create"),
    path("tasks/<int:pk>/edit/", views.task_update, name="task_update"),
    path("tasks/<int:pk>/complete/", views.task_complete, name="task_complete"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="task_delete"),
    path("tasks/<int:pk>/timer/", views.task_timer, name="task_timer"),
    
    # Timer API
    path("api/timer/save-log/", views.save_timer_log, name="save_timer_log"),
    path("api/timer/create-session/", views.create_timer_session, name="create_timer_session"),
    path("api/timer/session/<str:session_code>/participants/", views.get_session_participants, name="get_session_participants"),
    path("api/timer/session/<str:session_code>/state/", views.get_session_state, name="get_session_state"),
    path("api/timer/session/<str:session_code>/update/", views.update_session_state, name="update_session_state"),
    path("api/timer/session/<str:session_code>/end/", views.end_timer_session, name="end_timer_session"),
    path("api/timer/session/<str:session_code>/leave/", views.leave_timer_session, name="leave_timer_session"),

    path("logs/", views.log_list, name="log_list"),
    path("logs/new/", views.log_create, name="log_create"),
    path("logs/<int:pk>/edit/", views.log_update, name="log_update"),
    path("logs/<int:pk>/delete/", views.log_delete, name="log_delete"),
    path("logs/quick/", views.quick_log_activity, name="quick_log_activity"),
    
    # Habits
    path("habits/", views.habit_list, name="habit_list"),
    path("habits/new/", views.habit_create, name="habit_create"),
    path("habits/<int:pk>/edit/", views.habit_update, name="habit_update"),
    path("habits/<int:pk>/delete/", views.habit_delete, name="habit_delete"),
    path("habits/<int:pk>/complete/", views.habit_complete, name="habit_complete"),
    path("habits/<int:pk>/toggle-active/", views.habit_toggle_active, name="habit_toggle_active"),
    
    # Day schedule API endpoints
    path("api/day-schedule/save/", views.save_day_schedule, name="save_day_schedule"),
    path("api/day-schedule/smart-schedule/", views.smart_schedule_tasks, name="smart_schedule_tasks"),
    path("api/day-schedule/complete-habit/", views.complete_habit_from_planner, name="complete_habit_from_planner"),
    path("api/day-schedule/<str:schedule_date>/", views.load_day_schedule, name="load_day_schedule"),

    path("progress/", views.progress_view, name="progress"),

    path("categories/", views.category_list, name="category_list"),
    path("categories/new/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),

    path("users/", views.user_list, name="user_list"),
    path("users/<int:user_id>/profile/", views.view_user_profile, name="view_user_profile"),
    path("friends/", views.friends_list, name="friends_list"),
    path("friends/feed/", views.friends_feed, name="friends_feed"),
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

    # About, Privacy & Terms
    path("about/", views.about, name="about"),
    path("privacy/", views.privacy_policy, name="privacy_policy"),
    path("terms/", views.terms_of_service, name="terms_of_service"),

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
    
    # Plan sharing
    path("plans/<int:pk>/toggle_sharing/", views.plan_toggle_sharing, name="plan_toggle_sharing"),
    path("plans/<int:pk>/regenerate_token/", views.plan_regenerate_token, name="plan_regenerate_token"),
    path("shared/plan/<str:token>/", views.shared_plan_view, name="shared_plan"),

    path("messages/", views.inbox, name="inbox"),
    path("messages/start/<str:username>/", views.start_chat, name="start_chat"),
    path("messages/<int:conversation_id>/", views.conversation_detail, name="conversation_detail"),
        # mini chat json endpoints
    path("api/mini-chat/friends/", views.mini_chat_friends, name="mini_chat_friends"),
    path("api/mini-chat/<int:conversation_id>/messages/", views.mini_chat_messages, name="mini_chat_messages"),
    path("api/mini-chat/<int:conversation_id>/send/", views.mini_chat_send, name="mini_chat_send"),
    
    # User settings
    path("api/user/set-timezone/", views.set_user_timezone, name="set_user_timezone"),
    path("profile/settings/", views.profile_settings, name="profile_settings"),
    path("api/mini-chat/start/<int:friend_id>/", views.mini_chat_start, name="mini_chat_start"),

    # Google Calendar Integration
    path("calendar/settings/", views.calendar_settings, name="calendar_settings"),
    path("calendar/connect/", views.calendar_connect, name="calendar_connect"),
    path("calendar/oauth2callback/", views.calendar_oauth_callback, name="calendar_oauth_callback"),
    path("calendar/disconnect/", views.calendar_disconnect, name="calendar_disconnect"),
    path("calendar/sync/", views.calendar_sync_now, name="calendar_sync_now"),
    path("calendar/update_settings/", views.calendar_update_settings, name="calendar_update_settings"),
    path("api/calendar/list/", views.calendar_list_calendars, name="calendar_list_calendars"),

    # iCloud Calendar Integration
    path("calendar/icloud/connect/", views.icloud_calendar_connect, name="icloud_calendar_connect"),
    path("calendar/icloud/disconnect/", views.icloud_calendar_disconnect, name="icloud_calendar_disconnect"),
    path("calendar/icloud/sync/", views.icloud_calendar_sync, name="icloud_calendar_sync"),
    path("calendar/icloud/update_settings/", views.icloud_calendar_update_settings, name="icloud_calendar_update_settings"),

    # Profile Settings
    path("profile/settings/", views.profile_settings, name="profile_settings"),
    path("profile/download-data/", views.download_user_data, name="download_user_data"),
    path("profile/delete-account/", views.delete_account, name="delete_account"),

    # Mentorship
    path("mentors/", views.mentor_list, name="mentor_list"),
    path("mentors/<int:mentor_id>/", views.mentor_profile_view, name="mentor_profile"),
    path("mentors/<int:mentor_id>/apply/", views.apply_for_mentorship, name="apply_for_mentorship"),
    path("mentor/become/", views.become_mentor, name="become_mentor"),
    path("mentor/dashboard/", views.mentor_dashboard, name="mentor_dashboard"),
    path("mentor/requests/<int:request_id>/respond/", views.respond_to_mentorship_request, name="respond_to_mentorship_request"),
    path("mentor/requests/<int:request_id>/complete/", views.complete_mentorship, name="complete_mentorship"),
    path("my-mentorships/", views.my_mentorships, name="my_mentorships"),
    
    # Notifications
    path("notifications-list/", views.notifications_list, name="notifications_list"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("api/notifications/unread-count/", views.get_unread_notification_count, name="unread_notification_count"),
    
    # Recent Notifications (Django messages)
    path("recent-notifications/", views.recent_notifications, name="recent_notifications"),
    path("notifications/clear-all/", views.clear_all_notifications, name="clear_all_notifications"),
    
    # Landing Page Analytics (Admin only)
    path("admin-analytics/landing/", views.landing_analytics, name="landing_analytics"),

]
