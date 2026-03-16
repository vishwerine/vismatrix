from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from tracker.models import Task, Category


class Command(BaseCommand):
    help = 'Create global default tasks (one per global category) shared by ALL users. These tasks are not editable or deletable.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating tasks'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if global tasks already exist'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Remove old per-user global tasks before creating shared ones'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        cleanup = options['cleanup']
        
        self.stdout.write(self.style.SUCCESS('🌐 Creating Shared Global Default Tasks...\n'))
        self.stdout.write('=' * 70)
        
        # Get or create a system user for global tasks
        system_user, created = User.objects.get_or_create(
            username='system_global',
            defaults={
                'email': 'system@vismatrix.space',
                'is_staff': False,
                'is_superuser': False,
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'\n✨ Created system user: {system_user.username}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Using existing system user: {system_user.username}')
            )
        
        # Cleanup old per-user global tasks if requested
        if cleanup and not dry_run:
            old_tasks = Task.objects.filter(is_global=True).exclude(user=system_user)
            old_count = old_tasks.count()
            if old_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'\n🗑️  Cleaning up {old_count} old per-user global tasks...')
                )
                old_tasks.delete()
                self.stdout.write(self.style.SUCCESS('   ✅ Cleanup complete'))
        
        # Get all global categories
        global_categories = Category.objects.filter(is_global=True).order_by('name')
        
        if not global_categories.exists():
            self.stdout.write(
                self.style.ERROR('\n❌ No global categories found!')
            )
            self.stdout.write(
                self.style.WARNING('   Run: python manage.py create_global_categories first')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'\n📋 Found {global_categories.count()} global categories')
        )
        self.stdout.write('=' * 70 + '\n')
        
        # Calculate due date: 50 years from now
        due_date = timezone.now().date() + timedelta(days=365 * 50)
        
        total_created = 0
        total_skipped = 0
        total_errors = 0
        
        self.stdout.write(
            self.style.SUCCESS(f'📅 Due date for all tasks: {due_date.strftime("%Y-%m-%d")} (50 years from now)\n')
        )
        
        for category in global_categories:
            try:
                # Check if shared global task already exists for this category
                existing_task = Task.objects.filter(
                    user=system_user,
                    category=category,
                    is_global=True
                ).first()
                
                if existing_task and not force:
                    self.stdout.write(
                        f"⚠️  {category.name}: Task '{existing_task.title}' already exists (ID: {existing_task.id})"
                    )
                    total_skipped += 1
                    continue
                
                if dry_run:
                    self.stdout.write(
                        f"🔍 {category.name}: Would create shared global task"
                    )
                    total_created += 1
                    continue
                
                # Create the shared global default task
                task_title = f"{category.name} Activities"
                task_description = (
                    f"Shared default task for tracking {category.name.lower()} activities. "
                    f"This global task is visible to all users and cannot be modified or deleted."
                )
                
                if existing_task and force:
                    # Update existing task
                    existing_task.title = task_title
                    existing_task.description = task_description
                    existing_task.due_date = due_date
                    existing_task.is_editable = False
                    existing_task.is_deletable = False
                    existing_task.save()
                    self.stdout.write(
                        self.style.SUCCESS(f"⚙️  {category.name}: Updated task (ID: {existing_task.id})")
                    )
                    total_skipped += 1
                else:
                    # Create new task
                    task = Task.objects.create(
                        user=system_user,
                        title=task_title,
                        description=task_description,
                        category=category,
                        status='in_progress',
                        priority='medium',
                        due_date=due_date,
                        is_global=True,
                        is_editable=False,
                        is_deletable=False,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ {category.name}: Created '{task_title}' (ID: {task.id})")
                    )
                    total_created += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ {category.name}: Error - {str(e)}")
                )
                total_errors += 1
        
        # Final Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('\n🎉 FINAL SUMMARY:'))
        self.stdout.write(f"   ✅ Tasks created: {total_created}")
        self.stdout.write(f"   ⚠️  Tasks skipped: {total_skipped}")
        
        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f"   ❌ Errors: {total_errors}"))
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n⚠️  DRY RUN MODE - No tasks were actually created')
            )
            self.stdout.write('   Run without --dry-run to create tasks')
        else:
            # Show statistics
            total_global_tasks = Task.objects.filter(
                user=system_user,
                is_global=True
            ).count()
            
            self.stdout.write(
                self.style.SUCCESS(f'\n📊 Total shared global tasks: {total_global_tasks}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'👤 System user: {system_user.username}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'📅 Due date: {due_date.strftime("%Y-%m-%d")}')
            )
        
        self.stdout.write('=' * 70 + '\n')
        
        if not dry_run and total_created > 0:
            self.stdout.write(
                self.style.SUCCESS('✨ Shared global tasks created successfully!')
            )
            self.stdout.write('   - These tasks are visible to ALL users')
            self.stdout.write('   - They cannot be edited or deleted')
            self.stdout.write('   - Due date: 50 years from now')
            self.stdout.write('   - Perfect for standardized activity tracking\n')
            self.stdout.write(
                self.style.WARNING('⚠️  IMPORTANT: Update your views to show system_global user tasks to all users\n')
            )
