"""
Django management command to create sample landing page visitors with geolocation data.
Useful for testing the analytics dashboard and map visualization.

Usage:
    python manage.py create_sample_visitors
    python manage.py create_sample_visitors --count 50
"""

from django.core.management.base import BaseCommand
from tracker.models import LandingPageVisitor
from django.utils import timezone
import random
from datetime import timedelta

# Sample cities with real coordinates
SAMPLE_LOCATIONS = [
    # North America
    {'city': 'New York', 'country': 'United States', 'lat': 40.7128, 'lng': -74.0060},
    {'city': 'Los Angeles', 'country': 'United States', 'lat': 34.0522, 'lng': -118.2437},
    {'city': 'San Francisco', 'country': 'United States', 'lat': 37.7749, 'lng': -122.4194},
    {'city': 'Chicago', 'country': 'United States', 'lat': 41.8781, 'lng': -87.6298},
    {'city': 'Toronto', 'country': 'Canada', 'lat': 43.6532, 'lng': -79.3832},
    {'city': 'Vancouver', 'country': 'Canada', 'lat': 49.2827, 'lng': -123.1207},
    {'city': 'Mexico City', 'country': 'Mexico', 'lat': 19.4326, 'lng': -99.1332},
    
    # Europe
    {'city': 'London', 'country': 'United Kingdom', 'lat': 51.5074, 'lng': -0.1278},
    {'city': 'Paris', 'country': 'France', 'lat': 48.8566, 'lng': 2.3522},
    {'city': 'Berlin', 'country': 'Germany', 'lat': 52.5200, 'lng': 13.4050},
    {'city': 'Madrid', 'country': 'Spain', 'lat': 40.4168, 'lng': -3.7038},
    {'city': 'Amsterdam', 'country': 'Netherlands', 'lat': 52.3676, 'lng': 4.9041},
    {'city': 'Rome', 'country': 'Italy', 'lat': 41.9028, 'lng': 12.4964},
    {'city': 'Stockholm', 'country': 'Sweden', 'lat': 59.3293, 'lng': 18.0686},
    
    # Asia
    {'city': 'Tokyo', 'country': 'Japan', 'lat': 35.6762, 'lng': 139.6503},
    {'city': 'Singapore', 'country': 'Singapore', 'lat': 1.3521, 'lng': 103.8198},
    {'city': 'Hong Kong', 'country': 'Hong Kong', 'lat': 22.3193, 'lng': 114.1694},
    {'city': 'Seoul', 'country': 'South Korea', 'lat': 37.5665, 'lng': 126.9780},
    {'city': 'Shanghai', 'country': 'China', 'lat': 31.2304, 'lng': 121.4737},
    {'city': 'Mumbai', 'country': 'India', 'lat': 19.0760, 'lng': 72.8777},
    {'city': 'Bangalore', 'country': 'India', 'lat': 12.9716, 'lng': 77.5946},
    {'city': 'Bangkok', 'country': 'Thailand', 'lat': 13.7563, 'lng': 100.5018},
    
    # Australia / Oceania
    {'city': 'Sydney', 'country': 'Australia', 'lat': -33.8688, 'lng': 151.2093},
    {'city': 'Melbourne', 'country': 'Australia', 'lat': -37.8136, 'lng': 144.9631},
    {'city': 'Auckland', 'country': 'New Zealand', 'lat': -36.8485, 'lng': 174.7633},
    
    # South America
    {'city': 'São Paulo', 'country': 'Brazil', 'lat': -23.5505, 'lng': -46.6333},
    {'city': 'Buenos Aires', 'country': 'Argentina', 'lat': -34.6037, 'lng': -58.3816},
    {'city': 'Santiago', 'country': 'Chile', 'lat': -33.4489, 'lng': -70.6693},
    
    # Africa
    {'city': 'Cape Town', 'country': 'South Africa', 'lat': -33.9249, 'lng': 18.4241},
    {'city': 'Lagos', 'country': 'Nigeria', 'lat': 6.5244, 'lng': 3.3792},
    {'city': 'Cairo', 'country': 'Egypt', 'lat': 30.0444, 'lng': 31.2357},
]

BROWSERS = [
    ('Chrome', '120.0'),
    ('Safari', '17.2'),
    ('Firefox', '121.0'),
    ('Edge', '120.0'),
    ('Opera', '106.0'),
]

OPERATING_SYSTEMS = [
    'Windows 11',
    'Windows 10',
    'macOS Sonoma',
    'macOS Ventura',
    'Ubuntu 22.04',
    'iOS 17.2',
    'Android 14',
    'Android 13',
]

DEVICES = ['desktop', 'mobile', 'tablet']

UTM_SOURCES = ['google', 'facebook', 'twitter', 'linkedin', 'reddit', 'direct', 'email', '']
UTM_CAMPAIGNS = ['summer-2026', 'product-launch', 'newsletter', 'winter-promo', '']
UTM_MEDIUMS = ['cpc', 'social', 'email', 'organic', 'referral', '']


class Command(BaseCommand):
    help = 'Create sample landing page visitors with geolocation data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=30,
            help='Number of sample visitors to create (default: 30)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing visitors before creating new ones',
        )

    def handle(self, *args, **options):
        count = options['count']
        clear = options['clear']

        if clear:
            deleted_count = LandingPageVisitor.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f'Deleted {deleted_count} existing visitors'))

        self.stdout.write(f'Creating {count} sample visitors...\n')

        created = 0
        now = timezone.now()

        for i in range(count):
            location = random.choice(SAMPLE_LOCATIONS)
            browser, browser_version = random.choice(BROWSERS)
            os = random.choice(OPERATING_SYSTEMS)
            device = random.choice(DEVICES)
            
            # Random IP address (fake but valid format)
            ip = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
            
            # Random visit time within last 30 days
            days_ago = random.randint(0, 30)
            visit_time = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
            
            # 20% chance of conversion
            converted = random.random() < 0.2
            
            # Random visit count (1-5)
            visit_count = random.randint(1, 5)
            
            visitor = LandingPageVisitor.objects.create(
                ip_address=ip,
                session_key=f"session_{i}_{random.randint(1000, 9999)}",
                user_agent=f"Mozilla/5.0 ({os}) {browser}/{browser_version}",
                browser=browser,
                browser_version=browser_version,
                os=os,
                device=device,
                referrer=f"https://www.{random.choice(['google', 'facebook', 'twitter'])}.com/search" if random.random() > 0.3 else "",
                utm_source=random.choice(UTM_SOURCES),
                utm_medium=random.choice(UTM_MEDIUMS),
                utm_campaign=random.choice(UTM_CAMPAIGNS),
                country=location['country'],
                city=location['city'],
                latitude=location['lat'],
                longitude=location['lng'],
                landing_page_url="https://vismatrix.space/",
                language='en',
                visit_count=visit_count,
                converted_to_user=converted,
                first_visit=visit_time,
                last_visit=visit_time + timedelta(hours=random.randint(1, 48)),
            )
            
            created += 1
            
            if created % 10 == 0:
                self.stdout.write(f'  Created {created}/{count} visitors...')

        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✓ Successfully created {created} sample visitors!'))
        self.stdout.write(f'  Locations: {len(set(v["city"] for v in SAMPLE_LOCATIONS))} cities worldwide')
        self.stdout.write(f'  Conversions: ~{int(created * 0.2)} converted visitors')
        self.stdout.write('='*60)
        self.stdout.write('\nView them at: /admin-analytics/landing/')
