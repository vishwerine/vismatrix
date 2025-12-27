"""
Management command to clean up old data and optimize the database.
Usage: python manage.py cleanup_old_data [--days=180] [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from tracker.models import (
    DailyLog, Task, FriendRequest, ActivityReaction, 
    Message, Conversation, ConversationMember
)


class Command(BaseCommand):
    help = 'Clean up old data and optimize the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=180,
            help='Delete data older than this many days (default: 180)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--cleanup-rejected-requests',
            action='store_true',
            help='Clean up rejected/old friend requests'
        )
        parser.add_argument(
            '--optimize-db',
            action='store_true',
            help='Run database optimization after cleanup'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cleanup_requests = options['cleanup_rejected_requests']
        optimize = options['optimize_db']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(
            self.style.WARNING(f"\n{'DRY RUN - ' if dry_run else ''}Cleaning data older than {days} days")
        )
        self.stdout.write(f"Cutoff date: {cutoff_date.date()}\n")
        
        # Track stats
        stats = {
            'rejected_requests': 0,
            'old_reactions': 0,
            'empty_conversations': 0,
        }
        
        try:
            with transaction.atomic():
                # 1. Clean up old rejected friend requests (older than 30 days)
                if cleanup_requests:
                    request_cutoff = timezone.now() - timedelta(days=30)
                    rejected_requests = FriendRequest.objects.filter(
                        status='rejected',
                        updated_at__lt=request_cutoff
                    )
                    stats['rejected_requests'] = rejected_requests.count()
                    
                    if not dry_run:
                        rejected_requests.delete()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{'Would delete' if dry_run else 'Deleted'} "
                            f"{stats['rejected_requests']} old rejected friend requests"
                        )
                    )
                
                # 2. Clean up reactions on deleted activities
                orphaned_reactions = ActivityReaction.objects.filter(
                    task__isnull=True,
                    daily_log__isnull=True
                )
                stats['old_reactions'] = orphaned_reactions.count()
                
                if stats['old_reactions'] > 0:
                    if not dry_run:
                        orphaned_reactions.delete()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{'Would delete' if dry_run else 'Deleted'} "
                            f"{stats['old_reactions']} orphaned reactions"
                        )
                    )
                
                # 3. Clean up empty conversations (no messages and old)
                empty_convs = Conversation.objects.filter(
                    created_at__lt=cutoff_date
                ).annotate(
                    msg_count=models.Count('messages')
                ).filter(msg_count=0)
                
                stats['empty_conversations'] = empty_convs.count()
                
                if stats['empty_conversations'] > 0:
                    if not dry_run:
                        empty_convs.delete()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{'Would delete' if dry_run else 'Deleted'} "
                            f"{stats['empty_conversations']} empty conversations"
                        )
                    )
                
                # Summary
                total_items = sum(stats.values())
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n{'Would clean' if dry_run else 'Cleaned'} {total_items} total items"
                    )
                )
                
                # Rollback if dry run
                if dry_run:
                    transaction.set_rollback(True)
                    self.stdout.write(
                        self.style.WARNING("\nDry run complete - no changes made to database")
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS("\n✅ Cleanup complete!")
                    )
                
                # Database optimization (SQLite specific)
                if optimize and not dry_run:
                    self.stdout.write("\nOptimizing database...")
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute("VACUUM")
                        cursor.execute("ANALYZE")
                    self.stdout.write(
                        self.style.SUCCESS("✅ Database optimized!")
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n❌ Error during cleanup: {str(e)}")
            )
            raise


# Import after class definition
from django.db import models
