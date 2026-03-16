# IP Geolocation Setup Guide

## Overview

The landing page analytics now tracks visitor geolocation (country, city) based on their IP addresses. This guide explains how to set up and configure the GeoIP database.

## Features Added

1. **Automatic IP Geolocation** - Extracts country and city from visitor IP addresses
2. **Geographic Analytics** - New charts showing visitors by country and city
3. **Location Column** - Displays visitor location in the recent visitors table
4. **Privacy-Friendly** - Only tracks country/city level data, no precise coordinates stored

## Installation

### Step 1: Install Required Package

The `geoip2` library has been added to requirements.txt. Install it:

```bash
pip install geoip2==4.8.1
```

Or install all requirements:

```bash
cd /path/to/vismatrix/progress_tracker
pip install -r ../requirements.txt
```

### Step 2: Download GeoLite2 Database

MaxMind provides free GeoLite2 databases. You need the City database.

#### Option A: Manual Download

1. **Sign up for a free MaxMind account**: https://www.maxmind.com/en/geolite2/signup
2. **Download GeoLite2-City database** in binary format (.mmdb)
3. **Extract the database** to a secure location:
   ```bash
   # Example locations:
   # Linux/macOS: /usr/share/GeoIP/
   # Or keep it in your project (not in git!)
   sudo mkdir -p /usr/share/GeoIP
   sudo cp GeoLite2-City.mmdb /usr/share/GeoIP/
   ```

#### Option B: Using geoipupdate (Recommended for Production)

1. Install geoipupdate:
   ```bash
   # macOS
   brew install geoipupdate
   
   # Ubuntu/Debian
   sudo apt-get install geoipupdate
   ```

2. Configure with your MaxMind account credentials:
   ```bash
   # Edit /etc/GeoIP.conf or ~/.geoipupdate/GeoIP.conf
   AccountID YOUR_ACCOUNT_ID
   LicenseKey YOUR_LICENSE_KEY
   EditionIDs GeoLite2-City
   ```

3. Run update:
   ```bash
   geoipupdate
   ```

### Step 3: Configure Django Settings

Add the GeoIP database path to your Django settings:

```python
# In progress_tracker/settings.py

# GeoIP Configuration
GEOIP_PATH = '/usr/share/GeoIP/GeoLite2-City.mmdb'

# Alternative: Keep in project directory (don't commit to git!)
# GEOIP_PATH = os.path.join(BASE_DIR, 'geoip', 'GeoLite2-City.mmdb')
```

### Step 4: Apply Database Migration (if needed)

The `country` and `city` fields already exist in the `LandingPageVisitor` model, so no migration is needed. But if you're setting this up fresh:

```bash
python manage.py makemigrations
python manage.py migrate
```

## How It Works

### Geolocation Tracking Flow

1. **Visitor arrives** at the landing page
2. **IP address is extracted** from the request (handles proxies via X-Forwarded-For)
3. **GeoIP lookup is performed** using the MaxMind database
4. **Location data is stored**: country, city
5. **Graceful fallback**: If database is missing or IP is private, fields remain empty

### Code Structure

- **`visitor_tracking.py`**: Contains `get_geolocation_from_ip()` function
- **`track_landing_page_visitor()`**: Calls geolocation lookup and saves data
- **`views.py` (landing_analytics)**: Aggregates country/city statistics
- **`landing_analytics.html`**: Displays geographic breakdown charts

## Testing

### Test Geolocation Locally

```python
# Django shell
python manage.py shell

from tracker.visitor_tracking import get_geolocation_from_ip

# Test with a public IP
geo = get_geolocation_from_ip('8.8.8.8')
print(geo)
# Should output: {'country': 'United States', 'country_code': 'US', 'city': '', ...}

# Test with your current IP (if public)
import requests
my_ip = requests.get('https://api.ipify.org').text
geo = get_geolocation_from_ip(my_ip)
print(geo)
```

### Verify in Admin

1. Visit the landing page: http://localhost:8000/
2. Go to admin: http://localhost:8000/admin/tracker/landingpagevisitor/
3. Check if your visitor has `country` and `city` populated

