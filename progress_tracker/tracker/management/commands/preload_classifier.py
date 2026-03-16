"""
Management command to preload the semantic classifier model.
This loads the model into memory so it's ready for classification requests.
"""
from django.core.management.base import BaseCommand
import time


class Command(BaseCommand):
    help = 'Preload the semantic classifier model into memory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--background',
            action='store_true',
            help='Run in background (for use in startup scripts)',
        )

    def handle(self, *args, **options):
        background = options.get('background', False)
        
        if not background:
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('Preloading Semantic Classifier'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write('\n⏳ Loading model (this may take 30-180 seconds)...\n')
        
        try:
            from tracker.services.semantic_classifier import preload_model
            
            start_time = time.time()
            success = preload_model()
            elapsed = time.time() - start_time
            
            if success:
                if not background:
                    self.stdout.write(self.style.SUCCESS(f'\n✅ Model loaded successfully in {elapsed:.1f} seconds'))
                    self.stdout.write(self.style.SUCCESS('   Semantic classification is now ready for use.'))
                    self.stdout.write('=' * 70)
            else:
                if not background:
                    self.stdout.write(self.style.ERROR('\n❌ Failed to load model'))
                    self.stdout.write('   Check logs for details.')
                    self.stdout.write('=' * 70)
                raise SystemExit(1)
                
        except Exception as e:
            if not background:
                self.stdout.write(self.style.ERROR(f'\n❌ Error: {str(e)}'))
                self.stdout.write('=' * 70)
            raise SystemExit(1)
