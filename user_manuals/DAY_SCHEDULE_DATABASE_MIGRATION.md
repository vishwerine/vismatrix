# Day Schedule Database Migration

## Overview
Migrated the day planner schedule persistence from client-side localStorage to server-side database storage using Django models.

## Changes Made

### 1. Database Model (tracker/models.py)
Created a new `DaySchedule` model to store user schedules:

```python
class DaySchedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='day_schedules', db_index=True)
    date = models.DateField(db_index=True)
    title = models.CharField(max_length=255, blank=True, default='')
    events_data = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['user', 'date']]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', 'date']),
        ]
```

**Features:**
- User-specific schedules
- Date-based storage
- Custom title for each day
- JSON storage for events array
- Unique constraint on (user, date) to prevent duplicates
- Indexed for fast querying

### 2. API Endpoints (tracker/views.py)

Added two new AJAX endpoints:

#### Save Schedule
- **URL**: `/api/day-schedule/save/`
- **Method**: POST
- **Payload**: 
  ```json
  {
    "date": "2025-01-15",
    "title": "My Day Plan",
    "events": [
      {
        "id": 1,
        "title": "Task Name",
        "startMin": 540,
        "endMin": 600,
        "logged": false,
        "planNames": ["Project A"]
      }
    ]
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Schedule saved successfully",
    "schedule_id": 123
  }
  ```

#### Load Schedule
- **URL**: `/api/day-schedule/<date>/`
- **Method**: GET
- **Response**:
  ```json
  {
    "success": true,
    "date": "2025-01-15",
    "title": "My Day Plan",
    "events": [...]
  }
  ```

### 3. URL Configuration (tracker/urls.py)

Added new routes:
```python
path("api/day-schedule/save/", views.save_day_schedule, name="save_day_schedule"),
path("api/day-schedule/<str:schedule_date>/", views.load_day_schedule, name="load_day_schedule"),
```

### 4. Frontend Migration (tracker/templates/tracker/day_planner.html)

#### Removed:
- `getStorageKey()` function
- `getTitleKey()` function
- localStorage.getItem/setItem calls

#### Updated:
- `load()` - Now async, fetches from API
- `save()` - Now async, posts to API
- `changeDate()` - Now async to await load()
- Date navigation button handlers - Updated to async
- Initial page load - Uses promise chain for async load

#### Example Changes:

**Before (localStorage):**
```javascript
function load() {
  const raw = localStorage.getItem(getStorageKey());
  events = raw ? JSON.parse(raw) : [];
}

function save() {
  localStorage.setItem(getStorageKey(), JSON.stringify(events));
}
```

**After (Database API):**
```javascript
async function load() {
  const response = await fetch(`/api/day-schedule/${currentDate}/`, {
    headers: { 'X-CSRFToken': getCookie('csrftoken') }
  });
  const data = await response.json();
  if (data.success) {
    events = data.events || [];
    dayTitleEl.value = data.title || defaultTitle;
  }
}

async function save() {
  await fetch('/api/day-schedule/save/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({
      date: currentDate,
      title: dayTitleEl.value.trim(),
      events: events
    })
  });
}
```

### 5. Admin Interface (tracker/admin.py)

Added admin registration for easy management:
```python
@admin.register(DaySchedule)
class DayScheduleAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'title', 'created_at', 'updated_at']
    list_filter = ['user', 'date']
    search_fields = ['user__username', 'title']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-date']
```

## Migration Steps

1. **Created Migration**: `python manage.py makemigrations tracker`
   - Generated: `0014_dayschedule.py`

2. **Applied Migration**: `python manage.py migrate tracker`
   - Created DaySchedule table with proper indexes

## Benefits of Database Storage

1. **Persistence**: Schedules survive browser cache clearing
2. **Multi-device**: Access schedules from any device
3. **Backup**: Server-side data backup
4. **Security**: Data stored securely on server
5. **Sharing**: Future potential for schedule sharing
6. **Analytics**: Can track schedule patterns over time
7. **History**: Automatic timestamps for created/updated

## Testing

To test the changes:

1. Navigate to `/day-planner/`
2. Create a schedule with events
3. Refresh the page - schedule should persist
4. Navigate to previous/next days - each day maintains its own schedule
5. Check Django admin at `/admin/tracker/dayschedule/` to see saved schedules

## Event Data Structure

Each event in the `events_data` JSONField contains:
```json
{
  "id": 1,                          // Unique event ID
  "title": "Task Name",             // Event title
  "startMin": 540,                  // Start time in minutes from midnight
  "endMin": 600,                    // End time in minutes from midnight
  "logged": false,                  // Whether activity has been logged
  "planNames": ["Plan A", "Plan B"] // Associated plan names
}
```

## Notes

- CSRF token handling already in place via `getCookie()` function
- Error handling added for network failures
- Fallback to empty schedule if date not found
- Uses update_or_create() to avoid duplicate entries
- Async/await pattern for clean asynchronous code

## Future Enhancements

Potential improvements:
1. Schedule templates
2. Copy schedule from previous day
3. Recurring events
4. Schedule sharing with friends
5. Export to calendar formats (ICS)
6. Schedule analytics and insights
