"""
Django management command to sync Google Calendar events for all active users
Usage: python manage.py sync_calendars
"""
from django.core.management.base import BaseCommand
from tracker.calendar_service import sync_all_active_integrations
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Google Calendar events to DailyLog for all active integrations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Sync only for a specific username',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if sync interval has not passed',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        verbose = options.get('verbose')
        force = options.get('force')
        
        if username:
            # Sync specific user
            from django.contrib.auth import get_user_model
            from tracker.calendar_service import GoogleCalendarService
            from tracker.models import GoogleCalendarIntegration
            
            User = get_user_model()
            try:
                user = User.objects.get(username=username)
                integration = GoogleCalendarIntegration.objects.get(user=user)
                
                if not integration.is_active:
                    self.stdout.write(self.style.WARNING(f'Integration for {username} is not active'))
                    return
                
                self.stdout.write(f'Syncing calendar for {username}...')
                service = GoogleCalendarService(user)
                stats = service.sync_events_to_logs()
                
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Synced {username}: {stats.get("logs_created", 0)} events created, '
                    f'{stats.get("logs_updated", 0)} updated'
                ))
                
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{username}" not found'))
            except GoogleCalendarIntegration.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'No Google Calendar integration for {username}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error syncing {username}: {str(e)}'))
                logger.exception(f'Error syncing calendar for {username}')
        else:
            # Sync all active integrations
            self.stdout.write('Syncing all active Google Calendar integrations...')
            
            try:
                from tracker.models import GoogleCalendarIntegration
                from tracker.calendar_service import GoogleCalendarService
                
                if force:
                    # Force sync - ignore sync interval
                    integrations = GoogleCalendarIntegration.objects.filter(
                        is_active=True,
                        auto_sync=True
                    )
                    
                    if not integrations.exists():
                        self.stdout.write(self.style.WARNING('No active integrations found'))
                        return
                    
                    results = {}
                    for integration in integrations:
                        service = GoogleCalendarService(integration.user)
                        stats = service.sync_events_to_logs()
                        results[integration.user.username] = stats
                else:
                    # Normal sync - respect sync interval
                    results = sync_all_active_integrations()
                
                if not results:
                    self.stdout.write(self.style.WARNING('No integrations ready to sync (check sync intervals)'))
                    return
                
                # Display results
                total_created = 0
                total_updated = 0
                
                for username, stats in results.items():
                    created = stats.get('logs_created', 0)
                    updated = stats.get('logs_updated', 0)
                    total_created += created
                    total_updated += updated
                    
                    if verbose:
                        self.stdout.write(
                            f'  {username}: {created} created, {updated} updated'
                        )
                
                self.stdout.write(self.style.SUCCESS(
                    f'\n✓ Synced {len(results)} user(s): '
                    f'{total_created} events created, {total_updated} updated'
                ))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error during sync: {str(e)}'))
                logger.exception('Error syncing calendars')
