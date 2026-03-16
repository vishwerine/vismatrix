# AWS Linux Production Cron Job Setup

Complete guide for setting up iCloud Calendar auto-sync on AWS EC2 Linux server.

## Prerequisites

- SSH access to your AWS EC2 instance
- Django project deployed on the server
- Python virtual environment set up
- Root or sudo access

---

## Step-by-Step Setup

### 1. SSH into Your AWS Server

```bash
ssh -i "your-key.pem" ec2-user@your-server-ip
# or
ssh -i "your-key.pem" ubuntu@your-server-ip
```

### 2. Locate Your Project and Python

```bash
# Find your project directory
cd /home/ec2-user/vismatrix/progress_tracker
# or
cd /var/www/vismatrix/progress_tracker

# Find your Python path
which python
# or if using virtual environment
which /home/ec2-user/venv/bin/python
```

### 3. Test the Management Command

```bash
# Activate virtual environment (if using one)
source /home/ec2-user/venv/bin/activate

# Test the sync command
python manage.py sync_icloud_calendars

# Should see output like:
# Found X integration(s) to sync
# Syncing calendar for user: username
# ✓ Synced 5 events from 2 calendar(s)
```

### 4. Create Log Directory

```bash
# Create log directory
sudo mkdir -p /var/log/vismatrix
sudo chown ec2-user:ec2-user /var/log/vismatrix
# or for ubuntu
sudo chown ubuntu:ubuntu /var/log/vismatrix
```

### 5. Set Up Cron Job

```bash
# Open crontab editor
crontab -e

# If prompted, choose your preferred editor (nano is easiest)
# Press 'i' to enter insert mode if using vim
```

Add this line (modify paths as needed):

```bash
# iCloud Calendar Sync - runs every hour
0 * * * * cd /home/ec2-user/vismatrix/progress_tracker && /home/ec2-user/venv/bin/python manage.py sync_icloud_calendars >> /var/log/vismatrix/calendar_sync.log 2>&1
```

**For Ubuntu:**
```bash
0 * * * * cd /var/www/vismatrix/progress_tracker && /home/ubuntu/venv/bin/python manage.py sync_icloud_calendars >> /var/log/vismatrix/calendar_sync.log 2>&1
```

Save and exit:
- **nano**: Press `Ctrl+X`, then `Y`, then `Enter`
- **vim**: Press `Esc`, type `:wq`, press `Enter`

### 6. Verify Cron Job is Scheduled

```bash
# List all cron jobs
crontab -l

# Should show your scheduled job
```

### 7. Monitor the Logs

```bash
# Watch the log file in real-time
tail -f /var/log/vismatrix/calendar_sync.log

# View recent sync activity
tail -50 /var/log/vismatrix/calendar_sync.log

# Search for errors
grep -i error /var/log/vismatrix/calendar_sync.log
```

---

## Common Cron Schedules

```bash
# Every 30 minutes
*/30 * * * * cd /home/ec2-user/vismatrix/progress_tracker && /home/ec2-user/venv/bin/python manage.py sync_icloud_calendars >> /var/log/vismatrix/calendar_sync.log 2>&1

# Every hour
0 * * * * cd /home/ec2-user/vismatrix/progress_tracker && /home/ec2-user/venv/bin/python manage.py sync_icloud_calendars >> /var/log/vismatrix/calendar_sync.log 2>&1

# Every 3 hours
0 */3 * * * cd /home/ec2-user/vismatrix/progress_tracker && /home/ec2-user/venv/bin/python manage.py sync_icloud_calendars >> /var/log/vismatrix/calendar_sync.log 2>&1

# Daily at 3 AM
0 3 * * * cd /home/ec2-user/vismatrix/progress_tracker && /home/ec2-user/venv/bin/python manage.py sync_icloud_calendars >> /var/log/vismatrix/calendar_sync.log 2>&1

# Every 15 minutes during work hours (9 AM - 6 PM)
*/15 9-18 * * * cd /home/ec2-user/vismatrix/progress_tracker && /home/ec2-user/venv/bin/python manage.py sync_icloud_calendars >> /var/log/vismatrix/calendar_sync.log 2>&1
```

