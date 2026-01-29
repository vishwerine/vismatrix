# User Profile & Activity Feed Feature

## Overview

This feature adds personal user profiles where users can view their latest activities (completed tasks, logged activities, completed habits) with privacy controls. These activities automatically appear in friends' timelines based on visibility settings.

## Features Implemented

### 1. **User Profile Page** (`/my-profile/`)
- View your own profile with avatar, username, member since date
- See statistics: total activities, today's activities, friends count, pending requests
- Display recent activity feed with pagination
- Quick access to recent tasks, logs, and habits in sidebar

### 2. **Activity Visibility Control**
Users can set visibility for each activity:
- **Private** (🔒): Only visible to the user
- **Friends Only** (👥): Visible to accepted friends only
- **Public** (🌐): Visible to everyone

Click on the privacy badge on any activity to change visibility.

### 3. **User Timeline** (`/users/<user_id>/profile/timeline/`)
- View another user's public activity timeline
- If you're friends, see their "friends only" activities
- If you're not friends, see only "public" activities
- Shows friend status and options to add friend/send request

### 4. **Automatic Activity Creation**
- Completed tasks → Activity entry
- Created daily logs → Activity entry
- Completed habits → Activity entry
- All automatically tracked via Django signals

## Database Schema

### New Model: `UserActivity`

```python
class UserActivity(models.Model):
    user = ForeignKey(User)
    activity_type = CharField(choices=[
        'task_completed',
        'log_created',
        'habit_completed',
        'post_created'
    ])
    
    # Generic relations to any activity object
    task = ForeignKey(Task, null=True, blank=True)
    daily_log = ForeignKey(DailyLog, null=True, blank=True)
    habit_completion = ForeignKey(HabitCompletion, null=True, blank=True)
    blog_post = ForeignKey(BlogPost, null=True, blank=True)
    
    # Privacy control
    visibility = CharField(choices=[
        'private',    # Only user
        'friends',    # Friends only
        'public'      # Everyone
    ], default='friends')
    
    created_at = DateTimeField(auto_now_add=True)
    activity_date = DateField(auto_now_add=True)
```

### Updated Models

#### Task
- Added `visibility` field (choices: private/friends/public, default: friends)

#### DailyLog
- Added `visibility` field (choices: private/friends/public, default: friends)

## URLs

| Route | View | Purpose |
|-------|------|---------|
| `/my-profile/` | `my_profile()` | User's own profile page |
| `/my-profile/activity/<id>/toggle-privacy/` | `toggle_activity_privacy()` | AJAX endpoint to change activity visibility |
| `/users/<user_id>/profile/timeline/` | `user_timeline()` | View another user's timeline |

## Views

### `my_profile(request)`
**Location**: `profile_views.py`

**Purpose**: Display logged-in user's profile with their activities

