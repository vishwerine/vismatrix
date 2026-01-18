"""
Visitor tracking utilities for landing page analytics.
"""
from django.utils import timezone
from .models import LandingPageVisitor
import logging

logger = logging.getLogger(__name__)


def get_geolocation_from_ip(ip_address):
    """
    Get geolocation information from IP address using GeoIP2.
    Returns dict with country, city, region, latitude, longitude.
    
    Note: Requires GeoLite2 database to be set up:
    1. Download GeoLite2-City.mmdb from MaxMind
    2. Place in a secure location (e.g., /var/lib/GeoIP/)
    3. Set GEOIP_PATH in Django settings
    
    For development without database, returns None values gracefully.
    """
    geo_data = {
        'country': '',
        'country_code': '',
        'city': '',
        'region': '',
        'latitude': None,
        'longitude': None,
    }
    
    # Skip private/local IPs
    if not ip_address or ip_address.startswith(('127.', '192.168.', '10.', '172.')):
        return geo_data
    
    try:
        import geoip2.database
        from django.conf import settings
        
        # Get GeoIP database path from settings
        geoip_path = getattr(settings, 'GEOIP_PATH', '/usr/share/GeoIP/GeoLite2-City.mmdb')
        
        # Try to open the database and query
        with geoip2.database.Reader(geoip_path) as reader:
            response = reader.city(ip_address)
            
            geo_data['country'] = response.country.name or ''
            geo_data['country_code'] = response.country.iso_code or ''
            geo_data['city'] = response.city.name or ''
            geo_data['region'] = response.subdivisions.most_specific.name if response.subdivisions else ''
            geo_data['latitude'] = response.location.latitude
            geo_data['longitude'] = response.location.longitude
            
    except ImportError:
        logger.warning("geoip2 library not installed. Install with: pip install geoip2")
    except FileNotFoundError:
        logger.warning(f"GeoIP database not found. Download from MaxMind and configure GEOIP_PATH in settings.")
    except Exception as e:
        logger.debug(f"Could not get geolocation for IP {ip_address}: {e}")
    
    return geo_data


