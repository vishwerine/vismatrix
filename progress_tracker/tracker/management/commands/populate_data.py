from django.core.management.base import BaseCommand
from tracker.models import Category, Task, DailyLog
from django.utils import timezone
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Populate sample data for testing'

    def handle(self, *args, **kwargs):
        # Create categories
        categories = [
            Category.objects.get_or_create(name='Study', color='#3498db')[0],
            Category.objects.get_or_create(name='Exercise', color='#27ae60')[0],
            Category.objects.get_or_create(name='Reading', color='#9b59b6')[0],
            Category.objects.get_or_create(name='Coding', color='#e74c3c')[0],
        ]
        
        # Create tasks for last 7 days
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            for j in range(random.randint(2, 5)):
                task = Task.objects.create(
                    title=f'Task {j+1} for {date}',
                    description='Sample task description',
                    category=random.choice(categories),
                    status=random.choice(['pending', 'completed']),
                    priority=random.choice(['low', 'medium', 'high']),
                )
                if task.status == 'completed':
                    task.completed_at = timezone.datetime.combine(date, timezone.datetime.min.time())
                    task.save()
        
        # Create daily logs
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            for j in range(random.randint(3, 6)):
                DailyLog.objects.create(
                    date=date,
                    activity=f'Activity {j+1}',
                    description='Sample activity',
                    category=random.choice(categories),
                    duration=random.randint(30, 180),
                )
        
        self.stdout.write(self.style.SUCCESS('Successfully populated sample data'))
