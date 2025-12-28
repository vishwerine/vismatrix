# iCloud Calendar Auto-Sync Setup Guide

This guide explains how to set up automatic periodic syncing of iCloud calendars in production.

## Method 1: System Cron (Recommended for Simple Deployments)

### Setup Instructions

1. **Test the management command manually:**
```bash
python manage.py sync_icloud_calendars
```

2. **Open crontab editor:**
```bash
crontab -e
```

3. **Add cron job** (runs every hour):
```bash
# Sync iCloud calendars every hour
0 * * * * cd /path/to/your/project && /path/to/python manage.py sync_icloud_calendars >> /var/log/calendar_sync.log 2>&1
```

### Example Cron Schedules

```bash
# Every 30 minutes
*/30 * * * * cd /path/to/project && python manage.py sync_icloud_calendars

# Every hour at minute 0
0 * * * * cd /path/to/project && python manage.py sync_icloud_calendars

# Every 6 hours
0 */6 * * * cd /path/to/project && python manage.py sync_icloud_calendars

# Daily at 2 AM
0 2 * * * cd /path/to/project && python manage.py sync_icloud_calendars

# Every 15 minutes during business hours (9 AM - 6 PM, Mon-Fri)
*/15 9-18 * * 1-5 cd /path/to/project && python manage.py sync_icloud_calendars
```

### Full Production Cron Example

```bash
# iCloud Calendar Sync - runs every hour
0 * * * * cd /home/myuser/vismatrix/progress_tracker && \
  /home/myuser/venv/bin/python manage.py sync_icloud_calendars \
  >> /var/log/vismatrix/calendar_sync.log 2>&1

# Or with environment activation
0 * * * * source /home/myuser/venv/bin/activate && \
  cd /home/myuser/vismatrix/progress_tracker && \
  python manage.py sync_icloud_calendars \
  >> /var/log/vismatrix/calendar_sync.log 2>&1
```

### Command Options

```bash
# Force sync all active integrations (ignore sync interval)
python manage.py sync_icloud_calendars --force

# Sync only for a specific user
python manage.py sync_icloud_calendars --user-id 5

# Combine options
python manage.py sync_icloud_calendars --force --user-id 5
```

---

## Method 2: Celery Beat (Recommended for Production at Scale)

For larger production deployments, use Celery with Celery Beat for better control and monitoring.

### 1. Install Dependencies

```bash
pip install celery redis django-celery-beat
```

### 2. Configure Celery

Create `progress_tracker/celery.py`:

```python
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'progress_tracker.settings')

app = Celery('progress_tracker')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    'sync-icloud-calendars-hourly': {
        'task': 'tracker.tasks.sync_all_icloud_calendars',
        'schedule': crontab(minute=0),  # Every hour
    },
}
```

### 3. Create Tasks

Create `tracker/tasks.py`:

```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def sync_all_icloud_calendars():
    """Celery task to sync all iCloud calendars"""
    call_command('sync_icloud_calendars')
```

### 4. Update settings.py

```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
```

### 5. Run Celery Workers

```bash
# Terminal 1: Start Celery worker
celery -A progress_tracker worker --loglevel=info

# Terminal 2: Start Celery Beat scheduler
celery -A progress_tracker beat --loglevel=info
```

### 6. Production Deployment with Supervisor

Create `/etc/supervisor/conf.d/celery.conf`:

```ini
[program:celery_worker]
command=/home/myuser/venv/bin/celery -A progress_tracker worker --loglevel=info
directory=/home/myuser/vismatrix/progress_tracker
user=myuser
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker_err.log

[program:celery_beat]
command=/home/myuser/venv/bin/celery -A progress_tracker beat --loglevel=info
directory=/home/myuser/vismatrix/progress_tracker
user=myuser
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat_err.log
```

Then:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start celery_worker
sudo supervisorctl start celery_beat
```

---

## Method 3: Django Q (Alternative to Celery)

Simpler than Celery but still powerful.

### 1. Install

```bash
pip install django-q
```

### 2. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    # ...
    'django_q',
]

Q_CLUSTER = {
    'name': 'DjangORM',
    'workers': 4,
    'timeout': 90,
    'retry': 120,
    'queue_limit': 50,
    'bulk': 10,
    'orm': 'default',
}
```

### 3. Run migrations

```bash
python manage.py migrate
```

### 4. Create scheduled task in Django admin

Or programmatically:

```python
from django_q.models import Schedule

Schedule.objects.create(
    func='tracker.tasks.sync_all_icloud_calendars',
    schedule_type=Schedule.HOURLY,
    name='iCloud Calendar Sync',
)
```

### 5. Run cluster

```bash
python manage.py qcluster
```

---

## Monitoring & Logging

### 1. Set up logging

Add to `settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'calendar_sync': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/vismatrix/calendar_sync.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'loggers': {
        'tracker.icloud_calendar_service': {
            'handlers': ['calendar_sync'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### 2. Monitor sync status

Create a monitoring endpoint in `views.py`:

```python
@login_required
@user_passes_test(lambda u: u.is_staff)
def calendar_sync_status(request):
    """Admin view to check calendar sync status"""
    integrations = ICloudCalendarIntegration.objects.filter(is_active=True)
    
    context = {
        'integrations': integrations,
        'total_active': integrations.count(),
        'needs_sync': [i for i in integrations if i.should_sync()],
    }
    return render(request, 'admin/calendar_sync_status.html', context)
```

---

## Troubleshooting

### Check if cron is running:
```bash
# View cron logs
grep CRON /var/log/syslog

# Test command manually
cd /path/to/project && python manage.py sync_icloud_calendars
```

### Verify Python environment:
```bash
# Make sure cron uses the correct Python
which python
# Use full path in cron: /usr/bin/python3 or /home/user/venv/bin/python
```

### Check permissions:
```bash
# Ensure cron user can write to log files
sudo chmod 664 /var/log/vismatrix/calendar_sync.log
sudo chown myuser:myuser /var/log/vismatrix/calendar_sync.log
```

---

## Recommendations

- **Small deployments**: Use **system cron** (Method 1)
- **Medium to large deployments**: Use **Celery Beat** (Method 2)  
- **Simple async needs**: Use **Django Q** (Method 3)

For most Django apps in production, **Celery Beat** is the industry standard and provides the best monitoring, error handling, and scalability.