def get_client_ip(request):
    """Extract client IP address from request, considering proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def parse_user_agent(user_agent_string):
    """
    Parse user agent string to extract browser, OS, and device information.
    This is a simple parser. For production, consider using user-agents library:
    pip install user-agents
    """
    ua_lower = user_agent_string.lower()
    
    # Detect browser
    browser = 'Unknown'
    browser_version = ''
    
    if 'edg/' in ua_lower or 'edge/' in ua_lower:
        browser = 'Edge'
        if 'edg/' in ua_lower:
            browser_version = user_agent_string.split('Edg/')[1].split()[0]
        else:
            browser_version = user_agent_string.split('Edge/')[1].split()[0]
    elif 'chrome' in ua_lower and 'edg' not in ua_lower:
        browser = 'Chrome'
        if 'chrome/' in ua_lower:
            browser_version = user_agent_string.split('Chrome/')[1].split()[0]
    elif 'firefox' in ua_lower:
        browser = 'Firefox'
        if 'firefox/' in ua_lower:
            browser_version = user_agent_string.split('Firefox/')[1].split()[0]
    elif 'safari' in ua_lower and 'chrome' not in ua_lower:
        browser = 'Safari'
        if 'version/' in ua_lower:
            browser_version = user_agent_string.split('Version/')[1].split()[0]
    elif 'opera' in ua_lower or 'opr/' in ua_lower:
        browser = 'Opera'
        if 'opr/' in ua_lower:
            browser_version = user_agent_string.split('OPR/')[1].split()[0]
    
    # Detect OS
    os_name = 'Unknown'
    
    if 'windows nt 10' in ua_lower:
        os_name = 'Windows 10/11'
    elif 'windows nt 6.3' in ua_lower:
        os_name = 'Windows 8.1'
    elif 'windows nt 6.2' in ua_lower:
        os_name = 'Windows 8'
    elif 'windows nt 6.1' in ua_lower:
        os_name = 'Windows 7'
    elif 'windows' in ua_lower:
        os_name = 'Windows'
    elif 'mac os x' in ua_lower or 'macos' in ua_lower:
        os_name = 'macOS'
    elif 'linux' in ua_lower:
        if 'android' in ua_lower:
            os_name = 'Android'
        else:
            os_name = 'Linux'
    elif 'iphone' in ua_lower or 'ipad' in ua_lower:
        os_name = 'iOS'
    
    # Detect device type
    device = 'Desktop'
    
    if 'mobile' in ua_lower or 'iphone' in ua_lower or 'android' in ua_lower:
        device = 'Mobile'
    elif 'tablet' in ua_lower or 'ipad' in ua_lower:
        device = 'Tablet'
    
    return {
        'browser': browser,
        'browser_version': browser_version,
        'os': os_name,
        'device': device,
    }


def track_landing_page_visitor(request):
    """
    Track a visitor to the landing page and store their information.
    Returns the LandingPageVisitor instance.
    """
    # Get visitor information
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    referrer = request.META.get('HTTP_REFERER', '')
    language = request.META.get('HTTP_ACCEPT_LANGUAGE', '').split(',')[0]
    
    # Get or create session key
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    
    # Parse user agent
    ua_info = parse_user_agent(user_agent)
    
    # Get geolocation data
    geo_data = get_geolocation_from_ip(ip_address)
    
    # Extract UTM parameters
    utm_source = request.GET.get('utm_source', '')
    utm_medium = request.GET.get('utm_medium', '')
    utm_campaign = request.GET.get('utm_campaign', '')
    utm_term = request.GET.get('utm_term', '')
    utm_content = request.GET.get('utm_content', '')
    
    # Build full landing page URL
    landing_page_url = request.build_absolute_uri()
    
    # Try to find existing visitor by IP or session key
    visitor = None
    
    # First try by session key (most reliable)
    if session_key:
        visitor = LandingPageVisitor.objects.filter(session_key=session_key).first()
    
    # If not found, try by IP address (within last 24 hours)
    if not visitor:
        from datetime import timedelta
        yesterday = timezone.now() - timedelta(days=1)
        visitor = LandingPageVisitor.objects.filter(
            ip_address=ip_address,
            last_visit__gte=yesterday
        ).first()
    
    # Create or update visitor record
    if visitor:
        # Update existing visitor
        visitor.last_visit = timezone.now()
        visitor.visit_count += 1
        visitor.session_key = session_key  # Update session key if it changed
        
        # Update referrer if it's new and not empty
        if referrer and referrer != visitor.referrer:
            visitor.referrer = referrer
        
        # Update UTM parameters if they're new
        if utm_source:
            visitor.utm_source = utm_source
        if utm_medium:
            visitor.utm_medium = utm_medium
        if utm_campaign:
            visitor.utm_campaign = utm_campaign
        if utm_term:
            visitor.utm_term = utm_term
        if utm_content:
            visitor.utm_content = utm_content
        
        # Update geolocation if not already set
        if not visitor.country and geo_data['country']:
            visitor.country = geo_data['country']
        if not visitor.city and geo_data['city']:
            visitor.city = geo_data['city']
        
        visitor.save()
    else:
        # Create new visitor
        visitor = LandingPageVisitor.objects.create(
            ip_address=ip_address,
            session_key=session_key,
            user_agent=user_agent,
            browser=ua_info['browser'],
            browser_version=ua_info['browser_version'],
            os=ua_info['os'],
            device=ua_info['device'],
            referrer=referrer,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_term=utm_term,
            utm_content=utm_content,
            landing_page_url=landing_page_url,
            language=language,
            country=geo_data['country'],
            city=geo_data['city'],
        )
    
    return visitor


def mark_visitor_converted(request, user):
    """
    Mark a visitor as converted when they sign up.
    Call this after user registration.
    """
    session_key = request.session.session_key
    ip_address = get_client_ip(request)
    
    # Try to find the visitor record
    visitor = None
    
    if session_key:
        visitor = LandingPageVisitor.objects.filter(session_key=session_key).first()
    
    if not visitor and ip_address:
        from datetime import timedelta
        yesterday = timezone.now() - timedelta(days=1)
        visitor = LandingPageVisitor.objects.filter(
            ip_address=ip_address,
            last_visit__gte=yesterday,
            converted_to_user=False
        ).first()
    
    if visitor:
        visitor.converted_to_user = True
        visitor.user = user
        visitor.save()
        return visitor
    
    return None
