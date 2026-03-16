"""
Diagnostic script to check iCloud calendar sync classification issues
"""
from django.core.management.base import BaseCommand
from tracker.models import DailyLog, User, Category, Task
from django.db.models import Q


class Command(BaseCommand):
    help = 'Diagnose iCloud calendar sync classification issues'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('iCloud Calendar Sync Classification Diagnostics'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # 1. Check system user
        self.stdout.write('\n📋 Checking system user...')
        try:
            system_user = User.objects.get(username='system_global')
            self.stdout.write(self.style.SUCCESS(f'  ✅ System user exists: {system_user.username}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('  ❌ System user "system_global" NOT found'))
            self.stdout.write(self.style.WARNING('     Run: python manage.py create_global_default_tasks'))
            return
        
        # 2. Check semantic classifier
        self.stdout.write('\n🔍 Checking semantic classifier...')
        try:
            from tracker.services import MODEL_AVAILABLE, classify_text
            self.stdout.write(self.style.SUCCESS(f'  ✅ Semantic classifier imports successfully'))
            self.stdout.write(f'     MODEL_AVAILABLE: {MODEL_AVAILABLE}')
            
            if not MODEL_AVAILABLE:
                self.stdout.write(self.style.WARNING('     ⚠️  Model not loaded - check prototypes exist'))
                self.stdout.write('        Run: python manage.py build_prototypes')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Failed to import: {str(e)}'))
            return
        
        # 3. Check global categories and tasks
        self.stdout.write('\n📂 Checking global categories and tasks...')
        global_categories = Category.objects.filter(is_global=True)
        global_tasks = Task.objects.filter(user=system_user, is_global=True)
        
        self.stdout.write(f'  Categories: {global_categories.count()}')
        self.stdout.write(f'  Tasks: {global_tasks.count()}')
        
        if global_categories.count() == 0:
            self.stdout.write(self.style.WARNING('  ⚠️  No global categories found'))
            self.stdout.write('     Run: python manage.py create_global_default_tasks')
        
        # 4. Find unclassified logs from iCloud
        self.stdout.write('\n📝 Checking for unclassified iCloud logs...')
        unclassified_logs = DailyLog.objects.filter(
            Q(description__icontains='Synced from iCloud Calendar') &
            (Q(category__isnull=True) | Q(task__isnull=True))
        ).order_by('-date', '-id')
        
        if unclassified_logs.count() == 0:
            self.stdout.write(self.style.SUCCESS('  ✅ No unclassified iCloud logs found'))
        else:
            self.stdout.write(self.style.WARNING(f'  ⚠️  Found {unclassified_logs.count()} unclassified log(s)'))
            
            # Show first 5
            for log in unclassified_logs[:5]:
                self.stdout.write(f'\n  Log ID {log.id}:')
                self.stdout.write(f'    Activity: {log.activity}')
                self.stdout.write(f'    Category: {log.category or "None"}')
                self.stdout.write(f'    Task: {log.task or "None"}')
                self.stdout.write(f'    Date: {log.date}')
                
                # Test classification
                if MODEL_AVAILABLE:
                    predicted_category, scores = classify_text(log.activity)
                    self.stdout.write(f'    Predicted: {predicted_category}')
                    
                    # Check if category exists
                    matching_cat = Category.objects.filter(
                        name__iexact=predicted_category,
                        is_global=True
                    ).first()
                    
                    if matching_cat:
                        self.stdout.write(self.style.SUCCESS(f'      ✅ Category "{predicted_category}" exists'))
                        
                        # Check if task exists
                        matching_task = Task.objects.filter(
                            user=system_user,
                            category=matching_cat,
                            is_global=True
                        ).first()
                        
                        if matching_task:
                            self.stdout.write(self.style.SUCCESS(f'      ✅ Task exists: "{matching_task.title}"'))
                        else:
                            self.stdout.write(self.style.WARNING(f'      ⚠️  No task found for category'))
                    else:
                        self.stdout.write(self.style.WARNING(f'      ⚠️  Category "{predicted_category}" not found in global categories'))
        
        # 5. Solution
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('💡 SOLUTION'))
        self.stdout.write('=' * 70)
        
        if unclassified_logs.count() > 0:
            self.stdout.write('\nTo fix unclassified logs:')
            self.stdout.write('  1. The import issue has been fixed in the code')
            self.stdout.write('  2. Restart your Django server to apply the fix')
            self.stdout.write('  3. Re-sync your iCloud calendar:')
            self.stdout.write('     - Go to Calendar Settings in your app')
            self.stdout.write('     - Click "Sync Now" button')
            self.stdout.write('     OR run: python manage.py sync_icloud_calendars --force')
            self.stdout.write('\n  Note: Existing logs will keep their current category/task.')
            self.stdout.write('        Only NEW syncs will use automatic classification.')
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Everything looks good!'))
            self.stdout.write('   Next sync will automatically classify events.')
        
        self.stdout.write('=' * 70)
