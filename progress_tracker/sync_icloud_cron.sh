#!/bin/bash
#
# Cron script to sync iCloud calendars for all users
# Add to crontab: 0 * * * * /path/to/sync_icloud_cron.sh
#

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/icloud_sync_$(date +\%Y\%m\%d).log"

# Virtual environment (adjust path if needed)
VENV_PATH="$PROJECT_DIR/../../../myenv"  # Adjust to your venv path

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Timestamp for logging
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Function to log messages
log() {
    echo "[$TIMESTAMP] $1" >> "$LOG_FILE"
}

log "=========================================="
log "Starting iCloud calendar sync"
log "=========================================="

# Activate virtual environment if it exists
if [ -d "$VENV_PATH" ]; then
    log "Activating virtual environment: $VENV_PATH"
    source "$VENV_PATH/bin/activate"
else
    log "WARNING: Virtual environment not found at $VENV_PATH"
fi

# Change to project directory
cd "$PROJECT_DIR" || {
    log "ERROR: Failed to change to project directory: $PROJECT_DIR"
    exit 1
}

# Run the sync command
log "Running: python manage.py sync_icloud_calendars"
python manage.py sync_icloud_calendars >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log "✓ Sync completed successfully"
else
    log "✗ Sync failed with exit code: $EXIT_CODE"
fi

log "=========================================="
log "Finished iCloud calendar sync"
log "=========================================="
echo "" >> "$LOG_FILE"

# Keep only last 30 days of logs
find "$LOG_DIR" -name "icloud_sync_*.log" -mtime +30 -delete

exit $EXIT_CODE
