from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tracker.models import Category, Task


class Command(BaseCommand):
    help = 'Test semantic classification for iCloud calendar events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--event',
            type=str,
            help='Test a specific event text'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('iCloud Calendar Event Classification Test'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Check if system user exists
        try:
            system_user = User.objects.get(username='system_global')
            self.stdout.write(self.style.SUCCESS(f'\n✅ System user found: {system_user.username}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('\n❌ System user "system_global" not found!'))
            self.stdout.write(self.style.WARNING('   Run: python manage.py create_global_default_tasks'))
            return
        
        # Try to load semantic classifier
        try:
            from .semantic_classifier import classify_text
            self.stdout.write(self.style.SUCCESS('✅ Semantic classifier loaded'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Failed to load semantic classifier: {str(e)}'))
            self.stdout.write(self.style.WARNING('   Install: pip install gensim numpy'))
            return
        
        # Get global categories and tasks
        global_categories = Category.objects.filter(is_global=True).order_by('name')
        global_tasks = Task.objects.filter(user=system_user, is_global=True)
        
        self.stdout.write(f'\n📂 Found {global_categories.count()} global categories')
        self.stdout.write(f'📋 Found {global_tasks.count()} global tasks')
        
        # Test events
        if options['event']:
            test_events = [options['event']]
        else:
            test_events = [
                # Fitness
                "Morning workout at gym",
                "5k run in the park",
                "Yoga class downtown",
                
                # Health
                "Doctor appointment checkup",
                "Dentist cleaning",
                "Physical therapy session",
                
                # Meditation
                "10 minutes mindfulness breathing",
                "Evening meditation practice",
                
                # Study
                "Review lecture notes chapter 5",
                "Study for midterm exam",
                "Complete homework assignment",
                
                # Languages
                "Spanish lesson with tutor",
                "Practice French vocabulary",
                "Watch German movie with subtitles",
                
                # Work
                "Team standup meeting",
                "Code review session",
                "Client presentation prep",
                
                # Freelance
                "Invoice client for project",
                "Design mockups for website",
                
                # Reading
                "Read two chapters of book",
                "Finish article on AI",
                
                # Journaling
                "Write gratitude journal entry",
                "Reflect on daily progress",
                
                # Hobbies
                "Guitar practice session",
                "Paint landscape artwork",
                
                # Projects
                "Work on side project feature",
                "Debug app deployment issue",
                
                # Job Search
                "Update resume and portfolio",
                "Apply to 5 job positions",
                
                # Interviews
                "Prepare for technical interview",
                "Mock interview practice",
                
                # Goals
                "Review quarterly goals",
                "Plan next month objectives",
                
                # Habits
                "Track water intake",
                "Morning routine check-in",
                
                # Uncategorized/Ambiguous
                "Lunch with friends",
                "Quick errand run",
            ]
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('Testing Event Classification'))
        self.stdout.write('=' * 70 + '\n')
        
        results = {
            'matched': 0,
            'unmatched': 0,
            'uncategorized': 0,
        }
        
        for event_text in test_events:
            # Classify the event
            try:
                predicted_category, top_scores = classify_text(event_text)
                
                # Find matching category
                matching_category = Category.objects.filter(
                    name__iexact=predicted_category,
                    is_global=True
                ).first()
                
                # Find global task
                global_task = None
                if matching_category:
                    global_task = Task.objects.filter(
                        user=system_user,
                        category=matching_category,
                        is_global=True
                    ).first()
                
                # Display results
                self.stdout.write(f"📅 Event: '{event_text}'")
                
                if predicted_category == "Uncategorized":
                    self.stdout.write(self.style.WARNING(f"   ⚠️  Predicted: {predicted_category}"))
                    results['uncategorized'] += 1
                else:
                    self.stdout.write(f"   🎯 Predicted: {predicted_category}")
                
                if global_task:
                    self.stdout.write(self.style.SUCCESS(f"   ✅ Task: {global_task.title}"))
                    self.stdout.write(f"   📂 Category: {global_task.category.name}")
                    results['matched'] += 1
                else:
                    if predicted_category != "Uncategorized":
                        self.stdout.write(self.style.WARNING(f"   ⚠️  Task: None (category not found in global tasks)"))
                        results['unmatched'] += 1
                    else:
                        self.stdout.write(self.style.WARNING(f"   ⚠️  Task: None (using default category)"))
                
                # Show top predictions
                if len(top_scores) > 1:
                    self.stdout.write(f"   📊 Top predictions:")
                    for cat, score in top_scores[:3]:
                        self.stdout.write(f"      - {cat:15s} (similarity: {score:.3f})")
                
                self.stdout.write('')  # Blank line
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error: {str(e)}\n"))
                results['unmatched'] += 1
        
        # Summary
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write('=' * 70)
        
        total = results['matched'] + results['unmatched'] + results['uncategorized']
        
        self.stdout.write(f"\n📊 Total events tested: {total}")
        self.stdout.write(self.style.SUCCESS(f"   ✅ Successfully matched: {results['matched']} ({results['matched']/total*100:.1f}%)"))
        self.stdout.write(self.style.WARNING(f"   ⚠️  Uncategorized: {results['uncategorized']} ({results['uncategorized']/total*100:.1f}%)"))
        if results['unmatched'] > 0:
            self.stdout.write(self.style.ERROR(f"   ❌ Failed to match: {results['unmatched']} ({results['unmatched']/total*100:.1f}%)"))
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('How iCloud Sync Will Work:'))
        self.stdout.write('=' * 70)
        self.stdout.write('\n1️⃣  Calendar event synced from iCloud')
        self.stdout.write('2️⃣  Event title/summary is classified semantically')
        self.stdout.write('3️⃣  Matching global category is found')
        self.stdout.write('4️⃣  Corresponding global task is assigned')
        self.stdout.write('5️⃣  DailyLog created with task, category, and duration')
        self.stdout.write('\n✨ This ensures consistent categorization across all users!\n')
