"""
Test script to verify that build_prototypes.py and semantic_classifier.py
use the same paths for prototypes and metadata.
"""

from django.core.management.base import BaseCommand
import os


class Command(BaseCommand):
    help = 'Verify that build_prototypes and semantic_classifier use the same paths'

    def handle(self, *args, **options):
        from django.conf import settings
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Path Verification Test'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Expected paths using Django settings
        expected_protos_dir = os.path.join(settings.BASE_DIR, "protos")
        expected_npz = os.path.join(expected_protos_dir, "prototypes.npz")
        expected_meta = os.path.join(expected_protos_dir, "meta.json")
        
        # Path from semantic_classifier.py - import it to get the actual paths
        try:
            from tracker.services import semantic_classifier
            classifier_npz = semantic_classifier.NPZ_PATH
            classifier_meta = semantic_classifier.META_PATH
            classifier_protos_dir = semantic_classifier.PROTOS_DIR
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to import semantic_classifier: {e}'))
            return
        
        self.stdout.write('\n📁 Django Settings:')
        self.stdout.write(f'   BASE_DIR: {settings.BASE_DIR}')
        
        self.stdout.write('\n📁 Expected Paths (from settings.BASE_DIR):')
        self.stdout.write(f'   Protos Dir: {expected_protos_dir}')
        self.stdout.write(f'   NPZ: {expected_npz}')
        self.stdout.write(f'   Meta: {expected_meta}')
        
        self.stdout.write('\n📁 Semantic Classifier Actual Paths:')
        self.stdout.write(f'   Protos Dir: {classifier_protos_dir}')
        self.stdout.write(f'   NPZ: {classifier_npz}')
        self.stdout.write(f'   Meta: {classifier_meta}')
        
        self.stdout.write('\n' + '=' * 70)
        
        if expected_npz == classifier_npz and expected_meta == classifier_meta:
            self.stdout.write(self.style.SUCCESS('✅ PATHS MATCH! All components use the same location.'))
            self.stdout.write(self.style.SUCCESS(f'\n   Shared location: {expected_protos_dir}'))
        else:
            self.stdout.write(self.style.ERROR('❌ PATHS DO NOT MATCH!'))
            
        self.stdout.write('=' * 70)
        
        # Check if files exist
        self.stdout.write('\n📋 File Status:')
        if os.path.exists(expected_npz):
            self.stdout.write(self.style.SUCCESS(f'   ✅ {expected_npz} exists'))
        else:
            self.stdout.write(self.style.WARNING(f'   ⚠️  {expected_npz} does not exist'))
            self.stdout.write('      Run: python manage.py build_prototypes')
            
        if os.path.exists(expected_meta):
            self.stdout.write(self.style.SUCCESS(f'   ✅ {expected_meta} exists'))
        else:
            self.stdout.write(self.style.WARNING(f'   ⚠️  {expected_meta} does not exist'))
            self.stdout.write('      Run: python manage.py build_prototypes')
