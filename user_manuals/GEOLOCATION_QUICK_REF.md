# Geolocation Feature - Quick Reference

## What Was Added

IP-based geolocation tracking for landing page visitors to identify their country and city.

## Files Modified

1. **requirements.txt** - Added `geoip2==4.8.1`
2. **tracker/visitor_tracking.py** - Added `get_geolocation_from_ip()` function
3. **tracker/visitor_tracking.py** - Updated `track_landing_page_visitor()` to capture location
4. **tracker/views.py** - Added country_stats and city_stats to landing_analytics view
5. **templates/tracker/landing_analytics.html** - Added geographic charts and location column

## Quick Start

### 1. Install the package:
```bash
pip install geoip2==4.8.1
```

### 2. Download GeoLite2 database:
- Sign up at https://www.maxmind.com/en/geolite2/signup
- Download GeoLite2-City.mmdb
- Place at `/usr/share/GeoIP/GeoLite2-City.mmdb`

### 3. Add to Django settings:
```python
# progress_tracker/settings.py
GEOIP_PATH = '/usr/share/GeoIP/GeoLite2-City.mmdb'
```

### 4. Test it:
```python
python manage.py shell
from tracker.visitor_tracking import get_geolocation_from_ip
print(get_geolocation_from_ip('8.8.8.8'))  # Should return US location
```

## What's New in Analytics Dashboard

### Geographic Charts (New Section)
- 🌍 **Visitors by Country** - Bar chart showing top 15 countries
- 🏙️ **Visitors by City** - Bar chart showing top 15 cities with country

### Recent Visitors Table (Updated)
- Added **Location** column showing "City, Country" or just "Country"
- Shows "-" if no location data available

## Privacy Notes

- Only stores country and city (not precise coordinates)
- Private IPs (local/internal) are not resolved
- Update privacy policy to mention IP-based location tracking

## Troubleshooting

**No location data showing?**
- Check database file exists: `ls /usr/share/GeoIP/GeoLite2-City.mmdb`
- Check Django logs for warnings about missing database
- Test with public IP (not 127.0.0.1 or 192.168.x.x)

**Getting country but not city?**
- This is normal for some IP ranges (VPNs, mobile carriers)
- Database may have incomplete data for certain regions

## For Complete Documentation

See [GEOLOCATION_SETUP.md](GEOLOCATION_SETUP.md) for:
- Detailed installation steps
- Production deployment guide
- Alternative services (IP-API, IPinfo)
- GDPR compliance notes
- Advanced troubleshooting
