from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tracker.models import Category

User = get_user_model()

class Command(BaseCommand):
    help = 'Create standard global categories for the progress tracker'

    def handle(self, *args, **options):
        """Create comprehensive set of standard global categories"""
        
        global_categories = [
            # 💪 FITNESS & HEALTH
            {'name': 'Fitness', 'color': '#10b981'},
            {'name': 'Health', 'color': '#f59e0b'},
            {'name': 'Meditation', 'color': '#8b5cf6'},
            
            # 📚 LEARNING & STUDY
            {'name': 'Study', 'color': '#3b82f6'},
            {'name': 'Languages', 'color': '#ef4444'},
            {'name': 'Skills', 'color': '#06b6d4'},
            
            # 💼 CAREER & PROFESSIONAL
            {'name': 'Job Search', 'color': '#f97316'},
            {'name': 'Interviews', 'color': '#84cc16'},
            {'name': 'Work', 'color': '#1e40af'},
            {'name': 'Freelance', 'color': '#7c3aed'},
            
            # 🏠 PERSONAL DEVELOPMENT
            {'name': 'Reading', 'color': '#14b8a6'},
            {'name': 'Journaling', 'color': '#a855f7'},
            {'name': 'Hobbies', 'color': '#f472b6'},
            
            # 🚀 GOAL CATEGORIES
            {'name': 'Goals', 'color': '#059669'},
            {'name': 'Habits', 'color': '#dc2626'},
            {'name': 'Projects', 'color': '#ea580c'},
        ]
        
        created_count = 0
        skipped_count = 0
        
        self.stdout.write(
            self.style.SUCCESS('🌐 Creating Global Categories...')
        )
        self.stdout.write('-' * 60)
        
        for cat_data in global_categories:
            name = cat_data['name']
            
            if Category.objects.filter(name=name, is_global=True).exists():
                self.stdout.write(
                    self.style.WARNING(f"⚠️  SKIP: {name} (already exists)")
                )
                skipped_count += 1
                continue
            
            category = Category.objects.create(
                name=name,
                color=cat_data['color'],
                is_global=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ CREATED: {name} ({cat_data['color']})")
            )
            created_count += 1
        
        self.stdout.write('-' * 60)
        self.stdout.write(
            self.style.SUCCESS(f"🎉 SUMMARY: {created_count} created, {skipped_count} skipped")
        )
        self.stdout.write(
            self.style.SUCCESS(f"📊 Total global categories: {Category.objects.filter(is_global=True).count()}")
        )
        
        # Sample user categories (optional)
        try:
            first_user = User.objects.first()
            if first_user:
                user_cats = [
                    {'name': 'Django Dev', 'color': '#6366f1'},
                    {'name': 'AI Research', 'color': '#ec4899'},
                    {'name': 'Tennis Training', 'color': '#10b981'},
                ]
                
                self.stdout.write(f"\n👤 Sample categories for {first_user.username}:")
                for cat_data in user_cats:
                    if not Category.objects.filter(user=first_user, name=cat_data['name']).exists():
                        Category.objects.create(
                            user=first_user,
                            name=cat_data['name'],
                            color=cat_data['color']
                        )
                        self.stdout.write(f"  ✅ {cat_data['name']}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Skipped user categories: {e}"))
        
        self.stdout.write(
            self.style.SUCCESS('✨ Global categories setup complete!')
        )
