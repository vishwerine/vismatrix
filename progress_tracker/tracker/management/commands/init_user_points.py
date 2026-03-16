from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tracker.models import UserPoints


class Command(BaseCommand):
    help = 'Initialize UserPoints for existing users'

    def handle(self, *args, **options):
        users = User.objects.all()
        created_count = 0
        
        for user in users:
            user_points, created = UserPoints.objects.get_or_create(user=user)
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created UserPoints for {user.username}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal: {created_count} UserPoints profiles created'))
        self.stdout.write(self.style.SUCCESS(f'Existing: {users.count() - created_count} profiles already existed'))