---

## Production Best Practices

### 1. Use Full Paths

Always use absolute paths in cron jobs:

```bash
# ✓ Good - uses full paths
0 * * * * cd /home/ec2-user/vismatrix/progress_tracker && /home/ec2-user/venv/bin/python manage.py sync_icloud_calendars >> /var/log/vismatrix/calendar_sync.log 2>&1

# ✗ Bad - relies on PATH
0 * * * * cd ~/project && python manage.py sync_icloud_calendars
```

### 2. Set Environment Variables

Create a wrapper script if you need environment variables:

```bash
# Create wrapper script
nano /home/ec2-user/sync_calendar.sh
```

Add:
```bash
#!/bin/bash

# Load environment variables
export DJANGO_SETTINGS_MODULE=progress_tracker.settings
export PATH=/home/ec2-user/venv/bin:$PATH

# Change to project directory
cd /home/ec2-user/vismatrix/progress_tracker

# Run sync command
python manage.py sync_icloud_calendars
```

Make executable:
```bash
chmod +x /home/ec2-user/sync_calendar.sh
```

Update cron:
```bash
0 * * * * /home/ec2-user/sync_calendar.sh >> /var/log/vismatrix/calendar_sync.log 2>&1
```

### 3. Log Rotation

Prevent logs from growing too large:

```bash
# Create logrotate config
sudo nano /etc/logrotate.d/vismatrix
```

Add:
```
/var/log/vismatrix/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ec2-user ec2-user
}
```

Test logrotate:
```bash
sudo logrotate -f /etc/logrotate.d/vismatrix
```

### 4. Email Notifications on Errors

Add email notification to cron:

```bash
# Add at top of crontab
MAILTO=your-email@example.com

# Your cron job
0 * * * * cd /home/ec2-user/vismatrix/progress_tracker && /home/ec2-user/venv/bin/python manage.py sync_icloud_calendars >> /var/log/vismatrix/calendar_sync.log 2>&1
```

### 5. Health Check Script

Create a monitoring script to verify sync is working:

```bash
nano /home/ec2-user/check_calendar_sync.sh
```

Add:
```bash
#!/bin/bash

LOG_FILE="/var/log/vismatrix/calendar_sync.log"
HOURS_THRESHOLD=2

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "ERROR: Log file not found!"
    exit 1
fi

# Check last modification time
LAST_MOD=$(stat -c %Y "$LOG_FILE")
CURRENT_TIME=$(date +%s)
DIFF_HOURS=$(( ($CURRENT_TIME - $LAST_MOD) / 3600 ))

if [ $DIFF_HOURS -gt $HOURS_THRESHOLD ]; then
    echo "WARNING: Calendar sync hasn't run in $DIFF_HOURS hours!"
    exit 1
else
    echo "OK: Calendar sync is running normally"
    exit 0
fi
```

Make executable:
```bash
chmod +x /home/ec2-user/check_calendar_sync.sh
```

---

## Troubleshooting

### Cron Job Not Running

**1. Check cron service is running:**
```bash
sudo systemctl status cron
# or on Amazon Linux 2
sudo systemctl status crond
```

**2. Start/restart cron:**
```bash
sudo systemctl start crond
sudo systemctl enable crond
```

**3. Check system logs:**
```bash
# View cron logs
sudo grep CRON /var/log/syslog
# or on Amazon Linux
sudo tail -f /var/log/cron
```

### Permission Errors

```bash
# Ensure log directory is writable
sudo chown -R ec2-user:ec2-user /var/log/vismatrix
ls -la /var/log/vismatrix

# Ensure project directory is accessible
ls -la /home/ec2-user/vismatrix/progress_tracker
```

### Python/Django Errors

**Test command manually:**
```bash
# Activate environment
source /home/ec2-user/venv/bin/activate

# Change to project directory
cd /home/ec2-user/vismatrix/progress_tracker

# Run command
python manage.py sync_icloud_calendars

# Check for any errors
```

