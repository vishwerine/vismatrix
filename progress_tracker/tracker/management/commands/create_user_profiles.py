"""
Management command to create UserProfile for all existing users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tracker.models import UserProfile


class Command(BaseCommand):
    help = 'Create UserProfile for all existing users who don\'t have one'

    def handle(self, *args, **options):
        users_without_profile = []
        created_count = 0
        
        for user in User.objects.all():
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'timezone': 'UTC'}
            )
            if created:
                created_count += 1
                users_without_profile.append(user.username)
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created {created_count} UserProfile(s) for: {", ".join(users_without_profile)}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All users already have UserProfile.')
            )
