"""
Django management command to backfill geolocation data for all landing page visitors.
Updates latitude, longitude, country, and city fields using GeoIP2 database.

Usage:
    python manage.py backfill_visitor_locations
    python manage.py backfill_visitor_locations --missing-only
    python manage.py backfill_visitor_locations --force
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from tracker.models import LandingPageVisitor
from tracker.visitor_tracking import get_geolocation_from_ip
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backfill geolocation data (lat/lng, country, city) for landing page visitors using GeoIP'

    def add_arguments(self, parser):
        parser.add_argument(
            '--missing-only',
            action='store_true',
            help='Only update visitors that are missing country or city data',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update all visitors, even if they already have location data',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of visitors to process',
        )

    def handle(self, *args, **options):
        missing_only = options['missing_only']
        force = options['force']
        limit = options['limit']

        # Determine which visitors to process
        if force:
            visitors = LandingPageVisitor.objects.all()
            self.stdout.write(self.style.WARNING('Force mode: Processing ALL visitors'))
        elif missing_only:
            visitors = LandingPageVisitor.objects.filter(
                Q(country='') | Q(country__isnull=True) | 
                Q(city='') | Q(city__isnull=True)
            )
            self.stdout.write(self.style.SUCCESS('Processing visitors with missing location data'))
        else:
            # Default: update visitors that don't have latitude/longitude
            visitors = LandingPageVisitor.objects.filter(
                Q(latitude__isnull=True) | Q(longitude__isnull=True)
            )
            self.stdout.write(self.style.SUCCESS('Processing visitors missing lat/lng coordinates'))

        total_count = visitors.count()
        
        if limit:
            visitors = visitors[:limit]
            self.stdout.write(self.style.WARNING(f'Limited to first {limit} visitors'))

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No visitors need updating!'))
            return

        self.stdout.write(f'Found {total_count} visitors to process...\n')

        # Check if latitude/longitude fields exist in the model
        model_fields = [f.name for f in LandingPageVisitor._meta.get_fields()]
        has_lat_lng_fields = 'latitude' in model_fields and 'longitude' in model_fields
        
        if not has_lat_lng_fields:
            self.stdout.write(
                self.style.ERROR(
                    '✗ Error: latitude and longitude fields not found in LandingPageVisitor model.\n'
                    'Please add these fields to the model and run migrations first:\n'
                    '  latitude = models.FloatField(null=True, blank=True)\n'
                    '  longitude = models.FloatField(null=True, blank=True)'
                )
            )
            return

        # Process visitors
        success_count = 0
        skip_count = 0
        error_count = 0

        for i, visitor in enumerate(visitors, 1):
            try:
                # Skip private/local IPs
                ip = visitor.ip_address
                if not ip or ip.startswith(('127.', '192.168.', '10.', '172.')):
                    skip_count += 1
                    if i % 100 == 0:
                        self.stdout.write(f'Progress: {i}/{total_count} ({skip_count} skipped, {error_count} errors)')
                    continue

                # Get geolocation data
                geo_data = get_geolocation_from_ip(ip)
                
                # Update visitor record
                updated = False
                if geo_data['country']:
                    visitor.country = geo_data['country']
                    updated = True
                if geo_data['city']:
                    visitor.city = geo_data['city']
                    updated = True
                if geo_data['latitude'] is not None:
                    visitor.latitude = geo_data['latitude']
                    updated = True
                if geo_data['longitude'] is not None:
                    visitor.longitude = geo_data['longitude']
                    updated = True
                
                if updated:
                    visitor.save(update_fields=['country', 'city', 'latitude', 'longitude'])
                    success_count += 1
                    
                    if i % 100 == 0:
                        self.stdout.write(
                            f'Progress: {i}/{total_count} '
                            f'({success_count} updated, {skip_count} skipped, {error_count} errors)'
                        )
                else:
                    skip_count += 1
                    
            except Exception as e:
                error_count += 1
                logger.error(f'Error processing visitor {visitor.id} with IP {visitor.ip_address}: {e}')
                if error_count <= 5:  # Show first 5 errors
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error processing {visitor.ip_address}: {str(e)}')
                    )

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✓ Processing complete!'))
        self.stdout.write(f'  Total processed: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'  Successfully updated: {success_count}'))
        self.stdout.write(self.style.WARNING(f'  Skipped (private IPs/no data): {skip_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'  Errors: {error_count}'))
        self.stdout.write('='*60)
        
        if success_count == 0 and error_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    '\nNote: If you\'re seeing many errors, ensure:\n'
                    '1. GeoIP2 library is installed: pip install geoip2\n'
                    '2. GeoLite2-City.mmdb database is downloaded and GEOIP_PATH is configured\n'
                    '3. See user_manuals/GEOLOCATION_SETUP.md for setup instructions'
                )
            )