**Features**:
- Fetches user's activities sorted by recent
- Calculates stats (total, today's, friends count)
- Shows recent tasks, logs, habits from past 7 days
- Paginated activity feed (20 per page)

**Context Variables**:
- `profile_user`: Current user
- `activities`: Paginated UserActivity objects
- `total_activities`: Total count
- `today_activities`: Activities created today
- `recent_tasks`: Last 5 completed tasks (7 days)
- `recent_logs`: Last 5 activity logs (7 days)
- `recent_habits`: Last 5 habit completions (7 days)
- `friends_count`: Number of accepted friendships
- `pending_requests`: Number of pending friend requests
- `is_own_profile`: True (always for this view)

### `toggle_activity_privacy(request, activity_id)`
**Location**: `profile_views.py`

**Method**: POST (AJAX)

**Purpose**: Change privacy setting of an activity

**Parameters**:
- `visibility`: 'private', 'friends', or 'public'

**Returns**: JSON
```json
{
  "success": true,
  "message": "Activity set to friends",
  "new_visibility": "friends",
  "visibility_display": "Friends (Visible to friends only)"
}
```

### `user_timeline(request, user_id)`
**Location**: `profile_views.py`

**Purpose**: View another user's activity timeline with privacy controls

**Features**:
- Checks friendship status with target user
- Applies visibility filters based on relationship:
  - Own profile: See all activities
  - Friend: See 'friends' and 'public' activities
  - Non-friend: See only 'public' activities
- Shows friend status and friend action buttons
- Paginated feed (20 per page)

**Context Variables**:
- `profile_user`: Target user
- `activities`: Filtered UserActivity objects
- `is_own_profile`: True/False
- `is_friend`: True/False
- `friendship`: Friendship object (if friends)
- `friend_request_sent`: True/False

## Signals

Auto-matically create activity entries when:

### Task Completion
```python
@receiver(post_save, sender=Task)
def create_activity_on_task_completion(sender, instance, created, **kwargs):
    # Creates UserActivity when task.completed_at is set
    # Inherits visibility from task.visibility
```

### Daily Log Creation
```python
@receiver(post_save, sender=DailyLog)
def create_activity_on_daily_log(sender, instance, created, **kwargs):
    # Creates UserActivity when DailyLog is created
    # Inherits visibility from log.visibility
```

### Habit Completion
```python
@receiver(post_save, sender=HabitCompletion)
def create_activity_on_habit_completion(sender, instance, created, **kwargs):
    # Creates UserActivity when habit is marked complete
    # Always uses 'friends' visibility (customizable)
```

## Templates

### `my_profile.html`
**Purpose**: User's personal profile page

**Key Sections**:
- Header: Avatar, name, member since, settings button
- Stats Grid: Total activities, today's, friends, pending requests
- Main Content (2/3 width):
  - Recent activity feed with icons
  - Privacy dropdown on each activity
  - Pagination controls
- Sidebar (1/3 width):
  - Recent tasks (with link to full list)
  - Recent logs (with link to full list)
  - Recent habits (with link to full list)

**Styling**:
- Activity cards with left border accent
- Hover effects
- Color-coded privacy badges
- Icons for activity types (checkmark for tasks, clock for logs, repeat for habits)

### `user_timeline.html`
**Purpose**: View another user's activity timeline

**Key Sections**:
- Header: User's avatar, name, friend status
- Friend action buttons (Add Friend / Request Sent / Friends badge)
- Activity feed (privacy-filtered)
- Privacy notice explaining what activities they can see
- Pagination controls

**Privacy Messaging**:
- If viewing own profile: "No activities yet. Start tracking your progress!"
- If friend: "You're viewing this user's activities. They have set some activities to be visible only to friends."
- If not friend: "You're viewing only public activities shared by this user. Add them as a friend to see more activities."

## Usage Examples

### For Users

**View My Profile**:
1. Click "My Profile" in navigation
2. See all your activities and stats
3. Click privacy badge to change visibility of any activity

**View Friend's Timeline**:
1. Go to friend's profile
2. Click "Timeline" tab (or visit `/users/<id>/profile/timeline/`)
3. See their shared activities (respecting privacy settings)

**Hide Activity from Friends**:
1. On your profile, find the activity
2. Click the privacy badge (Friends/Public/Private)
3. Select "Private (Only me)"
4. Activity no longer shows in friends' timelines

### For Developers

**Create Activity Manually**:
```python
from tracker.profile_views import create_user_activity

create_user_activity(
    user=request.user,
    activity_type='task_completed',
    task=my_task,
    visibility='friends'
)
```

**Query Activities**:
```python
# Get all public activities
public_activities = UserActivity.objects.filter(visibility='public')

# Get friend-visible activities for user
friend_activities = UserActivity.objects.filter(
    user=friend_user,
    visibility__in=['friends', 'public']
)

# Get today's activities for a user
today_activities = UserActivity.objects.filter(
    user=user,
    activity_date=today
)
```

## Migration Steps

1. Run migrations to create `UserActivity` model and add visibility fields to Task/DailyLog:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. Restart application for signals to take effect

3. New activities will be automatically created going forward

4. To populate existing activities (optional), run command:
   ```python
   # In Django shell or management command
   from tracker.models import Task, DailyLog, HabitCompletion, UserActivity
   
   # Create activities for past completed tasks
   for task in Task.objects.filter(completed_at__isnull=False):
       UserActivity.objects.get_or_create(
           task=task,
           activity_type='task_completed',
           defaults={'user': task.user, 'visibility': task.visibility}
       )
   ```

## Privacy & Security

### Visibility Rules Enforced

1. **Private Activities**:
   - Only visible to the owner
   - Not queryable via `user_timeline()` for other users

2. **Friends Activities**:
   - Visible to accepted friends only
   - Checked via `Friendship` model with status='accepted'

3. **Public Activities**:
   - Visible to everyone
   - No relationship required

### Database-Level Protections

- Each activity tied to specific user
- Visibility setting persisted per activity
- Friend relationship must exist (status='accepted')
- Queries filtered before response

## Future Enhancements

1. **Activity Feed Notifications**:
   - Notify users when friends complete activities
   - Configurable notification preferences

2. **Activity Reactions**:
   - Like/star/react to friends' activities
   - Reaction counts and activity popularity

3. **Activity Filtering**:
   - Filter by activity type (tasks, logs, habits)
   - Filter by date range
   - Filter by category

4. **Activity Sharing**:
   - Share activities on external social media
   - Generate activity reports/summaries

5. **Leaderboards**:
   - Most active users
   - Most completed tasks/habits
   - Community achievements

## Support

For issues or feature requests, contact the development team or open an issue in the project repository.
