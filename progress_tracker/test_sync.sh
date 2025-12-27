#!/bin/bash
# Test script for calendar sync

cd /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker

echo "========================================="
echo "Testing Calendar Sync Command"
echo "========================================="
echo ""

/opt/anaconda3/bin/python manage.py sync_calendars --verbose

echo ""
echo "========================================="
echo "Sync test complete!"
echo "========================================="
