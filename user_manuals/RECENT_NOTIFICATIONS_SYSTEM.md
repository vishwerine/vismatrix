# Recent Notifications System

## Overview
A persistent notification system that captures all Django success/error/info messages and stores them in the database for later viewing on a dedicated notifications page.

## Problem Solved
Previously, Django messages (toasts) would only appear once and disappear after being displayed. Users couldn't review past notifications or see what happened if they missed the toast. This system archives all notifications for persistent access.

## Features

### 1. Automatic Message Capture
All Django messages (`messages.success()`, `messages.error()`, etc.) are automatically intercepted by middleware and saved to the database.

### 2. Persistent Storage
Messages are stored in the `UserNotification` model with:
- User (who received it)
- Level (success/error/warning/info)
- Message content
- Read status
- Timestamps

### 3. Dedicated Notifications Page
**URL**: `/recent-notifications/`

Shows:
- All notifications with appropriate icons and colors
- "New" badge for unread notifications
- Time elapsed ("5 minutes ago")
- Clear read notifications button
- Empty state with helpful message

### 4. Navigation Integration
- Added to user profile dropdown menu
- Shows unread count badge
- Easy access from any page

### 5. Auto-Read Functionality
When user visits the notifications page, all notifications are automatically marked as read.

## Technical Implementation

### New Model: UserNotification
```python
- user: ForeignKey to User
- level: success/info/warning/error
- message: TextField (the actual message)
- is_read: Boolean
- created_at: DateTime
- read_at: DateTime (nullable)
```

### Middleware: SaveMessagesMiddleware
Location: `tracker/middleware.py`

**Function**: Intercepts Django messages after response is processed and saves them to database for authenticated users.

**How it works**:
1. User action triggers Django message (e.g., `messages.success(request, "Task completed!")`)
2. Middleware captures message before it's lost
3. Maps Django message levels to notification levels
4. Creates UserNotification record in database
5. Message still shows as normal toast (if enabled in base.html)

### Views Added

#### recent_notifications(request)
- Lists all notifications (limit 100)
- Auto-marks as read when viewed
- Context includes unread count

#### clear_all_notifications(request)
- POST endpoint
- Deletes all read notifications
- Returns JSON response

### URLs
```python
path("recent-notifications/", views.recent_notifications, name="recent_notifications")
path("notifications/clear-all/", views.clear_all_notifications, name="clear_all_notifications")
```

### Template: recent_notifications.html
Features:
- Icon-based display (✓ for success, ✗ for error, etc.)
- Color-coded badges
- Relative timestamps
- Empty state
- Clear button
- Link to mentorship notifications
- Responsive design

## Configuration

### Settings (progress_tracker/settings.py)
Added middleware to MIDDLEWARE list:
```python
'tracker.middleware.SaveMessagesMiddleware',
```

**Important**: Must be placed AFTER:
- `django.contrib.messages.middleware.MessageMiddleware`
- `django.contrib.auth.middleware.AuthenticationMiddleware`

## Migration
**Migration**: `0018_usernotification.py`

Creates UserNotification table with indexes on `(user, is_read, created_at)` for performance.

## Usage Examples

### In Views (No Changes Needed!)
```python
# Existing code continues to work
messages.success(request, "Activity logged successfully! +10 points")
messages.error(request, "Cannot delete this task")
messages.info(request, "You're not registered as a mentor yet")
messages.warning(request, "You've reached your maximum number of mentees")
```

All these messages are now automatically saved!

### In Templates
```django
<!-- Link to notifications page -->
<a href="{% url 'recent_notifications' %}">
  Notifications
  {% if unread_app_notifications_count > 0 %}
  <span class="badge">{{ unread_app_notifications_count }}</span>
  {% endif %}
</a>
```

## Admin Interface

### UserNotification Admin
- View all user notifications
- Filter by level, read status, date
- Search by user or message
- Preview messages (truncated to 50 chars)
- Sort by date (newest first)

## Differences from Mentorship Notifications

| Feature | UserNotification | Notification (Mentorship) |
|---------|-----------------|---------------------------|
| Purpose | App messages/toasts | Mentorship system events |
| Source | Django messages framework | Manual creation in code |
| Auto-created | Yes (middleware) | No (explicit code) |
| Page | `/recent-notifications/` | `/notifications-list/` |
| Linked objects | None | MentorshipRequest |
| Clearable | Yes | No |

## Benefits

1. **User Experience**
   - Never miss important notifications
   - Review past messages anytime
   - Clear notification history

2. **Debugging**
   - Track what messages users received
   - Verify notification delivery
   - Audit system messages

3. **No Code Changes**
   - Existing `messages.*` calls work as-is
   - Automatic capture via middleware
   - Zero refactoring needed

## Performance Considerations

- Lightweight middleware (only processes messages if they exist)
- Indexed queries for fast lookups
- Auto-cleanup via "Clear Read" button
- Limit display to 100 most recent

## Future Enhancements

Potential additions:
1. Push notifications for important messages
2. Email digest of unread notifications
3. Notification preferences (enable/disable types)
4. Export notification history
5. Advanced filtering (by date, level, keyword)
6. Notification grouping/threading

## Testing

### Manual Tests
- [ ] Create notification (log activity, complete task, etc.)
- [ ] Visit notifications page
- [ ] Verify notification appears
- [ ] Verify auto-read on page visit
- [ ] Clear read notifications
- [ ] Check unread badge in menu
- [ ] Verify empty state

### Edge Cases
- [ ] No notifications (empty state)
- [ ] 100+ notifications (pagination limit)
- [ ] Concurrent notifications
- [ ] Unauthenticated users (should not capture)

## Troubleshooting

### Messages not saving
- Check middleware is in settings.py
- Verify middleware is after MessageMiddleware
- Check user is authenticated

### Notifications not showing
- Verify migration applied (`0018_usernotification`)
- Check URL is accessible
- Verify user has notifications in admin

### Badge not updating
- Refresh page (badge updates on page load)
- Check context includes `unread_app_notifications_count`

## Files Modified

1. `models.py` - Added UserNotification model
2. `middleware.py` - Created SaveMessagesMiddleware
3. `views.py` - Added 2 views
4. `urls.py` - Added 2 URLs
5. `admin.py` - Registered UserNotification
6. `base.html` - Added notifications link with badge
7. `recent_notifications.html` - Created template
8. `settings.py` - Added middleware
