"""
iCloud Calendar Service - CalDAV integration for syncing calendar events
"""
import caldav
from caldav.elements import dav
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
import logging

from .models import ICloudCalendarIntegration, DailyLog, Category

logger = logging.getLogger(__name__)


class ICloudCalendarService:
    """Service for syncing iCloud Calendar events via CalDAV"""
    
    def __init__(self, user):
        self.user = user
        try:
            self.integration = ICloudCalendarIntegration.objects.get(user=user)
        except ICloudCalendarIntegration.DoesNotExist:
            raise ValueError("iCloud Calendar integration not found for this user")
        
        if not self.integration.is_active:
            raise ValueError("iCloud Calendar integration is disabled")
        
        self.client = None
        self.principal = None
    
    def connect(self):
        """Establish connection to iCloud CalDAV server"""
        try:
            # Create CalDAV client
            self.client = caldav.DAVClient(
                url=self.integration.caldav_url,
                username=self.integration.apple_id,
                password=self.integration.app_specific_password
            )
            
            # Get principal (user's calendar home)
            self.principal = self.client.principal()
            
            logger.info(f"Successfully connected to iCloud CalDAV for user {self.user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to iCloud CalDAV for user {self.user.id}: {str(e)}")
            raise Exception(f"Failed to connect to iCloud Calendar: {str(e)}")
    
    def get_calendars(self):
        """Get list of available calendars"""
        if not self.principal:
            self.connect()
        
        try:
            calendars = self.principal.calendars()
            return [
                {
                    'name': cal.name or 'Unnamed Calendar',
                    'url': str(cal.url),
                    'id': str(cal.url),
                }
                for cal in calendars
            ]
        except Exception as e:
            logger.error(f"Failed to fetch calendars for user {self.user.id}: {str(e)}")
            return []
    
    def sync_events(self, days_back=7, days_forward=0):
        """
        Sync calendar events from iCloud to DailyLog
        
        Args:
            days_back: Number of days to sync backwards from today
            days_forward: Number of days to sync forward from today
        """
        if not self.principal:
            self.connect()
        
        try:
            # Calculate date range
            today = timezone.now().date()
            start_date = today - timedelta(days=days_back)
            end_date = today + timedelta(days=days_forward)
            
            # Get calendars to sync
            calendars = self.principal.calendars()
            
            # Filter calendars if specific ones are configured
            if self.integration.sync_calendars:
                calendar_names = [name.strip() for name in self.integration.sync_calendars.split(',')]
                calendars = [cal for cal in calendars if cal.name in calendar_names]
            
            synced_count = 0
            skipped_count = 0
            
            # Get default category for calendar events
            default_category = self.integration.default_category
            
            with transaction.atomic():
                for calendar in calendars:
                    try:
                        # Search for events in date range
                        events = calendar.date_search(
                            start=datetime.combine(start_date, datetime.min.time()),
                            end=datetime.combine(end_date, datetime.max.time()),
                            expand=True
                        )
                        
                        for event in events:
                            try:
                                # Parse event data
                                vevent = event.vobject_instance.vevent
                                
                                # Get event details
                                summary = str(vevent.summary.value) if hasattr(vevent, 'summary') else 'Untitled Event'
                                dtstart = vevent.dtstart.value if hasattr(vevent, 'dtstart') else None
                                dtend = vevent.dtend.value if hasattr(vevent, 'dtend') else None
                                
                                if not dtstart or not dtend:
                                    skipped_count += 1
                                    continue
                                
                                # Handle all-day events
                                if hasattr(dtstart, 'date'):
                                    # All-day event
                                    if self.integration.exclude_all_day_events:
                                        skipped_count += 1
                                        continue
                                    
                                    event_date = dtstart
                                    duration_minutes = 60  # Default 1 hour for all-day events
                                else:
                                    # Regular event with time
                                    event_date = dtstart.date()
                                    
                                    # Calculate duration in minutes
                                    if isinstance(dtstart, datetime) and isinstance(dtend, datetime):
                                        duration = dtend - dtstart
                                        duration_minutes = int(duration.total_seconds() / 60)
                                    else:
                                        duration_minutes = 60  # Default 1 hour
                                
                                # Skip events shorter than minimum duration
                                if duration_minutes < self.integration.min_event_duration:
                                    skipped_count += 1
                                    continue
                                
                                # Create or update DailyLog
                                log, created = DailyLog.objects.update_or_create(
                                    user=self.user,
                                    date=event_date,
                                    activity=summary[:200],  # Limit to 200 chars
                                    defaults={
                                        'duration': duration_minutes,
                                        'category': default_category,
                                        'description': f'Synced from iCloud Calendar: {calendar.name}',
                                    }
                                )
                                
                                if created:
                                    synced_count += 1
                                    logger.debug(f"Created DailyLog for event: {summary}")
                                
                            except Exception as e:
                                logger.warning(f"Failed to process event: {str(e)}")
                                skipped_count += 1
                                continue
                    
                    except Exception as e:
                        logger.error(f"Failed to sync calendar {calendar.name}: {str(e)}")
                        continue
            
            # Mark sync as successful
            self.integration.mark_sync_success()
            
            logger.info(f"iCloud sync completed for user {self.user.id}: {synced_count} synced, {skipped_count} skipped")
            
            return {
                'success': True,
                'synced_count': synced_count,
                'skipped_count': skipped_count,
                'calendars_synced': len(calendars),
            }
            
        except Exception as e:
            error_msg = f"Sync failed: {str(e)}"
            logger.error(f"iCloud sync error for user {self.user.id}: {error_msg}")
            self.integration.mark_sync_error(error_msg)
            raise Exception(error_msg)
    
    def test_connection(self):
        """Test if credentials are valid"""
        try:
            self.connect()
            calendars = self.get_calendars()
            return {
                'success': True,
                'calendar_count': len(calendars),
                'calendars': calendars,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
