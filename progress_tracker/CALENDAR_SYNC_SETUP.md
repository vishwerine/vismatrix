# Google Calendar Auto-Sync Setup Guide

## Overview
This guide explains how to set up automatic background syncing of Google Calendar events to VisMatrix.

## Manual Sync

### Run sync for all active users:
```bash
python manage.py sync_calendars
```

### Run sync for a specific user:
```bash
python manage.py sync_calendars --username your_username
```

### Verbose output:
```bash
python manage.py sync_calendars --verbose
```

## Automatic Background Sync Options

### Option 1: Cron Job (Recommended for Simple Setup)

#### For macOS/Linux:

1. **Open crontab editor:**
```bash
crontab -e
```

2. **Add one of these lines** (choose based on desired frequency):

**Every hour:**
```bash
0 * * * * cd /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker && /opt/anaconda3/bin/python manage.py sync_calendars >> /tmp/calendar_sync.log 2>&1
```

**Every 30 minutes:**
```bash
*/30 * * * * cd /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker && /opt/anaconda3/bin/python manage.py sync_calendars >> /tmp/calendar_sync.log 2>&1
```

**Every 15 minutes:**
```bash
*/15 * * * * cd /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker && /opt/anaconda3/bin/python manage.py sync_calendars >> /tmp/calendar_sync.log 2>&1
```

**Every 6 hours:**
```bash
0 */6 * * * cd /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker && /opt/anaconda3/bin/python manage.py sync_calendars >> /tmp/calendar_sync.log 2>&1
```

3. **Save and exit** (in vim: press Esc, type `:wq`, press Enter)

4. **Verify cron job is installed:**
```bash
crontab -l
```

5. **Check sync logs:**
```bash
tail -f /tmp/calendar_sync.log
```

---

### Option 2: Celery Beat (Recommended for Production)

#### 1. Install Celery:
```bash
pip install celery redis django-celery-beat
```

#### 2. Add to `requirements.txt`:
```
celery==5.3.4
redis==5.0.1
django-celery-beat==2.5.0
```

#### 3. Install Redis (task queue):
**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

#### 4. Create `progress_tracker/celery.py`:
```python
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'progress_tracker.settings')

app = Celery('progress_tracker')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic task schedule
app.conf.beat_schedule = {
    'sync-calendars-every-hour': {
        'task': 'tracker.tasks.sync_all_calendars',
        'schedule': crontab(minute=0),  # Every hour
    },
}
```

#### 5. Update `progress_tracker/__init__.py`:
```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

#### 6. Create `tracker/tasks.py`:
```python
from celery import shared_task
from .calendar_service import sync_all_active_integrations
import logging

logger = logging.getLogger(__name__)

@shared_task
def sync_all_calendars():
    """Celery task to sync all Google Calendar integrations"""
    try:
        results = sync_all_active_integrations()
        logger.info(f"Calendar sync completed: {len(results)} users synced")
        return results
    except Exception as e:
        logger.error(f"Calendar sync failed: {str(e)}")
        raise
```

#### 7. Add to `settings.py`:
```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Los_Angeles'  # Your timezone
```

#### 8. Run Celery worker and beat:
```bash
# Terminal 1 - Worker
celery -A progress_tracker worker --loglevel=info

# Terminal 2 - Beat scheduler
celery -A progress_tracker beat --loglevel=info
```

#### 9. For production, use supervisord or systemd to keep workers running

---

### Option 3: systemd Timer (Linux Only)

#### 1. Create service file: `/etc/systemd/system/calendar-sync.service`
```ini
[Unit]
Description=VisMatrix Calendar Sync
After=network.target

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/path/to/progress_tracker
Environment="PATH=/path/to/python/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/path/to/python manage.py sync_calendars

[Install]
WantedBy=multi-user.target
```

#### 2. Create timer file: `/etc/systemd/system/calendar-sync.timer`
```ini
[Unit]
Description=Run Calendar Sync Every Hour
Requires=calendar-sync.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Unit=calendar-sync.service

[Install]
WantedBy=timers.target
```

#### 3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable calendar-sync.timer
sudo systemctl start calendar-sync.timer
```

#### 4. Check status:
```bash
sudo systemctl status calendar-sync.timer
sudo systemctl list-timers
```

---

## User Settings

Users can configure their sync preferences at: **http://127.0.0.1:8000/calendar/settings/**

### Available Settings:
- **Auto Sync**: Enable/disable automatic syncing
- **Sync Interval**: How often to check for new events (in hours)
- **Default Category**: Which category to assign to synced events
- **Min Event Duration**: Ignore events shorter than X minutes
- **Exclude All-Day Events**: Skip all-day events

### Manual Sync Button
Users can also trigger manual sync anytime by clicking "Sync Now" in their calendar settings.

---

## Monitoring & Troubleshooting

### Check sync status:
```bash
# View cron logs
tail -f /tmp/calendar_sync.log

# Django logs
tail -f /path/to/django/logs/django.log
```

### Test sync manually:
```bash
python manage.py sync_calendars --verbose
```

### Common Issues:

1. **"No active integrations found"**
   - Users need to enable "Auto Sync" in their calendar settings
   - Check that integrations exist: `GoogleCalendarIntegration.objects.filter(is_active=True)`

2. **OAuth token expired**
   - Tokens should auto-refresh
   - If failing, users may need to reconnect their calendar

3. **Rate limiting**
   - Google Calendar API has quotas
   - Default: 1,000,000 queries per day
   - Per-user: 10,000 queries per day

### Database Check:
```bash
python manage.py shell
```
```python
from tracker.models import GoogleCalendarIntegration
integrations = GoogleCalendarIntegration.objects.filter(is_active=True, auto_sync=True)
for i in integrations:
    print(f"{i.user.username}: last_sync={i.last_sync_at}, should_sync={i.should_sync()}")
```

---

## Recommended Setup

**For Development (Local):**
- Use cron job with 1-hour interval
- Logs to `/tmp/calendar_sync.log`

**For Production:**
- Use Celery Beat with Redis
- Configure proper logging
- Monitor with tools like Sentry or New Relic
- Set sync interval based on user needs (recommended: 30-60 minutes)

---

## Next Steps

1. Choose your preferred sync method (cron for simple, Celery for production)
2. Set up the scheduled task
3. Test with `python manage.py sync_calendars --verbose`
4. Enable auto-sync in your calendar settings
5. Monitor logs to ensure syncing works correctly
