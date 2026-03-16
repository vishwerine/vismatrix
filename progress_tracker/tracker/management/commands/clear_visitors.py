"""
Management command to clear all entries from the LandingPageVisitor table.
Usage: python manage.py clear_visitors [--confirm]
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import LandingPageVisitor


class Command(BaseCommand):
    help = 'Remove all entries from the LandingPageVisitor table'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt and delete immediately'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        confirm = options['confirm']
        dry_run = options['dry_run']
        
        # Get count of visitors
        visitor_count = LandingPageVisitor.objects.count()
        
        if visitor_count == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ LandingPageVisitor table is already empty.')
            )
            return
        
        # Show summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.WARNING('LANDING PAGE VISITOR CLEANUP'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'\nTotal visitors to be deleted: {visitor_count:,}')
        
        # Show breakdown
        converted = LandingPageVisitor.objects.filter(converted_to_user=True).count()
        not_converted = visitor_count - converted
        
        self.stdout.write(f'  - Converted to users: {converted:,}')
        self.stdout.write(f'  - Not converted: {not_converted:,}')
        
        if dry_run:
            self.stdout.write('\n' + self.style.NOTICE('DRY RUN MODE - No data will be deleted'))
            self.stdout.write(self.style.SUCCESS(f'\n✓ Would delete {visitor_count:,} visitor records'))
            return
        
        # Confirmation prompt
        if not confirm:
            self.stdout.write('\n' + self.style.WARNING('⚠️  WARNING: This action cannot be undone!'))
            response = input('\nType "DELETE" to confirm deletion: ')
            
            if response != 'DELETE':
                self.stdout.write(self.style.ERROR('\n✗ Operation cancelled'))
                return
        
        # Perform deletion
        self.stdout.write('\n' + self.style.NOTICE('Deleting visitors...'))
        
        try:
            with transaction.atomic():
                deleted_count, _ = LandingPageVisitor.objects.all().delete()
                
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Successfully deleted {deleted_count:,} visitor records')
            )
            self.stdout.write(self.style.SUCCESS('✓ LandingPageVisitor table is now empty'))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Error during deletion: {str(e)}')
            )
            raise
        
        self.stdout.write('\n' + '=' * 60 + '\n')