### View Analytics

1. Visit: http://localhost:8000/landing-analytics/ (staff only)
2. Check the "Visitors by Country" and "Visitors by City" sections
3. Verify the Location column in the Recent Visitors table

## Privacy & GDPR Compliance

### Data Collected
- **Country**: e.g., "United States"
- **City**: e.g., "New York"

### Not Collected
- Latitude/longitude (available but not stored)
- Street addresses
- Precise coordinates

### Compliance Notes
- Geolocation is derived from IP, which may be considered personal data under GDPR
- Update your privacy policy to mention IP-based location tracking
- Provide opt-out mechanisms if required by your jurisdiction
- Consider anonymizing/deleting old visitor data periodically

## Troubleshooting

### No Location Data Showing

**Symptoms**: All visitors show "-" for location

**Solutions**:
1. Check database file exists:
   ```bash
   ls -lh /usr/share/GeoIP/GeoLite2-City.mmdb
   ```

2. Verify Django settings:
   ```python
   python manage.py shell
   from django.conf import settings
   print(settings.GEOIP_PATH)
   ```

3. Check logs for warnings:
   ```bash
   # Look for messages like:
   # "GeoIP database not found"
   # "geoip2 library not installed"
   ```

4. Test manually in shell (see Testing section above)

### Only Getting Country, No City

- Some IP ranges only provide country-level data
- This is normal for mobile carriers, VPNs, or data center IPs
- The database may have incomplete city information for certain regions

### Private IPs Not Resolved

- Local IPs (127.x, 192.168.x, 10.x) are intentionally skipped
- These have no geographic meaning
- Test with a public IP address

### Database Out of Date

MaxMind updates GeoLite2 databases regularly. Update monthly:

```bash
# If using geoipupdate
geoipupdate

# If manual, re-download from MaxMind website
```

## Production Deployment

### AWS EC2 / Cloud Servers

1. Install database on server:
   ```bash
   sudo mkdir -p /usr/share/GeoIP
   sudo wget -O /usr/share/GeoIP/GeoLite2-City.mmdb.gz \
     https://download.maxmind.com/app/geoip_download?...
   sudo gunzip /usr/share/GeoIP/GeoLite2-City.mmdb.gz
   ```

2. Set up automatic updates with cron:
   ```bash
   sudo crontab -e
   # Add: 0 2 * * 0 geoipupdate  # Weekly at 2 AM
   ```

### Docker

```dockerfile
# In your Dockerfile
RUN apt-get update && apt-get install -y geoipupdate
COPY GeoIP.conf /etc/GeoIP.conf
RUN geoipupdate

# Or copy database directly
COPY GeoLite2-City.mmdb /usr/share/GeoIP/
```

### Environment Variables

For different environments:

```python
# settings.py
import os

if os.environ.get('ENVIRONMENT') == 'production':
    GEOIP_PATH = '/usr/share/GeoIP/GeoLite2-City.mmdb'
else:
    GEOIP_PATH = os.path.join(BASE_DIR, 'geoip', 'GeoLite2-City.mmdb')
```

## Alternative Services

If you prefer cloud-based geolocation:

### IP-API.com (Free API)
- 45 requests/minute free
- No signup required
- Less accurate than MaxMind

### IPinfo.io
- 50,000 requests/month free
- Requires API key
- Very accurate

### Implementation Example (IP-API)

```python
# In visitor_tracking.py
import requests

def get_geolocation_from_ip(ip_address):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=2)
        data = response.json()
        return {
            'country': data.get('country', ''),
            'city': data.get('city', ''),
        }
    except:
        return {'country': '', 'city': ''}
```

⚠️ **Note**: External API calls add latency to page loads. MaxMind's local database is faster.

## Summary

You've successfully added IP geolocation tracking! Your landing page analytics now include:

- ✅ Country and city detection from IP addresses
- ✅ Geographic breakdown charts in analytics dashboard
- ✅ Location column in visitor table
- ✅ Privacy-friendly (city-level only)
- ✅ Graceful fallback if database unavailable

For questions or issues, check the logs or test the geolocation function directly in Django shell.
