from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tracker.models import Task, Category


class Command(BaseCommand):
    help = 'Create a global default task for all users'

    def handle(self, *args, **options):
        # Get or create a superuser or system user
        try:
            system_user = User.objects.filter(is_superuser=True).first()
            if not system_user:
                system_user = User.objects.create_user(
                    username='system',
                    email='system@vismatrix.space',
                    is_staff=True,
                    is_superuser=True
                )
                self.stdout.write(self.style.SUCCESS('Created system user'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating system user: {e}'))
            return

        # Try to get a general category
        general_category = Category.objects.filter(name__iexact='General', is_global=True).first()
        if not general_category:
            general_category = Category.objects.filter(is_global=True).first()

        # Create default task for each user
        for user in User.objects.filter(is_active=True):
            default_task, created = Task.objects.get_or_create(
                user=user,
                title='General Activity',
                defaults={
                    'description': 'Default task for general activities and time tracking',
                    'category': general_category,
                    'status': 'in_progress',
                    'priority': 'medium',
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created default task for user: {user.username}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Default task already exists for user: {user.username}')
                )

        self.stdout.write(self.style.SUCCESS('Default tasks setup complete!'))
