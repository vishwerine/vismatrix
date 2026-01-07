"""
Quick test script to verify timezone functionality
Run this after starting the Django server
"""
import requests
import json

# Test data
BASE_URL = "http://localhost:8000"
TEST_TIMEZONE = "America/New_York"

def test_timezone_api():
    """Test the timezone API endpoint"""
    print("Testing Timezone API...")
    print("-" * 50)
    
    # You'll need to authenticate first and get session cookies
    # This is a manual test outline
    
    print(f"1. Login to {BASE_URL}/accounts/login/")
    print("2. Open browser console")
    print("3. Check for 'Timezone saved:' message")
    print("4. Verify with: localStorage.getItem('user_timezone')")
    print("")
    print("To manually set timezone:")
    print(f"   TimezoneHelper.saveTimezoneToServer('{TEST_TIMEZONE}')")
    print("")
    print("To verify in Django shell:")
    print("   python manage.py shell")
    print("   >>> from django.contrib.auth.models import User")
    print("   >>> user = User.objects.get(username='YOUR_USERNAME')")
    print("   >>> print(user.userprofile.timezone)")
    print("")
    print("Test Cases to Verify:")
    print("✓ User login auto-detects timezone")
    print("✓ Timezone saved to UserProfile")
    print("✓ Day planner shows times in user's timezone")
    print("✓ Task times display in local timezone")
    print("✓ Calendar events show in local time")
    print("✓ Analytics times respect user timezone")
    print("")
    print("Expected Behavior:")
    print("- Times displayed match user's system clock")
    print("- 9:00 AM in New York displays as 9:00 AM for NY users")
    print("- 9:00 AM in New York displays as 2:00 PM for London users")
    print("")
    print("Common Timezones for Testing:")
    print("- America/New_York (EST/EDT)")
    print("- Europe/London (GMT/BST)")
    print("- Asia/Tokyo (JST)")
    print("- Australia/Sydney (AEDT)")
    print("- America/Los_Angeles (PST/PDT)")
    print("-" * 50)

if __name__ == "__main__":
    test_timezone_api()
