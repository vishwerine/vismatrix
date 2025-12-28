"""
Management command to sync iCloud calendars for all users with auto-sync enabled
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from tracker.models import ICloudCalendarIntegration
from tracker.icloud_calendar_service import ICloudCalendarService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync iCloud calendars for all users with auto-sync enabled'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync all active integrations regardless of sync interval',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Sync only for a specific user ID',
        )

    def handle(self, *args, **options):
        force = options['force']
        user_id = options.get('user_id')
        
        # Get integrations to sync
        integrations = ICloudCalendarIntegration.objects.filter(is_active=True)
        
        if user_id:
            integrations = integrations.filter(user_id=user_id)
        
        if not force:
            # Filter by those that should sync based on interval
            integrations = [i for i in integrations if i.should_sync()]
        else:
            integrations = list(integrations)
        
        if not integrations:
            self.stdout.write(self.style.WARNING('No integrations need syncing at this time'))
            return
        
        self.stdout.write(f'Found {len(integrations)} integration(s) to sync')
        
        success_count = 0
        error_count = 0
        
        for integration in integrations:
            try:
                self.stdout.write(f'Syncing calendar for user: {integration.user.username}')
                
                service = ICloudCalendarService(integration.user)
                result = service.sync_events(
                    days_back=integration.sync_days_back,
                    days_forward=integration.sync_days_forward
                )
                
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Synced {result["synced_count"]} events '
                        f'from {result["calendars_synced"]} calendar(s)'
                    )
                )
                
            except Exception as e:
                error_count += 1
                error_msg = str(e)
                logger.error(f'Failed to sync calendar for user {integration.user.id}: {error_msg}')
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Sync failed: {error_msg}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'✓ Successful syncs: {success_count}'))
        if error_count:
            self.stdout.write(self.style.ERROR(f'✗ Failed syncs: {error_count}'))
        self.stdout.write('='*50)
