"""
Google Calendar integration service for syncing calendar events to DailyLog
"""
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .models import GoogleCalendarIntegration, DailyLog, Category
import logging

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Service for interacting with Google Calendar API"""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    
    def __init__(self, user: User):
        self.user = user
        try:
            self.integration = GoogleCalendarIntegration.objects.get(user=user)
        except GoogleCalendarIntegration.DoesNotExist:
            self.integration = None
    
    def get_credentials(self) -> Credentials:
        """Get OAuth2 credentials for the user"""
        if not self.integration:
            raise ValueError("User has no Google Calendar integration")
        
        creds_dict = self.integration.get_credentials_dict()
        credentials = Credentials(
            token=creds_dict['token'],
            refresh_token=creds_dict['refresh_token'],
            token_uri=creds_dict['token_uri'],
            client_id=creds_dict['client_id'],
            client_secret=creds_dict['client_secret'],
            scopes=creds_dict['scopes']
        )
        
        return credentials
    
    def get_service(self):
        """Build and return Calendar API service"""
        credentials = self.get_credentials()
        return build('calendar', 'v3', credentials=credentials)
    
    def list_calendars(self):
        """List all calendars available to the user"""
        try:
            service = self.get_service()
            calendar_list = service.calendarList().list().execute()
            return calendar_list.get('items', [])
        except HttpError as error:
            logger.error(f"Error listing calendars for {self.user.username}: {error}")
            return []
    
    def fetch_events(self, calendar_id='primary', time_min=None, time_max=None, max_results=100):
        """
        Fetch events from a specific calendar
        
        Args:
            calendar_id: Calendar ID (default: 'primary')
            time_min: Start time (default: 7 days ago)
            time_max: End time (default: now)
            max_results: Maximum number of events to return
        """
        try:
            service = self.get_service()
            
            # Default time range: last 7 days
            if not time_min:
                time_min = (timezone.now() - timedelta(days=7)).isoformat()
            if not time_max:
                time_max = timezone.now().isoformat()
            
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
        
        except HttpError as error:
            logger.error(f"Error fetching events for {self.user.username}: {error}")
            self.integration.mark_sync_error(str(error))
            return []
    
    def sync_events_to_logs(self, days_back=7):
        """
        Sync calendar events to DailyLog entries
        
        Args:
            days_back: Number of days to look back (default: 7)
        
        Returns:
            dict with sync statistics
        """
        if not self.integration or not self.integration.is_active:
            return {'error': 'Integration not active'}
        
        stats = {
            'events_processed': 0,
            'logs_created': 0,
            'logs_skipped': 0,
            'errors': []
        }
        
        try:
            # Determine time range
            time_min = (timezone.now() - timedelta(days=days_back)).isoformat()
            time_max = timezone.now().isoformat()
            
            # Get calendars to sync
            calendars_to_sync = self._get_calendars_to_sync()
            
            for calendar_id in calendars_to_sync:
                events = self.fetch_events(
                    calendar_id=calendar_id,
                    time_min=time_min,
                    time_max=time_max
                )
                
                for event in events:
                    stats['events_processed'] += 1
                    
                    try:
                        result = self._create_log_from_event(event)
                        if result == 'created':
                            stats['logs_created'] += 1
                        else:
                            stats['logs_skipped'] += 1
                    except Exception as e:
                        logger.error(f"Error creating log from event: {e}")
                        stats['errors'].append(str(e))
            
            # Mark successful sync
            self.integration.mark_sync_success()
            
        except Exception as e:
            logger.error(f"Error syncing calendar for {self.user.username}: {e}")
            self.integration.mark_sync_error(str(e))
            stats['errors'].append(str(e))
        
        return stats
    
    def _get_calendars_to_sync(self):
        """Get list of calendar IDs to sync"""
        if self.integration.sync_calendars:
            # Use specified calendars
            return [cal.strip() for cal in self.integration.sync_calendars.split(',')]
        else:
            # Sync primary calendar only
            return ['primary']
    
    def _create_log_from_event(self, event):
        """
        Create a DailyLog entry from a calendar event
        
        Returns:
            'created' if new log was created, 'skipped' if skipped
        """
        # Extract event details
        summary = event.get('summary', 'Untitled Event')
        description = event.get('description', '')
        event_id = event.get('id')
        
        # Parse start and end times
        start = event.get('start', {})
        end = event.get('end', {})
        
        # Handle all-day events
        if 'date' in start:
            if self.integration.exclude_all_day_events:
                return 'skipped'
            event_date = datetime.fromisoformat(start['date']).date()
            duration = 0  # All-day events have no duration
        else:
            # Timed events
            start_datetime = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            end_datetime = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            event_date = start_datetime.date()
            duration = int((end_datetime - start_datetime).total_seconds() / 60)  # minutes
        
        # Skip events shorter than minimum duration
        if duration > 0 and duration < self.integration.min_event_duration:
            return 'skipped'
        
        # Check if log already exists for this event
        # We use event_id in description to track which events we've synced
        existing_log = DailyLog.objects.filter(
            user=self.user,
            date=event_date,
            activity__icontains=f"[gcal:{event_id}]"
        ).first()
        
        if existing_log:
            return 'skipped'
        
        # Get default category
        category = self.integration.default_category
        
        # Create DailyLog entry
        activity_text = f"{summary} [gcal:{event_id}]"
        
        DailyLog.objects.create(
            user=self.user,
            date=event_date,
            activity=activity_text,
            description=description[:500] if description else '',  # Truncate if needed
            category=category,
            duration=duration
        )
        
        return 'created'
    
    @staticmethod
    def refresh_credentials(integration: GoogleCalendarIntegration):
        """
        Refresh OAuth2 credentials if they're expired
        
        Args:
            integration: GoogleCalendarIntegration instance
        
        Returns:
            Updated credentials or None if refresh failed
        """
        try:
            creds_dict = integration.get_credentials_dict()
            credentials = Credentials(
                token=creds_dict['token'],
                refresh_token=creds_dict['refresh_token'],
                token_uri=creds_dict['token_uri'],
                client_id=creds_dict['client_id'],
                client_secret=creds_dict['client_secret'],
                scopes=creds_dict['scopes']
            )
            
            # Check if credentials need refresh
            if credentials.expired and credentials.refresh_token:
                from google.auth.transport.requests import Request
                credentials.refresh(Request())
                
                # Save new access token
                integration.access_token = credentials.token
                integration.save()
                
                return credentials
            
            return credentials
        
        except Exception as e:
            logger.error(f"Error refreshing credentials: {e}")
            integration.mark_sync_error(f"Failed to refresh credentials: {str(e)}")
            return None


def sync_all_active_integrations():
    """
    Sync all active Google Calendar integrations
    This function can be called by a cron job or celery task
    """
    integrations = GoogleCalendarIntegration.objects.filter(
        is_active=True,
        auto_sync=True
    )
    
    results = {}
    
    for integration in integrations:
        if integration.should_sync():
            service = GoogleCalendarService(integration.user)
            stats = service.sync_events_to_logs()
            results[integration.user.username] = stats
    
    return results
