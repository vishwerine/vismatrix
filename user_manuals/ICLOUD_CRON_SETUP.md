# iCloud Calendar Auto-Sync with Crontab

## Overview

Automatically sync iCloud calendars for all users every hour using crontab.

## Setup

### 1. Make Script Executable

```bash
chmod +x /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/sync_icloud_cron.sh
```

### 2. Configure Virtual Environment Path

Edit `sync_icloud_cron.sh` and update the `VENV_PATH` variable to point to your Python virtual environment:

```bash
# Around line 15
VENV_PATH="/path/to/your/venv"  # e.g., /home/ubuntu/myenv
```

### 3. Test the Script

Run it manually first to verify it works:

```bash
cd /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker
./sync_icloud_cron.sh
```

Check the log output:
```bash
cat logs/icloud_sync_$(date +%Y%m%d).log
```

### 4. Add to Crontab

Open crontab editor:
```bash
crontab -e
```

Add one of these lines:

**Option A: Every hour at minute 0**
```cron
0 * * * * /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/sync_icloud_cron.sh
```

**Option B: Every hour at minute 0 with output to syslog**
```cron
0 * * * * /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/sync_icloud_cron.sh 2>&1 | logger -t icloud-sync
```

**Option C: Every 2 hours**
```cron
0 */2 * * * /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/sync_icloud_cron.sh
```

**Option D: Custom times (e.g., 8 AM, 12 PM, 6 PM)**
```cron
0 8,12,18 * * * /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/sync_icloud_cron.sh
```

Save and exit (`:wq` in vim, or `Ctrl+O` then `Ctrl+X` in nano).

### 5. Verify Crontab Entry

```bash
crontab -l
```

You should see your entry listed.

## Production Setup (AWS/Linux)

### Option 1: User Crontab (Recommended)

Run as the application user (e.g., `ubuntu`):

```bash
# Switch to app user
sudo su - ubuntu

# Edit crontab
crontab -e

# Add:
0 * * * * /home/ubuntu/vismatrix/progress_tracker/sync_icloud_cron.sh
```

### Option 2: System Crontab

Add to `/etc/crontab` (requires sudo):

```bash
sudo nano /etc/crontab

# Add this line (replace 'ubuntu' with your user):
0 * * * * ubuntu /home/ubuntu/vismatrix/progress_tracker/sync_icloud_cron.sh
```

### Option 3: Cron.d File (Cleanest for deployment)

```bash
# Create cron file
sudo nano /etc/cron.d/icloud-sync

# Add (on ONE line):
0 * * * * ubuntu /home/ubuntu/vismatrix/progress_tracker/sync_icloud_cron.sh

# Set permissions
sudo chmod 644 /etc/cron.d/icloud-sync
```

## Monitoring

### View Logs

**Today's log:**
```bash
tail -f /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/logs/icloud_sync_$(date +%Y%m%d).log
```

**All recent logs:**
```bash
ls -lh /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/logs/
```

**Last 50 lines:**
```bash
tail -50 /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker/logs/icloud_sync_*.log | tail -50
```

### Check Cron Execution

**System log (macOS):**
```bash
log show --predicate 'process == "cron"' --last 1h
```

**System log (Linux):**
```bash
grep CRON /var/log/syslog | tail -20
```

### Email Notifications (Linux)

Install mail utilities:
```bash
sudo apt-get install mailutils
```

Modify crontab to send email on errors:
```cron
MAILTO=your-email@example.com
0 * * * * /home/ubuntu/vismatrix/progress_tracker/sync_icloud_cron.sh || echo "iCloud sync failed"
```

## Troubleshooting

### Cron Not Running

**Check cron service:**
```bash
# macOS
sudo launchctl list | grep cron

# Linux
sudo systemctl status cron
```

**Start cron service:**
```bash
# Linux
sudo systemctl start cron
sudo systemctl enable cron
```

### Permission Denied

```bash
chmod +x /path/to/sync_icloud_cron.sh
```

### Virtual Environment Not Found

Edit `sync_icloud_cron.sh` and verify `VENV_PATH` is correct:
```bash
ls -la /path/to/your/venv/bin/activate
```

### Django Settings Error

Make sure `DJANGO_SETTINGS_MODULE` is set correctly in your environment. The script should work automatically, but if needed, add to the script:

```bash
export DJANGO_SETTINGS_MODULE=progress_tracker.settings
```

### Calendar Sync Failing

Check the logs for specific errors:
```bash
grep "ERROR" /path/to/logs/icloud_sync_*.log
```

Common issues:
- **Auth errors**: App-specific password expired
- **Network errors**: CalDAV server unreachable
- **Database locked**: Another process using DB

## Advanced Configuration

### Sync Specific User Only

Modify the command in `sync_icloud_cron.sh`:
```bash
python manage.py sync_icloud_calendars --user-id 1
```

### Force Sync (Ignore Intervals)

```bash
python manage.py sync_icloud_calendars --force
```

### Custom Schedule Examples

```cron
# Every 30 minutes
*/30 * * * * /path/to/sync_icloud_cron.sh

# Every day at 2 AM
0 2 * * * /path/to/sync_icloud_cron.sh

# Every Monday at 9 AM
0 9 * * 1 /path/to/sync_icloud_cron.sh

# Every 4 hours during business hours (9 AM - 5 PM)
0 9-17/4 * * * /path/to/sync_icloud_cron.sh
```

## Log Rotation

The script automatically deletes logs older than 30 days. To adjust:

Edit `sync_icloud_cron.sh` (last few lines):
```bash
# Keep only last 7 days
find "$LOG_DIR" -name "icloud_sync_*.log" -mtime +7 -delete

# Keep only last 90 days
find "$LOG_DIR" -name "icloud_sync_*.log" -mtime +90 -delete
```

## Testing Cron Schedule

Use [crontab.guru](https://crontab.guru/) to visualize your cron expression.

Or test locally:
```bash
# Run every minute for testing (REMOVE after testing!)
* * * * * /path/to/sync_icloud_cron.sh

# Wait 2 minutes, then check logs
sleep 120 && cat logs/icloud_sync_*.log
```

**Remember to change back to hourly after testing!**

## Complete Example for Production

```bash
# 1. Setup
cd /home/ubuntu/vismatrix/progress_tracker
chmod +x sync_icloud_cron.sh

# 2. Edit script (update VENV_PATH)
nano sync_icloud_cron.sh

# 3. Test manually
./sync_icloud_cron.sh

# 4. Check logs
cat logs/icloud_sync_$(date +%Y%m%d).log

# 5. Add to crontab
crontab -e
# Add: 0 * * * * /home/ubuntu/vismatrix/progress_tracker/sync_icloud_cron.sh

# 6. Verify
crontab -l

# 7. Wait 1 hour and check
tail -f /home/ubuntu/vismatrix/progress_tracker/logs/icloud_sync_*.log
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `crontab -e` | Edit crontab |
| `crontab -l` | List crontab entries |
| `crontab -r` | Remove all crontab entries |
| `./sync_icloud_cron.sh` | Test script manually |
| `tail -f logs/icloud_sync_*.log` | Watch logs live |
| `grep ERROR logs/icloud_sync_*.log` | Find errors |