**Check Python path:**
```bash
# From cron's perspective
/home/ec2-user/venv/bin/python --version

# Verify Django can be imported
/home/ec2-user/venv/bin/python -c "import django; print(django.VERSION)"
```

### Database Connection Issues

If using PostgreSQL/MySQL, ensure connection settings work from cron:

```bash
# Test database connection
cd /home/ec2-user/vismatrix/progress_tracker
/home/ec2-user/venv/bin/python manage.py dbshell
```

### Time Zone Issues

```bash
# Check server timezone
timedatectl

# Set timezone if needed
sudo timedatectl set-timezone America/New_York

# Note: Cron uses server local time unless specified
```

---

## Advanced: Using systemd Timer (Modern Alternative to Cron)

For modern AWS Linux 2023 or Ubuntu 20.04+, use systemd timers:

### 1. Create Service File

```bash
sudo nano /etc/systemd/system/calendar-sync.service
```

Add:
```ini
[Unit]
Description=iCloud Calendar Sync
After=network.target

[Service]
Type=oneshot
User=ec2-user
WorkingDirectory=/home/ec2-user/vismatrix/progress_tracker
ExecStart=/home/ec2-user/venv/bin/python manage.py sync_icloud_calendars
StandardOutput=append:/var/log/vismatrix/calendar_sync.log
StandardError=append:/var/log/vismatrix/calendar_sync.log
```

### 2. Create Timer File

```bash
sudo nano /etc/systemd/system/calendar-sync.timer
```

Add:
```ini
[Unit]
Description=Run iCloud Calendar Sync hourly
Requires=calendar-sync.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

### 3. Enable and Start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable timer
sudo systemctl enable calendar-sync.timer

# Start timer
sudo systemctl start calendar-sync.timer

# Check status
sudo systemctl status calendar-sync.timer

# List all timers
sudo systemctl list-timers
```

### 4. Test Service

```bash
# Run service manually
sudo systemctl start calendar-sync.service

# Check logs
sudo journalctl -u calendar-sync.service -f
```

---

## Monitoring Dashboard (Optional)

Create a simple status page:

```bash
# Add to views.py
from django.contrib.admin.views.decorators import staff_member_required
from tracker.models import ICloudCalendarIntegration

@staff_member_required
def sync_status(request):
    integrations = ICloudCalendarIntegration.objects.filter(is_active=True)
    context = {
        'integrations': integrations,
        'log_file': '/var/log/vismatrix/calendar_sync.log',
    }
    return render(request, 'admin/sync_status.html', context)
```

Access at: `https://your-domain.com/admin/sync-status/`

---

## Quick Reference Card

```bash
# View cron jobs
crontab -l

# Edit cron jobs
crontab -e

# Remove all cron jobs (careful!)
crontab -r

# Check if cron is running
sudo systemctl status crond

# View recent logs
tail -50 /var/log/vismatrix/calendar_sync.log

# Watch logs live
tail -f /var/log/vismatrix/calendar_sync.log

# Test sync command
cd /home/ec2-user/vismatrix/progress_tracker && \
  /home/ec2-user/venv/bin/python manage.py sync_icloud_calendars

# Check cron execution history
sudo grep CRON /var/log/cron | tail -20
```

---

## Security Notes

1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive data
3. **Restrict log file permissions**:
   ```bash
   chmod 640 /var/log/vismatrix/calendar_sync.log
   ```
4. **Use IAM roles** for AWS service access instead of hardcoded credentials
5. **Enable CloudWatch monitoring** for production alerts

---

## Need Help?

If you encounter issues:
1. Check logs: `tail -50 /var/log/vismatrix/calendar_sync.log`
2. Test manually: `python manage.py sync_icloud_calendars`
3. Verify paths: `which python`, `pwd`
4. Check cron status: `sudo systemctl status crond`
5. Review cron logs: `sudo tail -f /var/log/cron`
