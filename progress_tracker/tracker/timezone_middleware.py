"""
Timezone middleware to activate user's preferred timezone for each request
"""
import pytz
from django.utils import timezone as django_timezone


class TimezoneMiddleware:
    """Middleware to activate user's timezone for the duration of the request"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get timezone from user profile if authenticated
        if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
            tzname = request.user.userprofile.timezone
            if tzname:
                try:
                    django_timezone.activate(pytz.timezone(tzname))
                except pytz.exceptions.UnknownTimeZoneError:
                    # Fall back to UTC if timezone is invalid
                    django_timezone.activate(pytz.UTC)
            else:
                django_timezone.activate(pytz.UTC)
        else:
            # For anonymous users, try to get timezone from session
            tzname = request.session.get('user_timezone')
            if tzname:
                try:
                    django_timezone.activate(pytz.timezone(tzname))
                except (pytz.exceptions.UnknownTimeZoneError, AttributeError):
                    django_timezone.deactivate()
            else:
                django_timezone.deactivate()
        
        response = self.get_response(request)
        
        # Deactivate timezone after request
        django_timezone.deactivate()
        
        return response
