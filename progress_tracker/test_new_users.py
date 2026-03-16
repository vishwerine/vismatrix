#!/usr/bin/env python
"""
Quick test to verify the new_users_tracking view is accessible.
Run from the progress_tracker directory: python test_new_users.py
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'progress_tracker.settings')
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth.models import User
from tracker.views import new_users_tracking

def test_new_users_tracking():
    print("Testing New Users Tracking Feature...")
    print("-" * 50)
    
    # Check if staff users exist
    staff_users = User.objects.filter(is_staff=True).count()
    print(f"✓ Staff users in database: {staff_users}")
    
    # Check total users
    total_users = User.objects.count()
    print(f"✓ Total users in database: {total_users}")
    
    # Test with authenticated staff user
    if staff_users > 0:
        staff_user = User.objects.filter(is_staff=True).first()
        client = Client()
        client.force_login(staff_user)
        
        response = client.get('/admin-analytics/new-users/')
        print(f"✓ View response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Page loads successfully!")
            print(f"✓ Template used: {response.templates[0].name if response.templates else 'N/A'}")
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
    else:
        print("⚠ No staff users found. Create a staff user to test the view.")
        print("  Run: python manage.py createsuperuser")
    
    # Test recent users query
    from datetime import timedelta
    from django.utils import timezone
    
    recent_users = User.objects.filter(
        date_joined__gte=timezone.now() - timedelta(days=30)
    ).count()
    print(f"✓ Users joined in last 30 days: {recent_users}")
    
    print("-" * 50)
    print("✅ Tests completed!")
    print("\nTo access the page:")
    print("1. Login as an admin/staff user")
    print("2. Click your profile avatar (top-right)")
    print("3. Go to Admin → New Users Tracking")
    print("   OR directly visit: /admin-analytics/new-users/")

if __name__ == "__main__":
    test_new_users_tracking()
