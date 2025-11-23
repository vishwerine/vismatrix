from django.core.management.base import BaseCommand
from tracker.models import Category

class Command(BaseCommand):
    help = 'Create default global categories'

    def handle(self, *args, **kwargs):
        global_categories = [
            {'name': 'Study', 'color': '#3498db'},
            {'name': 'Work', 'color': '#e74c3c'},
            {'name': 'Exercise', 'color': '#27ae60'},
            {'name': 'Personal', 'color': '#9b59b6'},
            {'name': 'Reading', 'color': '#f39c12'},
            {'name': 'Health', 'color': '#1abc9c'},
            {'name': 'Social', 'color': '#e91e63'},
        ]
        
        created_count = 0
        for cat_data in global_categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                is_global=True,
                user=None,
                defaults={'color': cat_data['color']}
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created global category: {category.name}')
                )
            else:
                self.stdout.write(f'  Category already exists: {category.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal: {created_count} new global categories created')
        )
