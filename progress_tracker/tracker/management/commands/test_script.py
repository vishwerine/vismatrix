from django.core.management.base import BaseCommand
from tracker.services.semantic_classifier import classify_text


class Command(BaseCommand):
    help = 'Test semantic classification of activities'

    def handle(self, *args, **options):
        # Demo
        tests = [
            "Leg day at the gym and a 5k run",
            "Book dentist appointment",
            "10 minutes mindfulness breathing",
            "Revise for exam and finish coursework",
            "Practice Spanish vocabulary",
            "Update CV and apply to jobs",
            "Prepare for technical interview",
            "Client meeting and send weekly report",
            "Invoice client for freelance gig",
            "Read two chapters",
            "Write a gratitude journal entry",
            "Work on my side project and ship feature",
        ]                       

        for t in tests:
            best, top = classify_text(t)
            self.stdout.write(f"\nTEXT: {t}")
            self.stdout.write(self.style.SUCCESS(f"PRED: {best}"))
            for cat, sc in top:
                self.stdout.write(f"  - {cat:12s}  sim={sc:.3f}")


